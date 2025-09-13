#!/usr/bin/env python3
"""
Train DPO directly from base model (not SFT) for methodology comparison
This enables comparing SFT→DPO vs DPO-only approaches
"""

import json
import logging
import argparse
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import sys
import os

import torch
from unsloth import FastLanguageModel
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig, TrainingArguments
from trl import DPOTrainer
from datasets import Dataset
import wandb

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Setup paths
BASE_DIR = Path(os.getenv('CAI_BASE_DIR', '/workspace/runs/stage1_20250911_131105/code'))
ARTIFACTS_DIR = BASE_DIR / "artifacts"
CHECKPOINTS_DIR = BASE_DIR / "checkpoints"
sys.path.insert(0, str(BASE_DIR / 'scripts'))

# Create directories
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
CHECKPOINTS_DIR.mkdir(parents=True, exist_ok=True)


class DPOOnlyTrainer:
    """DPO training directly from base model (no SFT first)"""
    
    def __init__(self, model_name="Qwen/Qwen2.5-32B", max_length=1024):
        """Initialize trainer with base model"""
        self.model_name = model_name
        self.max_length = max_length
        self.model = None
        self.tokenizer = None
        
        logger.info(f"🏗️ Initializing DPO-only trainer with {model_name}")
    
    def setup_base_model_for_dpo(self):
        """Load base model for DPO training (not SFT checkpoint)"""
        logger.info("🤖 Loading base model for DPO training...")
        
        # Use Unsloth for efficient training
        self.model, self.tokenizer = FastLanguageModel.from_pretrained(
            model_name=self.model_name,
            max_seq_length=self.max_length,
            dtype=None,  # Auto-detect
            load_in_4bit=True,
            device_map="auto"
        )
        
        # Configure for training
        self.model = FastLanguageModel.get_peft_model(
            self.model,
            r=16,  # LoRA rank
            target_modules=["q_proj", "k_proj", "v_proj", "o_proj", 
                           "gate_proj", "up_proj", "down_proj"],
            lora_alpha=16,
            lora_dropout=0.0,
            bias="none",
            use_gradient_checkpointing="unsloth",
            random_state=3407,
        )
        
        # Add pad token if missing  
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
            
        logger.info("✅ Base model loaded and configured for DPO training")
    
    def load_preference_pairs(self) -> List[Dict[str, Any]]:
        """Load and validate preference pairs created by create_preference_pairs_improved.py"""
        from utils.data_validation import load_and_validate_preference_pairs
        
        logger.info("📂 Loading and validating preference pairs...")
        
        # Use validation utility to load and validate data
        pairs = load_and_validate_preference_pairs(ARTIFACTS_DIR)
        
        logger.info(f"✅ Loaded and validated {len(pairs)} preference pairs")
        return pairs
    
    def prepare_dpo_dataset(self, pairs: List[Dict[str, Any]]) -> Dataset:
        """Prepare dataset in DPO format"""
        logger.info("🛠️ Preparing DPO dataset...")
        
        # Convert to DPO format
        dpo_data = {
            'prompt': [],
            'chosen': [], 
            'rejected': []
        }
        
        for pair in pairs:
            # Use consistent prompting format
            prompt = f"Instruction: {pair['instruction']}\nResponse: "
            
            dpo_data['prompt'].append(prompt)
            dpo_data['chosen'].append(pair['chosen'])
            dpo_data['rejected'].append(pair['rejected'])
        
        dataset = Dataset.from_dict(dpo_data)
        logger.info(f"✅ DPO dataset prepared: {len(dataset)} pairs")
        
        return dataset
    
    def train_dpo_only(self, pairs: List[Dict[str, Any]], output_dir: str):
        """Train DPO directly from base model"""
        logger.info("🚀 Starting DPO-only training (from base model)...")
        
        # Prepare dataset
        dataset = self.prepare_dpo_dataset(pairs)
        
        # Training arguments - same as SFT→DPO for fair comparison
        training_args = TrainingArguments(
            output_dir=output_dir,
            num_train_epochs=3,
            per_device_train_batch_size=1,  # Adjust based on memory
            gradient_accumulation_steps=8,
            learning_rate=5e-6,  # Lower LR for stability
            lr_scheduler_type="cosine",
            warmup_ratio=0.1,
            logging_steps=10,
            save_steps=100,
            save_total_limit=2,
            dataloader_drop_last=False,
            bf16=torch.cuda.is_available() and torch.cuda.is_bf16_supported(),
            fp16=not (torch.cuda.is_available() and torch.cuda.is_bf16_supported()),
            remove_unused_columns=False,
            report_to=["wandb"] if wandb.api.api_key else [],
            run_name="stage1_dpo_only",
            load_best_model_at_end=False,
        )
        
        # Initialize DPO trainer
        trainer = DPOTrainer(
            model=self.model,
            args=training_args,
            train_dataset=dataset,
            tokenizer=self.tokenizer,
            max_length=self.max_length,
            max_prompt_length=512,
            max_target_length=512,
            beta=0.1,  # DPO temperature parameter
            loss_type="sigmoid",
            label_smoothing=0.0,
            
            # Important: Use same formatting as SFT→DPO
            formatting_func=None  # Dataset already formatted
        )
        
        # Train
        start_time = time.time()
        trainer.train()
        training_time = time.time() - start_time
        
        # Save model
        trainer.save_model(output_dir)
        self.tokenizer.save_pretrained(output_dir)
        
        # Save training metadata
        metadata = {
            'model_type': 'dpo_only',
            'base_model': self.model_name,
            'training_approach': 'direct_dpo_from_base',
            'training_time_seconds': training_time,
            'num_preference_pairs': len(pairs),
            'training_args': training_args.to_dict(),
            'timestamp': datetime.now().isoformat(),
            'comparison_purpose': 'baseline_for_sft_dpo_methodology'
        }
        
        metadata_file = Path(output_dir) / "dpo_only_metadata.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"✅ DPO-only training complete in {training_time:.1f}s")
        logger.info(f"📁 Model saved to {output_dir}")
        
        return training_time
    
    def run_dpo_only_pipeline(self):
        """Run complete DPO-only training pipeline"""
        logger.info("🎯 Starting DPO-only baseline training")
        
        # Setup model
        self.setup_base_model_for_dpo()
        
        # Load preference pairs (same as SFT→DPO approach)
        pairs = self.load_preference_pairs()
        
        # Output directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = str(CHECKPOINTS_DIR / f"stage1_dpo_only_{timestamp}")
        
        # Train DPO directly on base model
        training_time = self.train_dpo_only(pairs, output_dir)
        
        # Summary
        summary = {
            'approach': 'dpo_only',
            'base_model': self.model_name,
            'preference_pairs': len(pairs),
            'training_time': training_time,
            'output_dir': output_dir,
            'purpose': 'baseline_comparison_for_sft_dpo_methodology'
        }
        
        # Save summary
        summary_file = ARTIFACTS_DIR / f"dpo_only_summary_{timestamp}.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2)
        
        logger.info(f"🎉 DPO-only baseline training complete!")
        logger.info(f"📊 Summary saved to {summary_file}")
        
        return summary


def main():
    """Main function for DPO-only training"""
    parser = argparse.ArgumentParser(description="Train DPO directly from base model")
    parser.add_argument("--model", default="Qwen/Qwen2.5-32B", help="Base model to use")
    parser.add_argument("--max-length", type=int, default=1024, help="Maximum sequence length")
    args = parser.parse_args()
    
    # Initialize and run
    trainer = DPOOnlyTrainer(model_name=args.model, max_length=args.max_length)
    summary = trainer.run_dpo_only_pipeline()
    
    print(f"\n✅ DPO-only training summary:")
    print(f"   Approach: {summary['approach']}")
    print(f"   Training time: {summary['training_time']:.1f}s")
    print(f"   Output: {summary['output_dir']}")
    print(f"   Purpose: {summary['purpose']}")


if __name__ == "__main__":
    main()