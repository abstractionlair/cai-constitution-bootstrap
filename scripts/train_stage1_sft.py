#!/usr/bin/env python3
"""
SFT (Supervised Fine-Tuning) training with proper loss masking for Stage 1
Trains only on Response: ... END tokens, masks instruction tokens
"""

import json
import logging
import torch
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import sys
import os
from dataclasses import dataclass, field
from datasets import Dataset
from transformers import (
    AutoTokenizer,
    TrainingArguments,
    DataCollatorForLanguageModeling,
    Trainer
)
from peft import LoraConfig, get_peft_model, TaskType

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Setup paths
BASE_DIR = Path(os.getenv('CAI_BASE_DIR', '/workspace/runs/stage1_20250911_131105/code'))
ARTIFACTS_DIR = BASE_DIR / "artifacts"
CHECKPOINTS_DIR = BASE_DIR / "checkpoints"
sys.path.insert(0, str(BASE_DIR / 'scripts'))

# Import CleanModelLoader
from utils.clean_model_loader import CleanModelLoader

# Import validation utilities
from utils.data_validation import load_and_validate_sft_data

# Create directories
CHECKPOINTS_DIR.mkdir(parents=True, exist_ok=True)

@dataclass
class SFTConfig:
    """Configuration for SFT training"""
    model_name: str = "Qwen/Qwen2.5-32B"
    output_dir: str = field(default_factory=lambda: str(CHECKPOINTS_DIR / "stage1_sft"))
    num_train_epochs: int = 1
    per_device_train_batch_size: int = 1
    per_device_eval_batch_size: int = 1
    gradient_accumulation_steps: int = 8
    learning_rate: float = 2e-5
    warmup_steps: int = 10
    logging_steps: int = 5
    save_steps: int = 50
    eval_steps: int = 50
    max_length: int = 512
    lora_r: int = 16
    lora_alpha: int = 32
    lora_dropout: float = 0.1
    load_in_8bit: bool = True
    gradient_checkpointing: bool = True

class SFTDataCollator:
    """Custom data collator with loss masking for instruction/response format"""
    
    def __init__(self, tokenizer, max_length=512):
        self.tokenizer = tokenizer
        self.max_length = max_length
        
        # Add pad token if not exists
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token
    
    def find_token_sequence(self, tokens: List[int], pattern: List[int]) -> Optional[int]:
        """Find start index of pattern within tokens"""
        for i in range(len(tokens) - len(pattern) + 1):
            if tokens[i:i+len(pattern)] == pattern:
                return i
        return None
    
    def __call__(self, features: List[Dict[str, Any]]) -> Dict[str, torch.Tensor]:
        """Process batch with proper loss masking"""
        
        batch_input_ids = []
        batch_attention_mask = []
        batch_labels = []
        
        for feature in features:
            # Get the full text and tokenize
            full_text = feature['formatted_text']
            prompt = feature['prompt']  # "Instruction: X\nResponse:"
            
            # Tokenize full sequence
            full_encoding = self.tokenizer(
                full_text,
                truncation=True,
                max_length=self.max_length,
                padding=False,
                return_tensors=None
            )
            
            # Tokenize just the prompt to find boundary
            prompt_encoding = self.tokenizer(
                prompt,
                truncation=True,
                max_length=self.max_length,
                padding=False,
                return_tensors=None
            )
            
            input_ids = full_encoding['input_ids']
            attention_mask = full_encoding['attention_mask']
            
            # Create labels with loss masking  
            labels = input_ids.copy()
            
            # More robust approach: look for "Response:" token sequence in context
            # Since tokenization is context-dependent, search for the key tokens
            response_token = self.tokenizer.encode("Response", add_special_tokens=False)[0]  # Should be 2582
            colon_token = self.tokenizer.encode(":", add_special_tokens=False)[0]  # Should be 25
            
            # Find "Response:" sequence in the actual tokens
            mask_until = None
            for i in range(len(input_ids) - 1):
                if input_ids[i] == response_token and input_ids[i + 1] == colon_token:
                    mask_until = i + 2  # Mask up to and including "Response:"
                    break
            
            if mask_until is None:
                # Fallback to original method if sequence not found
                logger.warning("Response: sequence not found in tokens, using fallback masking")
                mask_until = len(prompt_encoding['input_ids'])
            
            # Apply masking (set to -100 to ignore in loss)
            for i in range(min(mask_until, len(labels))):
                labels[i] = -100
            
            # Store processed sequences
            batch_input_ids.append(input_ids)
            batch_attention_mask.append(attention_mask)
            batch_labels.append(labels)
        
        # Pad sequences to same length
        max_len = min(max(len(seq) for seq in batch_input_ids), self.max_length)
        
        padded_input_ids = []
        padded_attention_mask = []
        padded_labels = []
        
        for i in range(len(batch_input_ids)):
            input_ids = batch_input_ids[i][:max_len]
            attention_mask = batch_attention_mask[i][:max_len]
            labels = batch_labels[i][:max_len]
            
            # Pad to max_len
            pad_length = max_len - len(input_ids)
            
            if pad_length > 0:
                input_ids.extend([self.tokenizer.pad_token_id] * pad_length)
                attention_mask.extend([0] * pad_length)
                labels.extend([-100] * pad_length)  # Mask padding in loss
            
            padded_input_ids.append(input_ids)
            padded_attention_mask.append(attention_mask)
            padded_labels.append(labels)
        
        return {
            'input_ids': torch.tensor(padded_input_ids, dtype=torch.long),
            'attention_mask': torch.tensor(padded_attention_mask, dtype=torch.long),
            'labels': torch.tensor(padded_labels, dtype=torch.long)
        }

def load_sft_dataset() -> List[Dict[str, Any]]:
    """Load and validate the most recent SFT training dataset"""
    logger.info("📂 Loading and validating SFT training data...")
    
    # Use validation utility to load and validate data
    data = load_and_validate_sft_data(ARTIFACTS_DIR)
    
    logger.info(f"✅ Loaded and validated {len(data)} SFT training examples")
    return data

def setup_model_and_tokenizer(config: SFTConfig):
    """Setup model and tokenizer with quantization and LoRA"""
    
    logger.info(f"🔧 Setting up model: {config.model_name}")
    
    # Load model via CleanModelLoader
    logger.info("🤖 Loading model with 8-bit quantization...")
    loader = CleanModelLoader(config.model_name, load_in_8bit=config.load_in_8bit)
    model, tokenizer, provenance = loader.load()
    logger.info(f"📋 Loader version: {provenance['loader_version'][:8]}")
    
    # Setup LoRA
    logger.info("🔧 Setting up LoRA adapters...")
    lora_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=config.lora_r,
        lora_alpha=config.lora_alpha,
        lora_dropout=config.lora_dropout,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        bias="none"
    )
    
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()
    
    if config.gradient_checkpointing:
        model.enable_input_require_grads()
        model.gradient_checkpointing_enable()
    
    logger.info("✅ Model and tokenizer setup complete")
    return model, tokenizer

def create_sft_dataset(sft_data: List[Dict[str, Any]], tokenizer) -> Dataset:
    """Create Hugging Face dataset from SFT data"""
    
    logger.info("📊 Creating SFT dataset...")
    
    # Prepare data for training
    formatted_data = []
    for example in sft_data:
        formatted_data.append({
            'formatted_text': example['formatted_text'],
            'prompt': example['prompt'],
            'instruction': example['instruction'],
            'response': example['response'],
            'instruction_type': example['instruction_type']
        })
    
    # Create dataset
    dataset = Dataset.from_list(formatted_data)
    
    logger.info(f"✅ Created dataset with {len(dataset)} examples")
    return dataset

def run_sft_training(epochs=3, lr_schedule="cosine", eval_split=0.2):
    """Run SFT training with proper loss masking"""
    
    logger.info("🚀 Starting Stage 1 SFT training")
    
    # Load config and update with parameters
    config = SFTConfig()
    config.num_train_epochs = epochs
    
    # Load dataset
    sft_data = load_sft_dataset()
    
    # Setup model and tokenizer
    model, tokenizer = setup_model_and_tokenizer(config)
    
    # Create dataset
    dataset = create_sft_dataset(sft_data, tokenizer)
    
    # Split dataset with specified split
    dataset = dataset.train_test_split(test_size=eval_split, seed=42)
    train_dataset = dataset['train']
    eval_dataset = dataset['test']
    
    logger.info(f"📊 Train samples: {len(train_dataset)}, Eval samples: {len(eval_dataset)}")
    
    # Create data collator with loss masking
    data_collator = SFTDataCollator(tokenizer, max_length=config.max_length)
    
    # Training arguments
    training_args = TrainingArguments(
        output_dir=config.output_dir,
        num_train_epochs=config.num_train_epochs,
        per_device_train_batch_size=config.per_device_train_batch_size,
        per_device_eval_batch_size=config.per_device_eval_batch_size,
        gradient_accumulation_steps=config.gradient_accumulation_steps,
        learning_rate=config.learning_rate,
        warmup_steps=config.warmup_steps,
        lr_scheduler_type=lr_schedule,  # cosine, linear, or constant
        logging_steps=config.logging_steps,
        eval_steps=config.eval_steps,
        save_steps=config.save_steps,
        eval_strategy="steps",
        save_strategy="steps",
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        greater_is_better=False,
        remove_unused_columns=False,
        dataloader_pin_memory=False,
        gradient_checkpointing=config.gradient_checkpointing,
        report_to=[]  # Disable wandb
    )
    
    # Create trainer
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        data_collator=data_collator,
        tokenizer=tokenizer,
    )
    
    logger.info("✅ SFT trainer setup complete")
    
    # Start training
    logger.info("🔥 Starting SFT training with loss masking...")
    start_time = time.time()
    
    try:
        # Train the model
        trainer.train()
        
        training_time = time.time() - start_time
        logger.info(f"✅ Training completed in {training_time/60:.1f} minutes")
        
        # Save the final model
        final_model_dir = Path(config.output_dir) / "final"
        trainer.save_model(str(final_model_dir))
        
        logger.info(f"💾 Final model saved to {final_model_dir}")
        
        # Save training summary
        training_summary = {
            'model_name': config.model_name,
            'training_method': 'SFT_with_loss_masking',
            'training_samples': len(train_dataset),
            'eval_samples': len(eval_dataset),
            'epochs': config.num_train_epochs,
            'learning_rate': config.learning_rate,
            'batch_size': config.per_device_train_batch_size * config.gradient_accumulation_steps,
            'lora_config': {
                'r': config.lora_r,
                'alpha': config.lora_alpha,
                'dropout': config.lora_dropout
            },
            'training_time_minutes': training_time / 60,
            'final_model_path': str(final_model_dir),
            'timestamp': datetime.now().isoformat()
        }
        
        summary_file = ARTIFACTS_DIR / "sft_training_summary.json"
        with open(summary_file, 'w') as f:
            json.dump(training_summary, f, indent=2)
        
        logger.info(f"📋 Training summary saved to {summary_file}")
        
        return trainer, training_summary
        
    except Exception as e:
        logger.error(f"❌ Training failed: {e}")
        raise
    
    finally:
        # Clear GPU memory
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

def main():
    """Main function to run SFT training"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Train SFT model for Stage 1")
    parser.add_argument("--epochs", type=int, default=3, help="Number of training epochs")
    parser.add_argument("--lr-schedule", type=str, default="cosine", 
                       choices=["linear", "cosine", "constant"], help="Learning rate schedule")
    parser.add_argument("--eval-split", type=float, default=0.2, help="Evaluation split ratio")
    args = parser.parse_args()
    
    logger.info(f"🎯 Starting SFT training for Stage 1 (epochs={args.epochs}, lr_schedule={args.lr_schedule})")
    
    try:
        trainer, summary = run_sft_training(args.epochs, args.lr_schedule, args.eval_split)
        
        print(f"""
============================================================
🎉 SFT TRAINING COMPLETE
============================================================

Training Summary:
- Model: {summary['model_name']}
- Method: {summary['training_method']}
- Samples: {summary['training_samples']} train, {summary['eval_samples']} eval
- Time: {summary['training_time_minutes']:.1f} minutes
- Saved to: {summary['final_model_path']}

✅ Ready for DPO training!
""")
        
    except Exception as e:
        logger.error(f"❌ SFT training failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()