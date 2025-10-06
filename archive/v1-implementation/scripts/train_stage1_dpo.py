#!/usr/bin/env python3
"""
Stage 1 DPO Training: Explicit Instruction Following
Train with LoRA adapters and save only the adapters (not full weights)
"""

import json
import torch
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import os
import sys

# Configure base directory for RunPod deployment
BASE_DIR = Path(os.getenv('CAI_BASE_DIR', '/workspace/cai-constitution-bootstrap'))

# Add utils to path
sys.path.append(str(BASE_DIR / 'scripts' / 'utils'))

from transformers import TrainingArguments, AutoTokenizer
from trl import DPOTrainer, DPOConfig
from datasets import Dataset
from peft import LoraConfig, get_peft_model, TaskType
from unsloth import FastLanguageModel
import wandb

from model_loader import load_base_model, clear_gpu_cache, print_gpu_utilization
from data_formatter import load_jsonl

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Stage1DPOTrainer:
    """DPO trainer for Stage 1 with LoRA"""
    
    def __init__(self, base_model_name: str = "Qwen/Qwen2.5-32B"):
        self.base_model_name = base_model_name
        self.model = None
        self.tokenizer = None
        self.trainer = None
        
        # Paths
        self.data_dir = BASE_DIR / "data" / "stage1"
        self.checkpoint_dir = BASE_DIR / "checkpoints" / "stage1"
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        
        # LoRA configuration optimized for instruction following
        self.lora_config = LoraConfig(
            r=64,                    # Rank - higher for better performance
            lora_alpha=16,           # Alpha parameter
            target_modules=[         # Qwen architecture modules
                "q_proj", "k_proj", "v_proj", "o_proj",
                "gate_proj", "up_proj", "down_proj"
            ],
            lora_dropout=0.1,        # Dropout for regularization
            bias="none",             # No bias training
            task_type=TaskType.CAUSAL_LM,
        )
        
        logger.info(f"🏋️  Stage 1 DPO trainer initialized")
        logger.info(f"📁 Checkpoints will be saved to: {self.checkpoint_dir}")
    
    def load_model_and_tokenizer(self):
        """Load base model with LoRA configuration"""
        logger.info(f"📥 Loading base model: {self.base_model_name}")
        
        try:
            # Use Unsloth for efficient loading
            self.model, self.tokenizer = FastLanguageModel.from_pretrained(
                model_name=self.base_model_name,
                max_seq_length=2048,
                dtype=None,  # Auto-detect
                load_in_4bit=True,  # For memory efficiency
            )
            
            # Prepare model for LoRA training
            self.model = FastLanguageModel.get_peft_model(
                self.model,
                r=self.lora_config.r,
                target_modules=self.lora_config.target_modules,
                lora_alpha=self.lora_config.lora_alpha,
                lora_dropout=self.lora_config.lora_dropout,
                bias=self.lora_config.bias,
                use_gradient_checkpointing="unsloth",  # Unsloth optimization
                random_state=3407,  # For reproducibility
            )
            
            # Set up tokenizer
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
            
            logger.info("✅ Model and tokenizer loaded with LoRA")
            print_gpu_utilization()
            
        except Exception as e:
            logger.error(f"❌ Failed to load model: {e}")
            raise
    
    def load_training_data(self) -> Dataset:
        """Load and prepare training data"""
        logger.info("📊 Loading training data...")
        
        # Load preference pairs
        train_file = self.data_dir / "train_preference_pairs.jsonl"
        if not train_file.exists():
            raise FileNotFoundError(f"Training data not found: {train_file}")
        
        preference_pairs = load_jsonl(train_file)
        logger.info(f"📈 Loaded {len(preference_pairs)} training preference pairs")
        
        # Convert to dataset format
        dataset_dict = {
            'prompt': [pair['prompt'] for pair in preference_pairs],
            'chosen': [pair['chosen'] for pair in preference_pairs],
            'rejected': [pair['rejected'] for pair in preference_pairs],
        }
        
        dataset = Dataset.from_dict(dataset_dict)
        logger.info(f"✅ Dataset created with {len(dataset)} examples")
        
        return dataset
    
    def load_eval_data(self) -> Optional[Dataset]:
        """Load evaluation data if available"""
        eval_file = self.data_dir / "test_preference_pairs.jsonl"
        
        if not eval_file.exists():
            logger.warning("⚠️  No evaluation data found, skipping eval during training")
            return None
        
        eval_pairs = load_jsonl(eval_file)
        logger.info(f"📊 Loaded {len(eval_pairs)} evaluation preference pairs")
        
        eval_dict = {
            'prompt': [pair['prompt'] for pair in eval_pairs],
            'chosen': [pair['chosen'] for pair in eval_pairs],
            'rejected': [pair['rejected'] for pair in eval_pairs],
        }
        
        return Dataset.from_dict(eval_dict)
    
    def setup_training_args(self, output_dir: str, num_train_epochs: int = 3, 
                           batch_size: int = 4, learning_rate: float = 5e-5) -> DPOConfig:
        """Setup training arguments"""
        
        # Calculate steps
        train_file = self.data_dir / "train_preference_pairs.jsonl"
        num_examples = sum(1 for _ in open(train_file))
        steps_per_epoch = num_examples // batch_size
        total_steps = steps_per_epoch * num_train_epochs
        
        logger.info(f"📊 Training setup:")
        logger.info(f"  Examples: {num_examples}")
        logger.info(f"  Batch size: {batch_size}")
        logger.info(f"  Steps per epoch: {steps_per_epoch}")
        logger.info(f"  Total epochs: {num_train_epochs}")
        logger.info(f"  Total steps: {total_steps}")
        
        config = DPOConfig(
            # Basic settings
            output_dir=output_dir,
            num_train_epochs=num_train_epochs,
            per_device_train_batch_size=batch_size,
            per_device_eval_batch_size=batch_size,
            gradient_accumulation_steps=1,
            
            # Learning rate and optimization
            learning_rate=learning_rate,
            lr_scheduler_type="cosine",
            warmup_steps=min(100, total_steps // 10),
            weight_decay=0.01,
            
            # DPO specific
            beta=0.1,  # DPO beta parameter
            loss_type="sigmoid",  # DPO loss type
            
            # Evaluation and saving
            eval_strategy="steps" if self.load_eval_data() is not None else "no",
            eval_steps=max(50, steps_per_epoch // 4),
            save_strategy="steps",
            save_steps=max(50, steps_per_epoch // 4),
            save_total_limit=3,  # Keep only 3 checkpoints
            
            # Logging
            logging_steps=25,
            report_to=["wandb"] if wandb.api.api_key else [],
            
            # Memory optimization
            dataloader_pin_memory=False,
            gradient_checkpointing=True,
            fp16=not torch.cuda.is_bf16_supported(),
            bf16=torch.cuda.is_bf16_supported(),
            
            # Reproducibility
            seed=42,
            data_seed=42,
            
            # Performance
            dataloader_num_workers=2,
            remove_unused_columns=False,
        )
        
        return config
    
    def train(self, num_epochs: int = 3, batch_size: int = 4, 
              learning_rate: float = 5e-5, run_name: str = None) -> Dict[str, Any]:
        """Train the model with DPO"""
        logger.info("🚀 Starting Stage 1 DPO training...")
        
        # Load model if not already loaded
        if self.model is None:
            self.load_model_and_tokenizer()
        
        # Load data
        train_dataset = self.load_training_data()
        eval_dataset = self.load_eval_data()
        
        # Setup output directory with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if run_name:
            output_dir = self.checkpoint_dir / f"{run_name}_{timestamp}"
        else:
            output_dir = self.checkpoint_dir / f"run_{timestamp}"
        
        # Setup training arguments
        training_args = self.setup_training_args(
            output_dir=str(output_dir),
            num_train_epochs=num_epochs,
            batch_size=batch_size,
            learning_rate=learning_rate
        )
        
        # Initialize Weights & Biases if available
        if wandb.api.api_key:
            wandb.init(
                project="maximalcai-stage1",
                name=f"stage1-dpo-{timestamp}",
                config={
                    "model": self.base_model_name,
                    "stage": 1,
                    "method": "DPO",
                    "lora_r": self.lora_config.r,
                    "lora_alpha": self.lora_config.lora_alpha,
                    "num_epochs": num_epochs,
                    "batch_size": batch_size,
                    "learning_rate": learning_rate,
                }
            )
        
        # Create DPO trainer
        logger.info("🏋️  Initializing DPO trainer...")
        try:
            self.trainer = DPOTrainer(
                model=self.model,
                args=training_args,
                train_dataset=train_dataset,
                eval_dataset=eval_dataset,
                tokenizer=self.tokenizer,
            )
            
            logger.info("✅ DPO trainer initialized")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize trainer: {e}")
            raise
        
        # Start training
        logger.info("🏃 Starting training...")
        try:
            train_result = self.trainer.train()
            
            logger.info("✅ Training completed successfully!")
            
            # Save the final LoRA adapters (not full model!)
            final_adapter_path = output_dir / "final_lora_adapters"
            self.save_lora_adapters(str(final_adapter_path))
            
            # Write success marker for robust checkpoint selection
            success_marker = output_dir / "TRAINING_SUCCESS"
            success_marker.write_text(json.dumps({
                'completed': datetime.now().isoformat(),
                'final_loss': train_result.training_loss,
                'epochs_completed': num_epochs,
                'adapter_path': str(final_adapter_path)
            }))
            
            # Save training summary
            summary = {
                'timestamp': datetime.now().isoformat(),
                'base_model': self.base_model_name,
                'stage': 1,
                'method': 'DPO',
                'lora_config': {
                    'r': self.lora_config.r,
                    'alpha': self.lora_config.lora_alpha,
                    'dropout': self.lora_config.lora_dropout,
                    'target_modules': self.lora_config.target_modules,
                },
                'training_args': {
                    'num_epochs': num_epochs,
                    'batch_size': batch_size,
                    'learning_rate': learning_rate,
                },
                'results': {
                    'train_loss': train_result.training_loss,
                    'train_steps': train_result.global_step,
                },
                'paths': {
                    'output_dir': str(output_dir),
                    'lora_adapters': str(final_adapter_path),
                }
            }
            
            with open(output_dir / "training_summary.json", 'w') as f:
                json.dump(summary, f, indent=2)
            
            logger.info(f"📊 Training loss: {train_result.training_loss:.4f}")
            logger.info(f"📁 LoRA adapters saved to: {final_adapter_path}")
            
            return summary
            
        except Exception as e:
            logger.error(f"❌ Training failed: {e}")
            raise
        
        finally:
            # Clean up
            if wandb.run is not None:
                wandb.finish()
            clear_gpu_cache()
    
    def save_lora_adapters(self, save_path: str):
        """Save only the LoRA adapters (not the full model)"""
        logger.info(f"💾 Saving LoRA adapters to: {save_path}")
        
        save_path = Path(save_path)
        save_path.mkdir(parents=True, exist_ok=True)
        
        try:
            # Save the PEFT model (LoRA adapters only)
            self.model.save_pretrained(save_path)
            
            # Save tokenizer for convenience
            self.tokenizer.save_pretrained(save_path)
            
            # Check size
            adapter_files = list(save_path.glob("*.bin")) + list(save_path.glob("*.safetensors"))
            total_size = sum(f.stat().st_size for f in adapter_files) / (1024**2)  # MB
            
            logger.info(f"✅ LoRA adapters saved successfully")
            logger.info(f"📊 Adapter size: {total_size:.1f} MB")
            
            # Verify we're not saving full weights
            if total_size > 2000:  # More than 2GB suggests full model
                logger.warning(f"⚠️  Adapter size seems large ({total_size:.1f} MB). Check if full weights were saved.")
            
        except Exception as e:
            logger.error(f"❌ Failed to save LoRA adapters: {e}")
            raise
    
    def load_lora_adapters(self, adapter_path: str):
        """Load LoRA adapters for inference or further training"""
        logger.info(f"📥 Loading LoRA adapters from: {adapter_path}")
        
        try:
            from peft import PeftModel
            
            # Load base model first
            if self.model is None:
                self.load_model_and_tokenizer()
            
            # Load LoRA adapters
            self.model = PeftModel.from_pretrained(self.model, adapter_path)
            logger.info("✅ LoRA adapters loaded successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to load LoRA adapters: {e}")
            raise


def main():
    """Run Stage 1 DPO training"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Train Stage 1 model with DPO")
    parser.add_argument("--model", default="Qwen/Qwen2.5-32B", help="Base model to use")
    parser.add_argument("--epochs", type=int, default=3, help="Number of training epochs")
    parser.add_argument("--batch-size", type=int, default=4, help="Batch size")
    parser.add_argument("--lr", type=float, default=5e-5, help="Learning rate")
    parser.add_argument("--run-name", help="Name for this training run")
    parser.add_argument("--quick-test", action="store_true", help="Quick test with 1 epoch")
    
    args = parser.parse_args()
    
    if args.quick_test:
        args.epochs = 1
        logger.info("🧪 Running quick test with 1 epoch")
    
    # Check if training data exists
    data_dir = BASE_DIR / "data" / "stage1"
    train_file = data_dir / "train_preference_pairs.jsonl"
    
    if not train_file.exists():
        logger.error(f"❌ Training data not found: {train_file}")
        logger.error("🚨 Please run generate_stage1_data.py first!")
        return
    
    # Create trainer
    trainer = Stage1DPOTrainer(args.model)
    
    # Run training
    try:
        summary = trainer.train(
            num_epochs=args.epochs,
            batch_size=args.batch_size,
            learning_rate=args.lr,
            run_name=args.run_name
        )
        
        # Print final summary
        print("\n" + "="*60)
        print("🎉 STAGE 1 TRAINING COMPLETED!")
        print("="*60)
        print(f"Model: {summary['base_model']}")
        print(f"Final Loss: {summary['results']['train_loss']:.4f}")
        print(f"Training Steps: {summary['results']['train_steps']}")
        print(f"LoRA Adapters: {summary['paths']['lora_adapters']}")
        print("="*60)
        print("\n🚀 Ready for Stage 1 evaluation!")
        
    except Exception as e:
        logger.error(f"❌ Training failed: {e}")
        raise


if __name__ == "__main__":
    main()