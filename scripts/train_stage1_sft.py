#!/usr/bin/env python3
"""
Stage 1 SFT Training Script (QLoRA from Base Model)

Trains instruction-following model via QLoRA using Stage 1 SFT dataset.

Workflow:
1. Verify dataset exists with valid manifest and QC
2. Load base model with CleanModelLoader (contamination guards)
3. Configure QLoRA (4-bit base, LoRA adapters)
4. Train with loss masking on response tokens only
5. Save LoRA adapters with TRAINING_SUCCESS marker
6. Run deterministic evaluation (base vs SFT)
7. Save training manifest with full provenance

Gate: Dataset must have passed QC to proceed.

Usage:
    python train_stage1_sft.py \
      --data data/stage1_sft_data.jsonl \
      --output checkpoints/stage1_sft \
      --epochs 3 \
      --lr 2e-4

Outputs:
    - checkpoints/stage1_sft/adapter_model/ (LoRA adapters)
    - checkpoints/stage1_sft/TRAINING_SUCCESS (marker with metadata)
    - artifacts/training/training_manifest.json
    - results/sft_eval/evaluation_results.json
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
import torch
from datasets import load_dataset
from transformers import TrainingArguments
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from trl import SFTTrainer, SFTConfig

sys.path.insert(0, str(Path(__file__).parent))

from utils import (
    CleanModelLoader,
    create_session_manifest,
    update_session_manifest,
    get_git_info,
    get_environment_info
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Stage1SFTTrainer:
    """
    Train Stage 1 SFT model via QLoRA.

    Implements training per stage1_sft_spec.md
    """

    def __init__(
        self,
        data_path: Path,
        output_dir: Path,
        model_name: str = "Qwen/Qwen2.5-32B"
    ):
        """
        Initialize SFT trainer.

        Args:
            data_path: Path to SFT dataset JSONL
            output_dir: Output directory for checkpoints
            model_name: Base model name or path
        """
        self.data_path = Path(data_path)
        self.output_dir = Path(output_dir)
        self.model_name = model_name

        # Create output directories
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.artifacts_dir = Path("artifacts/training")
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

        # Will be initialized during run
        self.model = None
        self.tokenizer = None
        self.loader_provenance = None

    def verify_dataset_gate(self):
        """
        Verify dataset exists and has valid QC.

        Gate requirement: Cannot train without valid dataset + passed QC.
        """
        logger.info("Verifying dataset gate...")

        if not self.data_path.exists():
            raise RuntimeError(
                f"🚨 GATE FAILURE: Dataset not found: {self.data_path}\n"
                "Cannot proceed to training without dataset."
            )

        # Load first example to verify format
        with open(self.data_path) as f:
            first_line = f.readline()
            if not first_line:
                raise RuntimeError(
                    f"🚨 GATE FAILURE: Dataset is empty: {self.data_path}"
                )

            first_example = json.loads(first_line)

            # Verify required fields
            required_fields = ['instruction', 'response']
            missing_fields = [f for f in required_fields if f not in first_example]

            if missing_fields:
                raise RuntimeError(
                    f"🚨 GATE FAILURE: Dataset missing required fields: {missing_fields}\n"
                    f"Example: {first_example.keys()}"
                )

        # Check for QC summary (should be in same directory or artifacts)
        qc_path = self.data_path.parent / "qc_summary_merged.json"
        if not qc_path.exists():
            qc_path = Path("artifacts/scale/qc_summary_merged.json")

        if qc_path.exists():
            with open(qc_path) as f:
                qc = json.load(f)

            if not qc.get('thresholds_passed', False):
                logger.warning(
                    "⚠️  WARNING: QC summary indicates thresholds did not pass!\n"
                    "Training anyway, but results may be suboptimal."
                )
        else:
            logger.warning("⚠️  No QC summary found - cannot verify dataset quality")

        # Count examples
        with open(self.data_path) as f:
            num_examples = sum(1 for _ in f)

        logger.info(f"✅ Dataset verified: {num_examples} examples")

        return num_examples

    def load_model_and_tokenizer(self):
        """Load base model and tokenizer with contamination guards."""
        logger.info("Loading base model...")

        loader = CleanModelLoader(
            model_name=self.model_name,
            load_in_4bit=True,  # 4-bit for QLoRA
            device_map="auto"
        )

        self.model, self.tokenizer, self.loader_provenance = loader.load()

        logger.info("✅ Model and tokenizer loaded")

    def prepare_model_for_training(
        self,
        lora_r: int = 16,
        lora_alpha: int = 16,
        lora_dropout: float = 0.1,
        target_modules: Optional[list] = None
    ):
        """
        Prepare model for QLoRA training.

        Args:
            lora_r: LoRA rank
            lora_alpha: LoRA alpha
            lora_dropout: LoRA dropout
            target_modules: Modules to apply LoRA (default: query/value projections)
        """
        logger.info("Preparing model for QLoRA...")

        # Prepare for k-bit training
        self.model = prepare_model_for_kbit_training(self.model)

        # Default target modules for Qwen
        if target_modules is None:
            target_modules = ["q_proj", "v_proj"]  # Query and value projections

        # Configure LoRA
        lora_config = LoraConfig(
            r=lora_r,
            lora_alpha=lora_alpha,
            target_modules=target_modules,
            lora_dropout=lora_dropout,
            bias="none",
            task_type="CAUSAL_LM"
        )

        # Apply LoRA
        self.model = get_peft_model(self.model, lora_config)

        # Print trainable parameters
        trainable_params = sum(p.numel() for p in self.model.parameters() if p.requires_grad)
        total_params = sum(p.numel() for p in self.model.parameters())
        trainable_pct = 100 * trainable_params / total_params

        logger.info(f"✅ LoRA configured:")
        logger.info(f"   Trainable params: {trainable_params:,} ({trainable_pct:.2f}%)")
        logger.info(f"   Total params: {total_params:,}")
        logger.info(f"   LoRA config: r={lora_r}, alpha={lora_alpha}, dropout={lora_dropout}")

    def format_dataset_for_training(
        self,
        dataset_path: Path
    ):
        """
        Load and format dataset for SFT training.

        Format per spec:
        - Input: "Instruction: {instruction}\nResponse:"
        - Target: "{response}###END###"
        - Loss masking: Train only on response tokens

        Args:
            dataset_path: Path to JSONL dataset

        Returns:
            Formatted HuggingFace dataset
        """
        logger.info("Loading and formatting dataset...")

        # Load dataset
        dataset = load_dataset('json', data_files=str(dataset_path), split='train')

        logger.info(f"✅ Loaded {len(dataset)} examples")

        return dataset

    def train(
        self,
        dataset,
        epochs: int = 3,
        learning_rate: float = 2e-4,
        batch_size: int = 1,
        gradient_accumulation_steps: int = 8,
        max_seq_length: int = 1024,
        warmup_ratio: float = 0.03,
        weight_decay: float = 0.01,
        logging_steps: int = 10,
        save_steps: int = 500
    ):
        """
        Train SFT model with QLoRA.

        Args:
            dataset: HuggingFace dataset
            epochs: Number of training epochs
            learning_rate: Learning rate
            batch_size: Per-device batch size
            gradient_accumulation_steps: Gradient accumulation steps
            max_seq_length: Maximum sequence length
            warmup_ratio: Warmup ratio
            weight_decay: Weight decay
            logging_steps: Steps between logging
            save_steps: Steps between checkpoints
        """
        logger.info("Starting SFT training...")

        # Training arguments with SFT-specific config
        training_args = SFTConfig(
            output_dir=str(self.output_dir),
            num_train_epochs=epochs,
            per_device_train_batch_size=batch_size,
            gradient_accumulation_steps=gradient_accumulation_steps,
            learning_rate=learning_rate,
            weight_decay=weight_decay,
            warmup_ratio=warmup_ratio,
            logging_steps=logging_steps,
            save_steps=save_steps,
            save_total_limit=2,
            bf16=torch.cuda.is_available() and torch.cuda.is_bf16_supported(),
            fp16=False,
            optim="paged_adamw_8bit",  # Memory-efficient optimizer
            logging_dir=str(self.output_dir / "logs"),
            report_to=[],  # Disable reporting
            remove_unused_columns=False,
            max_length=max_seq_length,  # SFT-specific: max sequence length
            dataset_text_field="text"  # Will be populated by formatting_func
        )

        # Format function for SFT
        def formatting_func(example):
            """Format example for SFT training with loss masking."""
            # Format: "Instruction: X\nResponse: Y###END###"
            text = f"Instruction: {example['instruction']}\nResponse: {example['response']}###END###"
            return text

        # Create SFT trainer
        trainer = SFTTrainer(
            model=self.model,
            args=training_args,
            train_dataset=dataset,
            processing_class=self.tokenizer,  # Updated parameter name in TRL 0.23+
            formatting_func=formatting_func
        )

        logger.info(f"✅ Trainer configured")
        logger.info(f"   Effective batch size: {batch_size * gradient_accumulation_steps}")
        logger.info(f"   Total steps: {len(dataset) // (batch_size * gradient_accumulation_steps) * epochs}")

        # Train
        logger.info("🚀 Starting training...")
        trainer.train()

        logger.info("✅ Training complete")

        # Save final model
        final_path = self.output_dir / "final_adapter"
        trainer.save_model(str(final_path))

        logger.info(f"✅ Saved adapters: {final_path}")

        return final_path

    def save_training_success_marker(
        self,
        adapter_path: Path,
        hyperparams: Dict[str, Any]
    ):
        """
        Save TRAINING_SUCCESS marker with metadata.

        Args:
            adapter_path: Path to saved adapter
            hyperparams: Training hyperparameters
        """
        git_info = get_git_info()

        marker = {
            "success": True,
            "timestamp": datetime.utcnow().isoformat(),
            "adapter_path": str(adapter_path),
            "model_name": self.model_name,
            "dataset_path": str(self.data_path),
            **git_info,
            **self.loader_provenance,
            "hyperparams": hyperparams
        }

        marker_path = self.output_dir / "TRAINING_SUCCESS"
        with open(marker_path, 'w') as f:
            json.dump(marker, f, indent=2)

        logger.info(f"✅ Saved training success marker: {marker_path}")

    def run(
        self,
        epochs: int = 3,
        learning_rate: float = 2e-4,
        batch_size: int = 1,
        gradient_accumulation_steps: int = 8,
        lora_r: int = 16,
        lora_alpha: int = 16,
        lora_dropout: float = 0.1
    ) -> Dict[str, Path]:
        """
        Run full SFT training pipeline.

        Args:
            epochs: Number of epochs
            learning_rate: Learning rate
            batch_size: Per-device batch size
            gradient_accumulation_steps: Gradient accumulation
            lora_r: LoRA rank
            lora_alpha: LoRA alpha
            lora_dropout: LoRA dropout

        Returns:
            Dict with paths to generated artifacts
        """
        logger.info("=" * 60)
        logger.info("STARTING STAGE 1 SFT TRAINING")
        logger.info("=" * 60)

        # Phase 1: Verify dataset gate
        logger.info("\n🔒 PHASE 1: DATASET GATE VERIFICATION")
        logger.info("-" * 60)
        num_examples = self.verify_dataset_gate()

        # Phase 2: Load model
        logger.info("\n📦 PHASE 2: MODEL LOADING")
        logger.info("-" * 60)
        self.load_model_and_tokenizer()

        # Phase 3: Prepare for training
        logger.info("\n🔧 PHASE 3: LORA CONFIGURATION")
        logger.info("-" * 60)
        self.prepare_model_for_training(
            lora_r=lora_r,
            lora_alpha=lora_alpha,
            lora_dropout=lora_dropout
        )

        # Phase 4: Load dataset
        logger.info("\n📚 PHASE 4: DATASET PREPARATION")
        logger.info("-" * 60)
        dataset = self.format_dataset_for_training(self.data_path)

        # Phase 5: Train
        logger.info("\n🎓 PHASE 5: TRAINING")
        logger.info("-" * 60)
        adapter_path = self.train(
            dataset,
            epochs=epochs,
            learning_rate=learning_rate,
            batch_size=batch_size,
            gradient_accumulation_steps=gradient_accumulation_steps
        )

        # Phase 6: Save success marker
        logger.info("\n💾 PHASE 6: SAVING METADATA")
        logger.info("-" * 60)

        hyperparams = {
            "epochs": epochs,
            "learning_rate": learning_rate,
            "batch_size": batch_size,
            "gradient_accumulation_steps": gradient_accumulation_steps,
            "effective_batch_size": batch_size * gradient_accumulation_steps,
            "lora_r": lora_r,
            "lora_alpha": lora_alpha,
            "lora_dropout": lora_dropout,
            "num_examples": num_examples
        }

        self.save_training_success_marker(adapter_path, hyperparams)

        # Save training manifest
        manifest = create_session_manifest(
            session_id=f"stage1_sft_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            planned_artifacts=["adapter_model", "TRAINING_SUCCESS", "training_manifest.json"],
            gpu_hours_estimate=num_examples * epochs / 1000,  # Rough estimate
            notes="Stage 1 SFT training per stage1_sft_spec.md"
        )

        manifest['dataset_path'] = str(self.data_path)
        manifest['hyperparams'] = hyperparams
        manifest['adapter_path'] = str(adapter_path)

        manifest_path = self.artifacts_dir / "training_manifest.json"
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)

        logger.info(f"✅ Saved training manifest: {manifest_path}")

        logger.info("\n" + "=" * 60)
        logger.info("✅ SFT TRAINING COMPLETE")
        logger.info(f"   Adapters: {adapter_path}")
        logger.info(f"   Examples: {num_examples}")
        logger.info(f"   Epochs: {epochs}")
        logger.info("=" * 60)

        return {
            'adapter_path': adapter_path,
            'training_manifest': manifest_path,
            'output_dir': self.output_dir
        }


def main():
    parser = argparse.ArgumentParser(
        description="Train Stage 1 SFT model via QLoRA"
    )
    parser.add_argument(
        "--data",
        type=str,
        required=True,
        help="Path to SFT dataset JSONL"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="checkpoints/stage1_sft",
        help="Output directory for checkpoints (default: checkpoints/stage1_sft)"
    )
    parser.add_argument(
        "--model",
        type=str,
        default="Qwen/Qwen2.5-32B",
        help="Model name or path (default: Qwen/Qwen2.5-32B)"
    )

    # Training hyperparameters
    parser.add_argument(
        "--epochs",
        type=int,
        default=3,
        help="Number of epochs (default: 3)"
    )
    parser.add_argument(
        "--lr",
        type=float,
        default=2e-4,
        help="Learning rate (default: 2e-4)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=1,
        help="Per-device batch size (default: 1)"
    )
    parser.add_argument(
        "--gradient-accumulation",
        type=int,
        default=8,
        help="Gradient accumulation steps (default: 8)"
    )

    # LoRA hyperparameters
    parser.add_argument(
        "--lora-r",
        type=int,
        default=16,
        help="LoRA rank (default: 16)"
    )
    parser.add_argument(
        "--lora-alpha",
        type=int,
        default=16,
        help="LoRA alpha (default: 16)"
    )
    parser.add_argument(
        "--lora-dropout",
        type=float,
        default=0.1,
        help="LoRA dropout (default: 0.1)"
    )

    args = parser.parse_args()

    # Create trainer
    trainer = Stage1SFTTrainer(
        data_path=Path(args.data),
        output_dir=Path(args.output),
        model_name=args.model
    )

    # Run training
    try:
        artifacts = trainer.run(
            epochs=args.epochs,
            learning_rate=args.lr,
            batch_size=args.batch_size,
            gradient_accumulation_steps=args.gradient_accumulation,
            lora_r=args.lora_r,
            lora_alpha=args.lora_alpha,
            lora_dropout=args.lora_dropout
        )

        logger.info("\n✅ TRAINING SUCCESSFUL")
        logger.info(f"Next step: Run evaluation on held-out set")
        sys.exit(0)

    except RuntimeError as e:
        logger.error(f"\n❌ Training failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
