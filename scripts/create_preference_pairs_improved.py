#!/usr/bin/env python3
"""
Create improved preference pairs with diverse negatives for DPO training
Combines SFT model responses (chosen) with diverse negative examples (rejected)
"""

import json
import logging
import torch
import random
from pathlib import Path
from typing import List, Dict, Any, Tuple
from datetime import datetime
from tqdm import tqdm
import sys
import os
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import PeftModel

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Setup paths
BASE_DIR = Path(os.getenv('CAI_BASE_DIR', '/workspace/runs/stage1_20250911_131105/code'))
ARTIFACTS_DIR = BASE_DIR / "artifacts"
CHECKPOINTS_DIR = BASE_DIR / "checkpoints"
sys.path.insert(0, str(BASE_DIR / 'scripts'))

# Import validation utilities  
from utils.data_validation import load_and_validate_sft_data, load_and_validate_negatives

class PreferencePairCreator:
    """Create preference pairs from SFT responses and diverse negatives"""
    
    def __init__(self, sft_model_path: str = None):
        """Initialize with optional SFT model for generating responses"""
        self.sft_model_path = sft_model_path
        self.model = None
        self.tokenizer = None
        
        if sft_model_path:
            logger.info(f"🤖 Will load SFT model from {sft_model_path}")
        else:
            logger.info("📝 Will use existing SFT responses")
    
    def load_sft_model(self):
        """Load the SFT model for generating responses"""
        if not self.sft_model_path:
            return
            
        logger.info(f"🔧 Loading SFT model from {self.sft_model_path}")
        
        # Quantization config
        bnb_config = BitsAndBytesConfig(
            load_in_8bit=True,
            bnb_8bit_use_double_quant=True,
            bnb_8bit_quant_type="nf8",
            bnb_8bit_compute_dtype=torch.bfloat16
        )
        
        # Load base model
        base_model = AutoModelForCausalLM.from_pretrained(
            "Qwen/Qwen2.5-32B",
            quantization_config=bnb_config,
            device_map="auto",
            trust_remote_code=True,
            dtype=torch.bfloat16
        )
        
        # Load tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(
            "Qwen/Qwen2.5-32B",
            trust_remote_code=True,
            padding_side='right'
        )
        
        # Disable chat template
        self.tokenizer.chat_template = None
        
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        
        # Load LoRA adapters
        self.model = PeftModel.from_pretrained(base_model, self.sft_model_path)
        
        logger.info("✅ SFT model loaded successfully")
    
    def generate_sft_response(self, instruction: str) -> str:
        """Generate response using SFT model"""
        if not self.model:
            raise ValueError("SFT model not loaded")
        
        # Format prompt
        prompt = f"Instruction: {instruction}\\nResponse:"
        
        # Tokenize
        inputs = self.tokenizer(
            prompt,
            return_tensors="pt",
            truncation=True,
            max_length=256
        ).to(self.model.device)
        
        # Generate
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=150,
                temperature=0.7,
                do_sample=True,
                pad_token_id=self.tokenizer.pad_token_id,
                eos_token_id=self.tokenizer.eos_token_id,
                stop_strings=["END", "\\n\\n", "Instruction:"],
                tokenizer=self.tokenizer
            )
        
        # Decode response
        response = self.tokenizer.decode(outputs[0][inputs['input_ids'].shape[1]:], skip_special_tokens=True)
        response = response.strip().split("END")[0].strip()
        
        return response
    
    def load_sft_examples(self) -> List[Dict[str, Any]]:
        """Load and validate SFT training examples"""
        logger.info("📂 Loading and validating SFT examples...")
        
        # Use validation utility to load and validate data
        examples = load_and_validate_sft_data(ARTIFACTS_DIR)
        
        logger.info(f"✅ Loaded and validated {len(examples)} SFT examples")
        return examples
    
    def load_diverse_negatives(self) -> List[Dict[str, Any]]:
        """Load and validate diverse negative examples"""
        logger.info("📂 Loading and validating diverse negatives...")
        
        # Use validation utility to load and validate data
        negatives = load_and_validate_negatives(ARTIFACTS_DIR)
        
        logger.info(f"✅ Loaded and validated {len(negatives)} diverse negatives")
        return negatives
    
    def evaluate_pair_with_logprob(self, prompt: str, chosen: str, rejected: str) -> Tuple[bool, float]:
        """Evaluate preference pair using log-probability comparison"""
        if not self.model:
            # Skip evaluation if no model loaded
            return True, 1.0
        
        # Format sequences
        chosen_seq = f"{prompt} {chosen}\\nEND"
        rejected_seq = f"{prompt} {rejected}\\nEND"
        
        # Get log probabilities
        chosen_logprob = self.get_sequence_logprob(chosen_seq)
        rejected_logprob = self.get_sequence_logprob(rejected_seq)
        
        # Check if chosen is preferred (higher log-prob)
        margin = chosen_logprob - rejected_logprob
        confident = margin > 0.5  # Confidence threshold
        
        return confident, abs(margin)
    
    def get_sequence_logprob(self, sequence: str) -> float:
        """Get log probability of a sequence"""
        inputs = self.tokenizer(sequence, return_tensors="pt").to(self.model.device)
        
        with torch.no_grad():
            outputs = self.model(**inputs, labels=inputs["input_ids"])
            loss = outputs.loss
        
        return -loss.item()
    
    def create_preference_pairs(self, max_pairs: int = 500) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Create preference pairs from SFT examples and diverse negatives"""
        
        logger.info(f"🎯 Creating preference pairs with diverse negatives")
        
        # Load data
        sft_examples = self.load_sft_examples()
        diverse_negatives = self.load_diverse_negatives()
        
        # Group negatives by instruction
        negatives_by_instruction = {}
        for neg in diverse_negatives:
            instruction = neg['instruction']
            if instruction not in negatives_by_instruction:
                negatives_by_instruction[instruction] = []
            negatives_by_instruction[instruction].append(neg)
        
        # Create preference pairs
        preference_pairs = []
        stats = {
            'total_pairs': 0,
            'confident_pairs': 0,
            'negative_types': {},
            'avg_margin': 0.0
        }
        
        total_margin = 0.0
        
        for sft_example in tqdm(sft_examples, desc="Creating preference pairs"):
            instruction = sft_example['instruction']
            
            # Get SFT response as chosen
            if self.model:
                # Generate new response with SFT model
                chosen_response = self.generate_sft_response(instruction)
            else:
                # Use existing response
                chosen_response = sft_example['response']
            
            # Get negatives for this instruction
            if instruction not in negatives_by_instruction:
                continue
            
            negatives = negatives_by_instruction[instruction]
            
            # Create pairs with each negative
            for negative in negatives:
                rejected_response = negative['negative_response']
                negative_type = negative['negative_type']
                
                # Format for DPO
                prompt = f"Instruction: {instruction}\\nResponse:"
                chosen = f" {chosen_response}\\nEND"
                rejected = f" {rejected_response}\\nEND"
                
                # Evaluate pair quality
                confident, margin = self.evaluate_pair_with_logprob(prompt, chosen, rejected)
                
                # Create pair
                pair = {
                    'prompt': prompt,
                    'chosen': chosen,
                    'rejected': rejected,
                    'instruction': instruction,
                    'instruction_type': sft_example['instruction_type'],
                    'negative_type': negative_type,
                    'confident': confident,
                    'margin': margin,
                    'timestamp': datetime.now().isoformat()
                }
                
                preference_pairs.append(pair)
                
                # Update stats
                stats['total_pairs'] += 1
                if confident:
                    stats['confident_pairs'] += 1
                
                stats['negative_types'][negative_type] = stats['negative_types'].get(negative_type, 0) + 1
                total_margin += margin
                
                # Limit pairs if specified
                if len(preference_pairs) >= max_pairs:
                    break
            
            if len(preference_pairs) >= max_pairs:
                break
        
        # Finalize stats
        if stats['total_pairs'] > 0:
            stats['avg_margin'] = total_margin / stats['total_pairs']
            stats['confidence_rate'] = stats['confident_pairs'] / stats['total_pairs']
        
        # Shuffle pairs for training
        random.shuffle(preference_pairs)
        
        logger.info(f"✅ Created {len(preference_pairs)} preference pairs")
        return preference_pairs, stats
    
    def cleanup(self):
        """Clean up model resources"""
        if self.model:
            del self.model
        if self.tokenizer:
            del self.tokenizer
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

def load_latest_sft_checkpoint() -> str:
    """Find the latest SFT checkpoint"""
    
    sft_checkpoints = list(CHECKPOINTS_DIR.glob("stage1_sft/final"))
    
    if sft_checkpoints:
        return str(sft_checkpoints[0])
    
    # Look for other SFT directories
    sft_dirs = list(CHECKPOINTS_DIR.glob("stage1_sft*"))
    for sft_dir in sft_dirs:
        final_dir = sft_dir / "final"
        if final_dir.exists():
            return str(final_dir)
    
    logger.warning("⚠️ No SFT checkpoint found, will use existing responses")
    return None

def main():
    """Main function to create improved preference pairs"""
    logger.info("🚀 Starting improved preference pair creation")
    
    try:
        # Find SFT checkpoint
        sft_checkpoint = load_latest_sft_checkpoint()
        
        # Create preference pairs
        creator = PreferencePairCreator(sft_model_path=sft_checkpoint)
        
        if sft_checkpoint:
            creator.load_sft_model()
        
        pairs, stats = creator.create_preference_pairs(max_pairs=500)
        
        # Save pairs
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pairs_file = ARTIFACTS_DIR / f"preference_pairs_improved_{timestamp}.jsonl"
        
        with open(pairs_file, 'w') as f:
            for pair in pairs:
                f.write(json.dumps(pair) + '\n')
        
        # Create summary
        summary = f"""📊 Improved Preference Pairs Created
=====================================

Total Pairs: {stats['total_pairs']}
Confident Pairs: {stats['confident_pairs']} ({stats.get('confidence_rate', 0):.1%})
Average Margin: {stats['avg_margin']:.3f}

Negative Type Distribution:
"""
        
        for neg_type, count in sorted(stats['negative_types'].items()):
            percentage = count / stats['total_pairs'] * 100
            summary += f"  {neg_type}: {count} ({percentage:.1f}%)\\n"
        
        summary += f"""
Sample Pairs:
-------------
"""
        
        # Show sample pairs by type
        for neg_type in list(stats['negative_types'].keys())[:3]:
            type_pairs = [p for p in pairs if p['negative_type'] == neg_type]
            if type_pairs:
                pair = type_pairs[0]
                summary += f"""
{neg_type.upper()} Example:
  Prompt: {pair['prompt']}
  Chosen: {pair['chosen'].strip()}
  Rejected: {pair['rejected'].strip()}
  Confident: {pair['confident']}, Margin: {pair['margin']:.3f}
"""
        
        # Save summary
        summary_file = ARTIFACTS_DIR / f"preference_pairs_summary_{timestamp}.txt"
        with open(summary_file, 'w') as f:
            f.write(summary)
        
        logger.info(f"💾 Pairs saved to {pairs_file}")
        logger.info(f"📋 Summary saved to {summary_file}")
        
        print(f"\\n{summary}")
        print(f"\\n✅ Preference pair creation complete!")
        
        return pairs, stats
        
    except Exception as e:
        logger.error(f"❌ Failed to create preference pairs: {e}")
        raise
    
    finally:
        # Cleanup
        if 'creator' in locals():
            creator.cleanup()

if __name__ == "__main__":
    main()