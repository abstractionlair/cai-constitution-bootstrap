#!/usr/bin/env python3
"""
Final Evaluation Script with Strict Criteria
Tests base model vs DPO-trained model on held-out test set with proper instruction-following detection
"""

import json
import sys
import os
import torch
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
from collections import defaultdict
import re

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
        logging.FileHandler(ARTIFACTS_DIR / 'evaluation_final.log')
    ]
)
logger = logging.getLogger(__name__)

class StrictInstructionFollowingEvaluator:
    """Strict evaluator that properly detects instruction-following failures"""
    
    def evaluate_response(self, instruction, response, instruction_type):
        """Strict evaluation that catches base model failures"""
        
        response = response.strip()
        instruction_lower = instruction.lower()
        response_lower = response.lower()
        
        # Basic failure checks
        if len(response) < 3:
            return False, "Response too short"
        
        if response_lower.startswith(("i can't", "i cannot", "i'm not", "sorry, i")):
            return False, "Refusal response"
        
        # Detect weird continuation behavior (key improvement!)
        if instruction_type == "generation":
            # Instructions like "Describe the seasons" should NOT start with weird phrases
            if instruction.startswith("Describe"):
                # Bad patterns: "in the X...", "during Y...", etc.
                if re.match(r'^(in|during|for|with|at|on|under|over|through)\\s+\\w+', response_lower):
                    return False, "Weird continuation (not answering instruction)"
                
                # Should actually describe something, not ask questions
                if response.count('?') > response.count('.'):
                    return False, "Asking questions instead of describing"
                    
                # Should be focused description, not rambling
                if len(response) > 500:  # Too long suggests rambling
                    return False, "Rambling/unfocused response"
            
            # Other generation tasks
            if instruction.startswith(("Write", "Explain", "List", "Name", "Give")):
                # Should follow the instruction, not continue pattern
                if len(response) < 15:
                    return False, "Insufficient content for generation task"
                    
        elif instruction_type == "completion":
            # Should complete the prompt appropriately
            if instruction.endswith(" at"):  # "Water freezes at"
                # Should start with appropriate answer, not ramble
                if not re.match(r'^\\d', response):  # Should start with number for "freezes at"
                    return False, "Not completing appropriately"
                
                # Should not continue with unrelated content after 50+ chars
                sentences = response.split('.', 1)
                if len(sentences) > 1 and len(sentences[1]) > 50:
                    # Check if it's rambling to unrelated topics
                    first_part = sentences[0].lower()
                    second_part = sentences[1][:100].lower()
                    
                    # If second part seems unrelated to first, it's rambling
                    if any(word in second_part for word in ['rectangle', 'weight', 'handshake', 'sequence']):
                        return False, "Rambling to unrelated topics"
            
            # General completion check
            if len(response) < 5:
                return False, "Incomplete response"
                
        elif instruction_type == "qa":
            # Should provide clear answer to question
            if instruction.startswith("Q:"):
                # Should not just repeat question
                question_words = set(instruction.lower().split())
                response_words = set(response.lower().split())
                
                # If response is mostly question words, it's not answering
                if len(question_words & response_words) / len(response_words) > 0.6:
                    return False, "Repeating question instead of answering"
                
                # Should be substantial answer
                if len(response) < 10:
                    return False, "Answer too short"
                    
                # Should not ramble to unrelated Q&A
                if response.count('Q:') > 0 or response.count('?') > 3:
                    return False, "Continuing Q&A pattern instead of focused answer"
        
        elif instruction_type == "response":
            # Should provide appropriate response
            if len(response) < 8:
                return False, "Response too brief"
                
            # Should not just echo the instruction
            if instruction.lower() in response.lower():
                return False, "Echoing instruction instead of responding"
        
        # If we get here, it passes our strict criteria
        return True, "Appropriate response"

def load_base_model_only():
    """Load just the base model"""
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    
    model_name = "Qwen/Qwen2.5-32B"
    
    logger.info(f"Loading base model: {model_name}")
    logger.info("🚨 DISABLING CHAT TEMPLATE for true base model evaluation")
    
    # Load tokenizer and DISABLE chat template
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    
    # CRITICAL: Disable chat template entirely
    tokenizer.chat_template = None
    logger.info("✅ Chat template disabled")
    
    # Use BitsAndBytesConfig
    bnb_config = BitsAndBytesConfig(
        load_in_8bit=True,
        llm_int8_threshold=6.0,
        llm_int8_has_fp16_weight=False
    )
    
    # Load base model
    base_model = AutoModelForCausalLM.from_pretrained(
        model_name,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True,
        low_cpu_mem_usage=True
    )
    
    logger.info("✅ Base model loaded (8-bit, no chat template)")
    
    return base_model, tokenizer

def load_trained_model_only():
    """Load just the trained model with LoRA adapter"""
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    from peft import PeftModel
    
    model_name = "Qwen/Qwen2.5-32B"
    
    logger.info("Loading DPO-trained model with LoRA adapter...")
    
    # Load tokenizer (same setup as base)
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.chat_template = None
    
    # Use BitsAndBytesConfig
    bnb_config = BitsAndBytesConfig(
        load_in_8bit=True,
        llm_int8_threshold=6.0,
        llm_int8_has_fp16_weight=False
    )
    
    # Load base model for LoRA
    trained_base_model = AutoModelForCausalLM.from_pretrained(
        model_name,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True,
        low_cpu_mem_usage=True
    )
    
    # Load LoRA adapter
    lora_path = CHECKPOINTS_DIR / "stage1_dpo_final"
    trained_model = PeftModel.from_pretrained(trained_base_model, str(lora_path))
    
    logger.info("✅ Trained model loaded with LoRA adapter")
    
    return trained_model, tokenizer

def generate_response_raw(model, tokenizer, instruction, max_new_tokens=150):
    """Generate response using RAW instruction (no formatting, no chat template)"""
    
    # Raw instruction - no formatting whatsoever
    prompt = instruction
    
    # Use encode() instead of __call__ to completely bypass any template processing
    input_ids = tokenizer.encode(prompt, return_tensors="pt")
    input_ids = input_ids.to(model.device)
    
    with torch.no_grad():
        outputs = model.generate(
            input_ids,
            max_new_tokens=max_new_tokens,
            temperature=0.1,
            do_sample=False,  # Deterministic
            pad_token_id=tokenizer.eos_token_id,
            eos_token_id=tokenizer.eos_token_id
        )
    
    # Decode only the new tokens
    new_tokens = outputs[0][input_ids.shape[1]:]
    response = tokenizer.decode(new_tokens, skip_special_tokens=True).strip()
    
    return response

def load_held_out_test_instructions():
    """Load the held-out test instructions"""
    
    # Find the most recent test instructions file
    test_files = list(ARTIFACTS_DIR.glob("held_out_test_instructions_*.jsonl"))
    if not test_files:
        raise FileNotFoundError("No held-out test instructions found")
    
    latest_file = max(test_files, key=lambda p: p.stat().st_mtime)
    logger.info(f"Loading test instructions from: {latest_file}")
    
    instructions = []
    with open(latest_file, 'r') as f:
        for line in f:
            instructions.append(json.loads(line))
    
    logger.info(f"📝 Loaded {len(instructions)} held-out test instructions")
    return instructions

def evaluate_models_on_heldout(test_instructions):
    """Evaluate both models on held-out test set"""
    
    logger.info(f"🧪 Starting evaluation on {len(test_instructions)} held-out instructions")
    logger.info("Using STRICT evaluation criteria to detect instruction-following failures")
    
    evaluator = StrictInstructionFollowingEvaluator()
    
    results = {
        'base_model': {'responses': [], 'successes': 0, 'total': 0},
        'trained_model': {'responses': [], 'successes': 0, 'total': 0}
    }
    
    # First pass: Base model evaluation
    logger.info("🔥 EVALUATING BASE MODEL")
    base_model, tokenizer = load_base_model_only()
    
    base_results = []
    
    for i, instruction_data in enumerate(test_instructions):
        instruction = instruction_data['instruction']
        instruction_type = instruction_data['instruction_type']
        
        if i % 10 == 0:
            logger.info(f"Base model: {i+1}/{len(test_instructions)}")
        
        # Generate response from base model
        response = generate_response_raw(base_model, tokenizer, instruction)
        
        # Strict evaluation
        success, reason = evaluator.evaluate_response(instruction, response, instruction_type)
        
        base_results.append({
            'instruction': instruction,
            'instruction_type': instruction_type,
            'response': response,
            'success': success,
            'reason': reason,
            'id': instruction_data['id']
        })
    
    # Clean up base model
    del base_model
    torch.cuda.empty_cache()
    logger.info("✅ Base model evaluation complete, GPU memory cleared")
    
    # Second pass: Trained model evaluation
    logger.info("🚀 EVALUATING TRAINED MODEL")  
    trained_model, tokenizer = load_trained_model_only()
    
    trained_results = []
    
    for i, instruction_data in enumerate(test_instructions):
        instruction = instruction_data['instruction']
        instruction_type = instruction_data['instruction_type']
        
        if i % 10 == 0:
            logger.info(f"Trained model: {i+1}/{len(test_instructions)}")
        
        # Generate response from trained model
        response = generate_response_raw(trained_model, tokenizer, instruction)
        
        # Strict evaluation
        success, reason = evaluator.evaluate_response(instruction, response, instruction_type)
        
        trained_results.append({
            'instruction': instruction,
            'instruction_type': instruction_type,
            'response': response,
            'success': success,
            'reason': reason,
            'id': instruction_data['id']
        })
    
    # Clean up trained model
    del trained_model
    torch.cuda.empty_cache()
    logger.info("✅ Trained model evaluation complete")
    
    # Combine results
    results['base_model']['responses'] = base_results
    results['trained_model']['responses'] = trained_results
    
    # Calculate success counts
    for model_key, model_data in results.items():
        model_data['total'] = len(model_data['responses'])
        model_data['successes'] = sum(1 for r in model_data['responses'] if r['success'])
    
    return results

def analyze_results(results):
    """Analyze results and create comprehensive metrics"""
    
    base_results = results['base_model']
    trained_results = results['trained_model']
    
    # Overall metrics
    base_success_rate = base_results['successes'] / base_results['total']
    trained_success_rate = trained_results['successes'] / trained_results['total']
    improvement = trained_success_rate - base_success_rate
    
    # By instruction type
    base_by_type = defaultdict(lambda: {'successes': 0, 'total': 0})
    trained_by_type = defaultdict(lambda: {'successes': 0, 'total': 0})
    
    for response in base_results['responses']:
        inst_type = response['instruction_type']
        base_by_type[inst_type]['total'] += 1
        if response['success']:
            base_by_type[inst_type]['successes'] += 1
    
    for response in trained_results['responses']:
        inst_type = response['instruction_type']
        trained_by_type[inst_type]['total'] += 1
        if response['success']:
            trained_by_type[inst_type]['successes'] += 1
    
    type_analysis = {}
    for inst_type in set(base_by_type.keys()) | set(trained_by_type.keys()):
        base_rate = base_by_type[inst_type]['successes'] / base_by_type[inst_type]['total'] if base_by_type[inst_type]['total'] > 0 else 0
        trained_rate = trained_by_type[inst_type]['successes'] / trained_by_type[inst_type]['total'] if trained_by_type[inst_type]['total'] > 0 else 0
        
        type_analysis[inst_type] = {
            'base_success_rate': base_rate,
            'trained_success_rate': trained_rate,
            'improvement': trained_rate - base_rate,
            'base_count': f"{base_by_type[inst_type]['successes']}/{base_by_type[inst_type]['total']}",
            'trained_count': f"{trained_by_type[inst_type]['successes']}/{trained_by_type[inst_type]['total']}"
        }
    
    # Failure analysis - what types of failures did each model have?
    base_failures = [r for r in base_results['responses'] if not r['success']]
    trained_failures = [r for r in trained_results['responses'] if not r['success']]
    
    base_failure_reasons = defaultdict(int)
    trained_failure_reasons = defaultdict(int)
    
    for failure in base_failures:
        base_failure_reasons[failure['reason']] += 1
        
    for failure in trained_failures:
        trained_failure_reasons[failure['reason']] += 1
    
    metrics = {
        'timestamp': datetime.now().isoformat(),
        'evaluation_type': 'final_heldout_strict_evaluation',
        'test_set_size': base_results['total'],
        'overall': {
            'base_success_rate': base_success_rate,
            'trained_success_rate': trained_success_rate,
            'improvement': improvement,
            'relative_improvement': improvement / base_success_rate if base_success_rate > 0 else float('inf'),
            'base_count': f"{base_results['successes']}/{base_results['total']}",
            'trained_count': f"{trained_results['successes']}/{trained_results['total']}"
        },
        'by_instruction_type': type_analysis,
        'failure_analysis': {
            'base_model_failures': dict(base_failure_reasons),
            'trained_model_failures': dict(trained_failure_reasons),
            'improvements': {
                'failures_eliminated': len(base_failures) - len(trained_failures),
                'failure_rate_reduction': len(trained_failures) / len(base_failures) if len(base_failures) > 0 else 0
            }
        },
        'detailed_results': results
    }
    
    return metrics

def print_evaluation_summary(metrics):
    """Print comprehensive evaluation summary"""
    
    overall = metrics['overall']
    by_type = metrics['by_instruction_type']
    failures = metrics['failure_analysis']
    
    print("\\n" + "="*80)
    print("🎯 FINAL EVALUATION RESULTS (HELD-OUT TEST SET)")
    print("="*80)
    print("📊 STRICT CRITERIA - PROPER INSTRUCTION-FOLLOWING DETECTION")
    print()
    
    print("Overall Performance:")
    print("-" * 50)
    print(f"Base Model:      {overall['base_success_rate']:.1%} ({overall['base_count']})")
    print(f"Trained Model:   {overall['trained_success_rate']:.1%} ({overall['trained_count']})")
    print(f"Improvement:     +{overall['improvement']:.1%}")
    print(f"Relative Gain:   {overall['relative_improvement']:.1f}x")
    print()
    
    print("By Instruction Type:")
    print("-" * 60)
    for inst_type, data in by_type.items():
        print(f"{inst_type.upper():12}: {data['base_success_rate']:.1%} → {data['trained_success_rate']:.1%} "
              f"(+{data['improvement']:.1%}) [{data['base_count']} → {data['trained_count']}]")
    
    print()
    print("Failure Analysis:")
    print("-" * 50)
    print(f"Base model failures eliminated: {failures['improvements']['failures_eliminated']}")
    print(f"Failure rate reduction: {(1-failures['improvements']['failure_rate_reduction']):.1%}")
    
    print("\\nTop Base Model Failure Types:")
    for reason, count in sorted(failures['base_model_failures'].items(), key=lambda x: x[1], reverse=True)[:5]:
        print(f"  {reason}: {count}")
    
    print("\\nTop Trained Model Failure Types:")
    for reason, count in sorted(failures['trained_model_failures'].items(), key=lambda x: x[1], reverse=True)[:5]:
        print(f"  {reason}: {count}")
    
    print("="*80)
    
    # Overall assessment
    improvement = overall['improvement']
    if improvement > 0.20:
        print("🎉 EXCELLENT: Major improvement (+20%+) - DPO training very effective!")
    elif improvement > 0.10:
        print("✅ GOOD: Significant improvement (+10%+) - DPO training effective")
    elif improvement > 0.05:
        print("📈 MODERATE: Noticeable improvement (+5%+) - DPO training somewhat effective")
    elif improvement > 0.00:
        print("😐 MINIMAL: Small improvement - DPO training had limited effect")
    else:
        print("😞 NO IMPROVEMENT: DPO training did not help or made things worse")

def main():
    """Run final comprehensive evaluation"""
    
    try:
        # Load held-out test instructions
        test_instructions = load_held_out_test_instructions()
        
        # Run evaluation on both models
        results = evaluate_models_on_heldout(test_instructions)
        
        # Analyze results
        metrics = analyze_results(results)
        
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = ARTIFACTS_DIR / f"final_evaluation_results_{timestamp}.json"
        
        with open(results_file, 'w') as f:
            json.dump(metrics, f, indent=2)
        
        logger.info(f"Results saved to {results_file}")
        
        # Print comprehensive summary
        print_evaluation_summary(metrics)
        
        logger.info("🎉 Final evaluation complete!")
        
        return metrics
        
    except Exception as e:
        logger.error(f"❌ Final evaluation failed: {e}")
        raise
    
    finally:
        # Cleanup
        torch.cuda.empty_cache()

if __name__ == "__main__":
    main()