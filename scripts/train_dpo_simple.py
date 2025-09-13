#!/usr/bin/env python3
"""
Simplified Stage 1 DPO Training Script
Uses standard TRL DPO trainer without Unsloth complications
"""

import json
import sys
import os
import torch
from pathlib import Path
from datetime import datetime
import logging
from datasets import Dataset
from transformers import TrainingArguments, AutoModelForCausalLM, AutoTokenizer
from trl import DPOTrainer, DPOConfig
from peft import LoraConfig, get_peft_model, TaskType
import time

# Setup paths
BASE_DIR = Path(os.getenv('CAI_BASE_DIR', '/workspace/runs/stage1_20250911_131105/code'))
ARTIFACTS_DIR = BASE_DIR / "artifacts"
CHECKPOINTS_DIR = BASE_DIR / "checkpoints"
sys.path.insert(0, str(BASE_DIR / 'scripts'))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(ARTIFACTS_DIR / 'dpo_simple_training.log')
    ]
)
logger = logging.getLogger(__name__)

def load_preference_pairs():
    """Load the high-quality preference pairs"""
    
    pairs_file = ARTIFACTS_DIR / "logprob_preference_pairs.jsonl"
    
    with open(pairs_file) as f:
        pairs = [json.loads(line) for line in f]
    
    logger.info(f"📝 Loaded {len(pairs)} preference pairs")
    
    # Convert to DPO format
    dpo_data = []
    for pair in pairs:
        dpo_data.append({
            'prompt': pair['instruction'],
            'chosen': pair['chosen'],
            'rejected': pair['rejected']
        })
    
    return dpo_data

def setup_model_and_tokenizer():
    """Setup model and tokenizer with LoRA"""
    
    model_name = "Qwen/Qwen2.5-32B"
    
    logger.info(f"🔧 Setting up model and tokenizer: {model_name}")
    
    # Load tokenizer
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    
    # Load base model with 4-bit quantization
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        load_in_4bit=True,
        device_map="auto",
        trust_remote_code=True,
        torch_dtype=torch.float16
    )
    
    # Setup LoRA for efficient fine-tuning
    lora_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        inference_mode=False,
        r=16,  # LoRA rank
        lora_alpha=32,
        lora_dropout=0.1,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"]
    )
    
    model = get_peft_model(model, lora_config)
    
    logger.info("✅ Standard model + LoRA setup complete")
    logger.info(f"GPU memory: {torch.cuda.max_memory_allocated()/1e9:.1f}GB")
    
    return model, tokenizer

def create_dpo_dataset(preference_pairs, tokenizer):
    """Create dataset for DPO training"""
    
    logger.info("📊 Creating DPO dataset...")
    
    # Format for DPO training - simple prompt format
    formatted_data = []
    
    for pair in preference_pairs:
        formatted_data.append({
            'prompt': f"Instruction: {pair['prompt']}",
            'chosen': pair['chosen'],
            'rejected': pair['rejected']
        })
    
    # Create Hugging Face dataset
    dataset = Dataset.from_list(formatted_data)
    
    logger.info(f"✅ Created dataset with {len(dataset)} examples")
    
    return dataset

def run_dpo_training():
    """Run DPO training with simplified approach"""
    
    logger.info("🚀 Starting simplified Stage 1 DPO training")
    
    # Load preference pairs
    preference_pairs = load_preference_pairs()
    
    # Setup model and tokenizer
    model, tokenizer = setup_model_and_tokenizer()
    
    # Create dataset
    dataset = create_dpo_dataset(preference_pairs, tokenizer)
    
    # Split dataset (80/20 train/eval)
    dataset = dataset.train_test_split(test_size=0.2, seed=42)
    train_dataset = dataset['train']
    eval_dataset = dataset['test']
    
    logger.info(f"📊 Train samples: {len(train_dataset)}, Eval samples: {len(eval_dataset)}")
    
    # Create checkpoints directory
    CHECKPOINTS_DIR.mkdir(parents=True, exist_ok=True)
    
    # DPO-specific configuration
    dpo_args = DPOConfig(
        output_dir=str(CHECKPOINTS_DIR / "stage1_dpo_simple"),
        num_train_epochs=1,  # Start with 1 epoch for testing
        per_device_train_batch_size=1,  # Small batch for 32B model
        per_device_eval_batch_size=1,
        gradient_accumulation_steps=4,  # Effective batch size = 4
        learning_rate=5e-6,  # Very conservative learning rate
        warmup_steps=10,
        logging_steps=5,
        eval_steps=25,
        save_steps=50,
        eval_strategy="steps",
        save_strategy="steps",
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        greater_is_better=False,
        report_to=[],  # Disable wandb
        remove_unused_columns=False,
        dataloader_pin_memory=False,
        fp16=True,  # Enable mixed precision
        gradient_checkpointing=True,  # Save memory
        beta=0.1,  # DPO beta parameter
        max_length=1024,  # Max sequence length
        max_prompt_length=256,  # Shorter prompt length
    )
    
    # Create DPO trainer
    trainer = DPOTrainer(
        model=model,
        args=dpo_args,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        processing_class=tokenizer,
    )
    
    logger.info("✅ DPO trainer setup complete")
    
    # Start training
    logger.info("🔥 Starting DPO training...")
    start_time = time.time()
    
    try:
        # Train the model
        trainer.train()
        
        training_time = time.time() - start_time
        logger.info(f"✅ Training completed in {training_time/60:.1f} minutes")
        
        # Save the final model
        final_model_dir = CHECKPOINTS_DIR / "stage1_dpo_final"
        trainer.save_model(str(final_model_dir))
        
        logger.info(f"💾 Final model saved to {final_model_dir}")
        
        # Save training summary
        training_summary = {
            'model_name': "Qwen/Qwen2.5-32B",
            'training_method': 'DPO_Simple',
            'preference_pairs': len(preference_pairs),
            'train_samples': len(train_dataset),
            'eval_samples': len(eval_dataset),
            'epochs': 1,
            'learning_rate': 5e-6,
            'batch_size': 4,  # effective
            'training_time_minutes': training_time / 60,
            'final_model_path': str(final_model_dir),
            'timestamp': datetime.now().isoformat()
        }
        
        summary_file = ARTIFACTS_DIR / "dpo_simple_training_summary.json"
        with open(summary_file, 'w') as f:
            json.dump(training_summary, f, indent=2)
        
        logger.info(f"📋 Training summary saved to {summary_file}")
        
        return trainer, training_summary
        
    except Exception as e:
        logger.error(f"❌ Training failed: {e}")
        raise

def main():
    """Main training function"""
    
    try:
        trainer, summary = run_dpo_training()
        
        if trainer and summary:
            print("\n" + "="*60)
            print("🎉 STAGE 1 SIMPLE DPO TRAINING COMPLETE")
            print("="*60)
            print(f"Training time: {summary['training_time_minutes']:.1f} minutes")
            print(f"Preference pairs used: {summary['preference_pairs']}")
            print(f"Final model: {summary['final_model_path']}")
            print("\nFiles created:")
            print("  - Stage 1 LoRA adapter (checkpoints/stage1_dpo_final/)")
            print("  - Training logs (artifacts/dpo_simple_training.log)")
            print("  - Training summary (artifacts/dpo_simple_training_summary.json)")
            print("\n✅ Ready for Stage 1 evaluation!")
        else:
            print("❌ Training failed - check logs for details")
            
    except Exception as e:
        logger.error(f"❌ Training script failed: {e}")
        print(f"\n❌ Training failed: {e}")
        raise

if __name__ == "__main__":
    main()