#!/usr/bin/env python3
"""
Corrected Stage 1 Evaluation Script
Disables chat template to test true base model vs DPO-trained model on raw instructions
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
        logging.FileHandler(ARTIFACTS_DIR / 'evaluation_corrected.log')
    ]
)
logger = logging.getLogger(__name__)

def load_base_model_only():
    """Load just the base model to avoid memory issues"""
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
    
    # Use BitsAndBytesConfig to avoid deprecated warning
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

def generate_response_few_shot(model, tokenizer, instruction, max_new_tokens=150):
    """Generate response using few-shot completion-style prompting (like original baseline)"""
    
    # Import the completion-style prompt formatter
    sys.path.insert(0, str(BASE_DIR / 'scripts' / 'utils'))
    from data_formatter import CompletionStylePrompts
    
    # Create completion-style prompt (same as original baseline)
    prompt = CompletionStylePrompts.create_response_generation_prompt(instruction)
    
    # Use encode() to bypass any template processing
    input_ids = tokenizer.encode(prompt, return_tensors="pt")
    input_ids = input_ids.to(model.device)
    
    with torch.no_grad():
        outputs = model.generate(
            input_ids,
            max_new_tokens=max_new_tokens,
            temperature=0.7,  # Match original baseline parameters
            do_sample=True,
            top_p=0.9,
            pad_token_id=tokenizer.eos_token_id,
            eos_token_id=tokenizer.eos_token_id
        )
    
    # Decode only the new tokens
    new_tokens = outputs[0][input_ids.shape[1]:]
    response = tokenizer.decode(new_tokens, skip_special_tokens=True).strip()
    
    return response

def evaluate_response(instruction, response, instruction_type):
    """Enhanced evaluation matching original baseline criteria"""
    
    response = response.strip()
    
    # Basic checks
    if len(response) < 3:
        return False, "Response too short"
    
    # Check for common base model failure patterns
    if response.lower().startswith(("i can't", "i cannot", "i'm not", "sorry, i")):
        return False, "Refusal response"
    
    # Check if it's just continuing the text inappropriately
    if instruction.lower() in response.lower()[:50]:
        # If the response starts by repeating the instruction, it might be confused
        return False, "Repetitive/confused response"
    
    # Type-specific enhanced checks
    if instruction_type == "qa":
        # For questions, check if it actually provides an answer vs continues text
        question_markers = ["what is", "where is", "who is", "how does", "q:"]
        is_question = any(marker in instruction.lower() for marker in question_markers)
        
        if is_question:
            # Look for answer-like responses
            if any(word in response.lower()[:100] for word in ["is", "are", "was", "were", "the", "it"]):
                return True, "Provided answer"
            else:
                return False, "No clear answer"
        
        return True, "QA response"
    
    elif instruction_type == "completion":
        # For completion, check if it completes appropriately
        if len(response) > 5 and not response.startswith(instruction):
            return True, "Completed prompt"
        return False, "Incomplete/inappropriate"
    
    elif instruction_type == "generation":
        # For generation, check if it generates content vs continues randomly  
        if len(response) > 20:
            # Check if it seems to be following the instruction vs random continuation
            if any(word in instruction.lower() for word in ["describe", "write", "explain"]):
                return True, "Generated content"
            elif len(response) > 30:
                return True, "Generated content"
        return False, "Insufficient generation"
    
    elif instruction_type == "response":
        # For response tasks
        if len(response) > 10:
            return True, "Provided response"
        return False, "Insufficient response"
    
    # Default: if it's substantial and not a refusal
    if len(response) > 15:
        return True, "General response"
    return False, "Inadequate response"

def load_test_instructions(limit=None):
    """Load our original 100 instructions for evaluation"""
    
    instructions_file = ARTIFACTS_DIR / "initial_responses.jsonl"
    
    with open(instructions_file, 'r') as f:
        instructions = [json.loads(line) for line in f]
    
    if limit:
        instructions = instructions[:limit]
    
    logger.info(f"Loaded {len(instructions)} test instructions")
    
    return instructions

def evaluate_models_sequential(test_instructions):
    """Evaluate both models sequentially to avoid memory issues"""
    
    logger.info(f"Evaluating both models on {len(test_instructions)} instructions")
    logger.info("Loading models sequentially to avoid GPU memory issues")
    
    results = {
        'base_raw': {'responses': [], 'successes': 0, 'total': 0},
        'trained_raw': {'responses': [], 'successes': 0, 'total': 0},
        'base_few_shot': {'responses': [], 'successes': 0, 'total': 0},
        'trained_few_shot': {'responses': [], 'successes': 0, 'total': 0}
    }
    
    # First pass: Base model evaluation
    logger.info("🔥 EVALUATING BASE MODEL")
    base_model, tokenizer = load_base_model_only()
    
    base_raw_results = []
    base_few_shot_results = []
    
    for i, test_data in enumerate(test_instructions):
        instruction = test_data['instruction']
        instruction_type = test_data['instruction_type']
        
        logger.info(f"Base model: {i+1}/{len(test_instructions)} - {instruction_type}")
        
        # Generate responses from base model
        base_raw = generate_response_raw(base_model, tokenizer, instruction)
        base_few_shot = generate_response_few_shot(base_model, tokenizer, instruction)
        
        # Evaluate responses
        base_raw_success, base_raw_reason = evaluate_response(instruction, base_raw, instruction_type)
        base_few_shot_success, base_few_shot_reason = evaluate_response(instruction, base_few_shot, instruction_type)
        
        # Store results
        base_raw_results.append({
            'instruction': instruction,
            'instruction_type': instruction_type,
            'response': base_raw,
            'success': base_raw_success,
            'reason': base_raw_reason
        })
        
        base_few_shot_results.append({
            'instruction': instruction,
            'instruction_type': instruction_type,
            'response': base_few_shot,
            'success': base_few_shot_success,
            'reason': base_few_shot_reason
        })
    
    # Clean up base model
    del base_model
    torch.cuda.empty_cache()
    logger.info("✅ Base model evaluation complete, GPU memory cleared")
    
    # Second pass: Trained model evaluation
    logger.info("🚀 EVALUATING TRAINED MODEL")  
    trained_model, tokenizer = load_trained_model_only()
    
    trained_raw_results = []
    trained_few_shot_results = []
    
    for i, test_data in enumerate(test_instructions):
        instruction = test_data['instruction']
        instruction_type = test_data['instruction_type']
        
        logger.info(f"Trained model: {i+1}/{len(test_instructions)} - {instruction_type}")
        
        # Generate responses from trained model
        trained_raw = generate_response_raw(trained_model, tokenizer, instruction)
        trained_few_shot = generate_response_few_shot(trained_model, tokenizer, instruction)
        
        # Evaluate responses
        trained_raw_success, trained_raw_reason = evaluate_response(instruction, trained_raw, instruction_type)
        trained_few_shot_success, trained_few_shot_reason = evaluate_response(instruction, trained_few_shot, instruction_type)
        
        # Store results
        trained_raw_results.append({
            'instruction': instruction,
            'instruction_type': instruction_type,
            'response': trained_raw,
            'success': trained_raw_success,
            'reason': trained_raw_reason
        })
        
        trained_few_shot_results.append({
            'instruction': instruction,
            'instruction_type': instruction_type,
            'response': trained_few_shot,
            'success': trained_few_shot_success,
            'reason': trained_few_shot_reason
        })
    
    # Clean up trained model
    del trained_model
    torch.cuda.empty_cache()
    logger.info("✅ Trained model evaluation complete")
    
    # Combine results
    results['base_raw']['responses'] = base_raw_results
    results['base_few_shot']['responses'] = base_few_shot_results
    results['trained_raw']['responses'] = trained_raw_results
    results['trained_few_shot']['responses'] = trained_few_shot_results
    
    # Calculate success counts
    for condition, data in results.items():
        data['total'] = len(data['responses'])
        data['successes'] = sum(1 for r in data['responses'] if r['success'])
    
    # Print comparison summary
    print(f"\n{'='*80}")
    print("📊 EVALUATION RESULTS SUMMARY")
    print(f"{'='*80}")
    
    for i, test_data in enumerate(test_instructions):
        instruction = test_data['instruction']
        print(f"\nExample {i+1}: {instruction}")
        print(f"  Base (raw):        {'✅' if base_raw_results[i]['success'] else '❌'} {base_raw_results[i]['response'][:60]}...")
        print(f"  Trained (raw):     {'✅' if trained_raw_results[i]['success'] else '❌'} {trained_raw_results[i]['response'][:60]}...")
        print(f"  Base (few-shot):   {'✅' if base_few_shot_results[i]['success'] else '❌'} {base_few_shot_results[i]['response'][:60]}...")
        print(f"  Trained (few-shot):{'✅' if trained_few_shot_results[i]['success'] else '❌'} {trained_few_shot_results[i]['response'][:60]}...")
        
        # Key insights
        if not base_raw_results[i]['success'] and trained_raw_results[i]['success']:
            print("    🎯 RAW INSTRUCTION IMPROVEMENT!")
    
    return results

def calculate_comprehensive_metrics(results):
    """Calculate metrics for all four test conditions"""
    
    metrics = {
        'timestamp': datetime.now().isoformat(),
        'evaluation_type': 'corrected_dual_evaluation',
        'note': 'Tests both raw instructions and few-shot prompting without chat template',
        'conditions': {}
    }
    
    for condition in ['base_raw', 'trained_raw', 'base_few_shot', 'trained_few_shot']:
        data = results[condition]
        success_rate = data['successes'] / data['total']
        
        # By instruction type
        by_type = defaultdict(lambda: {'successes': 0, 'total': 0})
        for response in data['responses']:
            inst_type = response['instruction_type']
            by_type[inst_type]['total'] += 1
            if response['success']:
                by_type[inst_type]['successes'] += 1
        
        type_rates = {}
        for inst_type, counts in by_type.items():
            type_rates[inst_type] = {
                'success_rate': counts['successes'] / counts['total'],
                'count': f"{counts['successes']}/{counts['total']}"
            }
        
        metrics['conditions'][condition] = {
            'success_rate': success_rate,
            'count': f"{data['successes']}/{data['total']}",
            'by_type': type_rates
        }
    
    # Calculate key comparisons
    metrics['key_comparisons'] = {
        'raw_improvement': metrics['conditions']['trained_raw']['success_rate'] - metrics['conditions']['base_raw']['success_rate'],
        'few_shot_improvement': metrics['conditions']['trained_few_shot']['success_rate'] - metrics['conditions']['base_few_shot']['success_rate'],
        'base_few_shot_vs_raw': metrics['conditions']['base_few_shot']['success_rate'] - metrics['conditions']['base_raw']['success_rate'],
        'trained_few_shot_vs_raw': metrics['conditions']['trained_few_shot']['success_rate'] - metrics['conditions']['trained_raw']['success_rate']
    }
    
    # Add detailed results
    metrics['detailed_results'] = results
    
    return metrics

def print_comprehensive_summary(metrics):
    """Print comprehensive evaluation summary"""
    
    conditions = metrics['conditions']
    comparisons = metrics['key_comparisons']
    
    print("\n" + "="*80)
    print("📊 CORRECTED STAGE 1 DPO EVALUATION RESULTS")
    print("="*80)
    print("🚨 CHAT TEMPLATE DISABLED - TRUE BASE MODEL EVALUATION")
    print()
    
    print("Overall Success Rates:")
    print("-" * 40)
    print(f"Base Model (Raw Instructions):      {conditions['base_raw']['success_rate']:.1%} ({conditions['base_raw']['count']})")
    print(f"Trained Model (Raw Instructions):   {conditions['trained_raw']['success_rate']:.1%} ({conditions['trained_raw']['count']})")
    print(f"Base Model (Few-Shot Prompting):    {conditions['base_few_shot']['success_rate']:.1%} ({conditions['base_few_shot']['count']})")
    print(f"Trained Model (Few-Shot Prompting): {conditions['trained_few_shot']['success_rate']:.1%} ({conditions['trained_few_shot']['count']})")
    print()
    
    print("Key Improvements:")
    print("-" * 40)  
    print(f"Raw Instruction Improvement:        +{comparisons['raw_improvement']:.1%}")
    print(f"Few-Shot Prompting Improvement:     +{comparisons['few_shot_improvement']:.1%}")
    print(f"Base Model: Few-Shot vs Raw:        +{comparisons['base_few_shot_vs_raw']:.1%}")
    print(f"Trained Model: Few-Shot vs Raw:     +{comparisons['trained_few_shot_vs_raw']:.1%}")
    print()
    
    print("By Instruction Type:")
    print("-" * 60)
    for inst_type in ['qa', 'completion', 'generation', 'response']:
        if inst_type in conditions['base_raw']['by_type']:
            base_raw_rate = conditions['base_raw']['by_type'][inst_type]['success_rate']
            trained_raw_rate = conditions['trained_raw']['by_type'][inst_type]['success_rate']
            base_fs_rate = conditions['base_few_shot']['by_type'][inst_type]['success_rate']
            trained_fs_rate = conditions['trained_few_shot']['by_type'][inst_type]['success_rate']
            
            print(f"{inst_type.upper():12}:")
            print(f"  Raw:      {base_raw_rate:.1%} → {trained_raw_rate:.1%} (+{trained_raw_rate-base_raw_rate:.1%})")
            print(f"  Few-shot: {base_fs_rate:.1%} → {trained_fs_rate:.1%} (+{trained_fs_rate-base_fs_rate:.1%})")
    
    print("="*80)
    
    # Assessment
    raw_improvement = comparisons['raw_improvement']
    few_shot_improvement = comparisons['few_shot_improvement']
    
    if raw_improvement > 0.30:
        print("🎉 EXCELLENT: Major improvement on raw instructions (+30%)")
    elif raw_improvement > 0.15:
        print("✅ GOOD: Significant improvement on raw instructions (+15%)")
    elif raw_improvement > 0.05:
        print("📈 PROMISING: Moderate improvement on raw instructions (+5%)")
    else:
        print("🤔 LIMITED: Small improvement on raw instructions")
    
    if few_shot_improvement > 0.10:
        print("🚀 BONUS: Strong improvement even with few-shot prompting")
    elif few_shot_improvement > 0.05:
        print("📊 GOOD: Some improvement with few-shot prompting")
    else:
        print("📝 EXPECTED: Few-shot prompting already effective for base model")

def main():
    """Main evaluation function"""
    
    import argparse
    
    parser = argparse.ArgumentParser(description="Corrected Stage 1 DPO evaluation (no chat template)")
    parser.add_argument("--quick", action="store_true", help="Quick test with 10 examples")
    parser.add_argument("--limit", type=int, help="Limit number of test examples")
    
    args = parser.parse_args()
    
    try:
        # Determine test size
        if args.quick:
            test_limit = 10
            logger.info("🧪 Running quick corrected evaluation (10 examples)")
        elif args.limit:
            test_limit = args.limit
            logger.info(f"🧪 Running corrected evaluation with {test_limit} examples")
        else:
            test_limit = None  # All 100
            logger.info("🧪 Running full corrected evaluation (100 examples)")
        
        # Load test instructions
        test_instructions = load_test_instructions(test_limit)
        
        # Run sequential evaluation (models loaded as needed)
        results = evaluate_models_sequential(test_instructions)
        
        # Calculate comprehensive metrics
        metrics = calculate_comprehensive_metrics(results)
        
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        size_suffix = "quick" if args.quick else f"{len(test_instructions)}"
        results_file = ARTIFACTS_DIR / f"evaluation_corrected_{size_suffix}_{timestamp}.json"
        
        with open(results_file, 'w') as f:
            json.dump(metrics, f, indent=2)
        
        logger.info(f"Results saved to {results_file}")
        
        # Print comprehensive summary
        print_comprehensive_summary(metrics)
        
        logger.info("🎉 Corrected evaluation complete!")
        
        return metrics
        
    except Exception as e:
        logger.error(f"❌ Evaluation failed: {e}")
        raise
    
    finally:
        # Cleanup
        torch.cuda.empty_cache()

if __name__ == "__main__":
    main()