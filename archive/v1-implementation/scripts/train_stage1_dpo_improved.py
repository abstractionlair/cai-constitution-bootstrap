#!/usr/bin/env python3
"""
Improved DPO training starting from SFT checkpoint with diverse preference pairs
Uses the SFT model as both starting point and reference model
"""

import json
import logging
import torch
import time
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
import sys
import os
from datasets import Dataset
from transformers import AutoTokenizer
from trl import DPOConfig, DPOTrainer
from peft import LoraConfig, get_peft_model, TaskType, PeftModel

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
from utils.data_validation import load_and_validate_preference_pairs

# Create directories
CHECKPOINTS_DIR.mkdir(parents=True, exist_ok=True)

def load_preference_pairs() -> List[Dict[str, Any]]:
    """Load and validate the most recent improved preference pairs"""
    logger.info("📂 Loading and validating preference pairs...")
    
    # Use validation utility to load and validate data
    pairs = load_and_validate_preference_pairs(ARTIFACTS_DIR)
    
    logger.info(f"✅ Loaded and validated {len(pairs)} preference pairs")
    return pairs

def find_sft_checkpoint() -> str:
    """Find the SFT checkpoint to start from"""
    
    sft_checkpoints = list(CHECKPOINTS_DIR.glob("stage1_sft/final"))
    
    if sft_checkpoints:
        return str(sft_checkpoints[0])
    
    # Look for other SFT directories
    sft_dirs = list(CHECKPOINTS_DIR.glob("stage1_sft*"))
    for sft_dir in sft_dirs:
        final_dir = sft_dir / "final"
        if final_dir.exists():
            return str(final_dir)
    
    raise FileNotFoundError("No SFT checkpoint found. Run SFT training first.")

def setup_model_and_tokenizer(sft_checkpoint_path: str):
    """Setup model and tokenizer from SFT checkpoint"""
    
    logger.info(f"🔧 Loading SFT checkpoint: {sft_checkpoint_path}")
    
    # Load base model via CleanModelLoader
    logger.info("🤖 Loading base model with quantization...")
    loader = CleanModelLoader("Qwen/Qwen2.5-32B", load_in_8bit=True)
    base_model, tokenizer, provenance = loader.load()
    logger.info(f"📋 Loader version: {provenance['loader_version'][:8]}")
    
    # Load SFT LoRA adapters
    logger.info("🔌 Loading SFT LoRA adapters...")
    model = PeftModel.from_pretrained(base_model, sft_checkpoint_path)
    
    # Merge LoRA weights for DPO training
    logger.info("🔗 Merging LoRA weights...")
    model = model.merge_and_unload()
    
    # Add new LoRA for DPO training
    logger.info("⚙️ Adding new LoRA for DPO...")
    lora_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=16,
        lora_alpha=32,
        lora_dropout=0.1,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        bias="none"
    )
    
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()
    
    # Enable gradient checkpointing
    model.enable_input_require_grads()
    model.gradient_checkpointing_enable()
    
    logger.info("✅ Model and tokenizer setup complete")
    return model, tokenizer

def create_dpo_dataset(preference_pairs: List[Dict[str, Any]], tokenizer) -> Dataset:
    """Create dataset for DPO training - handles both DPO format and original format"""
    
    logger.info("📊 Creating DPO dataset from preference pairs...")
    
    # Check format of first pair
    first_pair = preference_pairs[0]
    has_prompt = 'prompt' in first_pair
    
    # Filter confident pairs for training (if confidence info exists)
    confident_pairs = [p for p in preference_pairs if p.get('confident', True)]
    logger.info(f"📈 Using {len(confident_pairs)} confident pairs out of {len(preference_pairs)} total")
    
    # Format for DPO training
    formatted_data = []
    
    for pair in confident_pairs:
        if has_prompt:
            # Already in DPO format
            prompt = pair['prompt']
        else:
            # Original format - create prompt from instruction
            prompt = f"Instruction: {pair['instruction']}\nResponse:"
        
        formatted_data.append({
            'prompt': prompt,
            'chosen': pair['chosen'],
            'rejected': pair['rejected'],
            'instruction_type': pair.get('instruction_type', 'unknown'),
            'negative_type': pair.get('negative_type', 'unknown'),
            'margin': pair.get('margin', 0.0)
        })
    
    # Create Hugging Face dataset
    dataset = Dataset.from_list(formatted_data)
    
    format_type = "DPO format" if has_prompt else "original format"
    logger.info(f"✅ Created DPO dataset with {len(dataset)} examples ({format_type})")
    return dataset

def run_dpo_training():
    """Run improved DPO training from SFT checkpoint"""
    
    logger.info("🚀 Starting improved Stage 1 DPO training")
    
    # Find SFT checkpoint
    sft_checkpoint = find_sft_checkpoint()
    logger.info(f"📍 Using SFT checkpoint: {sft_checkpoint}")
    
    # Load preference pairs
    preference_pairs = load_preference_pairs()
    
    # Setup model and tokenizer
    model, tokenizer = setup_model_and_tokenizer(sft_checkpoint)
    
    # Create reference model (copy of the SFT model)
    logger.info("🔄 Creating reference model...")
    ref_model = None  # DPO will create reference model automatically
    
    # Create dataset
    dataset = create_dpo_dataset(preference_pairs, tokenizer)
    
    # Split dataset (80/20 train/eval)
    dataset = dataset.train_test_split(test_size=0.2, seed=42)
    train_dataset = dataset['train']
    eval_dataset = dataset['test']
    
    logger.info(f"📊 Train samples: {len(train_dataset)}, Eval samples: {len(eval_dataset)}")
    
    # DPO configuration - using DPOConfig as recommended by Codex
    output_dir = CHECKPOINTS_DIR / "stage1_dpo_improved"
    
    # Ensure tokenizer has pad token
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    
    # Create DPOConfig with all parameters (replaces TrainingArguments)
    dpo_config = DPOConfig(
        output_dir=str(output_dir),
        num_train_epochs=1,
        per_device_train_batch_size=1,
        per_device_eval_batch_size=1,
        gradient_accumulation_steps=4,
        learning_rate=5e-6,  # Conservative learning rate
        warmup_steps=10,
        logging_steps=5,
        eval_steps=25,
        save_steps=50,
        save_strategy="steps",
        load_best_model_at_end=False,  # DPO loss may not correlate with eval_loss
        remove_unused_columns=False,
        gradient_checkpointing=True,
        dataloader_pin_memory=False,
        report_to=[],  # Disable wandb
        
        # DPO-specific parameters
        beta=0.1,  # DPO temperature parameter
        max_length=512,
        max_prompt_length=256,
        label_pad_token_id=-100,
        padding_value=tokenizer.pad_token_id,
    )
    
    # Create DPO trainer
    logger.info("🏋️ Setting up DPO trainer...")
    trainer = DPOTrainer(
        model=model,
        ref_model=ref_model,  # Will be created automatically
        args=dpo_config,  # Use DPOConfig instead of TrainingArguments
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        processing_class=tokenizer,  # TRL 0.23.0 still uses processing_class
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
        final_model_dir = output_dir / "final"
        trainer.save_model(str(final_model_dir))
        
        logger.info(f"💾 Final model saved to {final_model_dir}")
        
        # Create summary
        training_summary = {
            'model_name': "Qwen/Qwen2.5-32B",
            'training_method': 'DPO_improved_from_SFT',
            'sft_checkpoint': sft_checkpoint,
            'preference_pairs': len(preference_pairs),
            'confident_pairs': len([p for p in preference_pairs if p.get('confident', True)]),
            'train_samples': len(train_dataset),
            'eval_samples': len(eval_dataset),
            'epochs': 1,
            'learning_rate': 5e-6,
            'beta': 0.1,
            'batch_size': 4,  # effective
            'training_time_minutes': training_time / 60,
            'final_model_path': str(final_model_dir),
            'timestamp': datetime.now().isoformat()
        }
        
        # Add negative type distribution
        neg_type_counts = {}
        for pair in preference_pairs:
            neg_type = pair.get('negative_type', 'unknown')
            neg_type_counts[neg_type] = neg_type_counts.get(neg_type, 0) + 1
        
        training_summary['negative_type_distribution'] = neg_type_counts
        
        summary_file = ARTIFACTS_DIR / "dpo_improved_training_summary.json"
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
    """Main function to run improved DPO training"""
    logger.info("🎯 Starting improved DPO training for Stage 1")
    
    try:
        trainer, summary = run_dpo_training()
        
        print(f"""
============================================================
🎉 IMPROVED DPO TRAINING COMPLETE
============================================================

Training Summary:
- Model: {summary['model_name']}
- Method: {summary['training_method']}
- Started from: {summary['sft_checkpoint']}
- Preference pairs: {summary['preference_pairs']} total, {summary['confident_pairs']} confident
- Training samples: {summary['train_samples']} train, {summary['eval_samples']} eval
- Training time: {summary['training_time_minutes']:.1f} minutes
- Final model: {summary['final_model_path']}

Negative Type Distribution:
""")
        
        for neg_type, count in sorted(summary['negative_type_distribution'].items()):
            percentage = count / summary['preference_pairs'] * 100
            print(f"  {neg_type}: {count} ({percentage:.1f}%)")
        
        print(f"""
✅ Model ready for evaluation!
Next step: Run evaluation on held-out test set
""")
        
    except Exception as e:
        logger.error(f"❌ DPO training failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()