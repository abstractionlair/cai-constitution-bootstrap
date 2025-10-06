#!/usr/bin/env python3
"""
Simplified Stage 1 Evaluation Script
Compares base model vs DPO-trained model on instruction following
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
        logging.FileHandler(ARTIFACTS_DIR / 'evaluation.log')
    ]
)
logger = logging.getLogger(__name__)

def load_models():
    """Load base model and trained model with LoRA adapter"""
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    from peft import PeftModel
    
    model_name = "Qwen/Qwen2.5-32B"
    
    logger.info(f"Loading base model: {model_name}")
    
    # 8-bit quantization for evaluation
    bnb_config = BitsAndBytesConfig(
        load_in_8bit=True,
        llm_int8_threshold=6.0,
        llm_int8_has_fp16_weight=False
    )
    
    # Load tokenizer
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)

    # CRITICAL: Disable chat template to prevent contamination
    # See docs/BASE_MODEL_TRUTH.md for why this is essential
    tokenizer.chat_template = None

    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    
    # Load base model
    base_model = AutoModelForCausalLM.from_pretrained(
        model_name,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True,
        low_cpu_mem_usage=True,
        torch_dtype=torch.float16
    )
    
    logger.info("✅ Base model loaded")
    
    # Load trained model with LoRA adapter
    logger.info("Loading DPO-trained model with LoRA adapter...")
    
    trained_base_model = AutoModelForCausalLM.from_pretrained(
        model_name,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True,
        low_cpu_mem_usage=True,
        torch_dtype=torch.float16
    )
    
    # Load LoRA adapter
    lora_path = CHECKPOINTS_DIR / "stage1_dpo_final"
    trained_model = PeftModel.from_pretrained(trained_base_model, str(lora_path))
    
    logger.info("✅ Trained model loaded with LoRA adapter")
    
    return base_model, trained_model, tokenizer

def generate_response(model, tokenizer, instruction, max_new_tokens=150):
    """Generate response from model"""
    
    # Use the instruction as-is (raw instruction)
    prompt = instruction

    inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=1500, add_special_tokens=False)
    inputs = {k: v.to(model.device) for k, v in inputs.items()}
    
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            temperature=0.1,
            do_sample=False,  # Deterministic for fair comparison
            pad_token_id=tokenizer.eos_token_id,
            eos_token_id=tokenizer.eos_token_id
        )
    
    # Decode only the new tokens
    new_tokens = outputs[0][inputs['input_ids'].shape[1]:]
    response = tokenizer.decode(new_tokens, skip_special_tokens=True).strip()
    
    return response

def evaluate_response(instruction, response, instruction_type):
    """Simple heuristic evaluation of response quality"""
    
    response = response.strip()
    
    # Basic checks
    if len(response) < 3:
        return False, "Response too short"
    
    if "I can't" in response or "I cannot" in response:
        return False, "Refusal response"
    
    # Type-specific checks
    if instruction_type == "qa":
        # For Q&A, check if it looks like an answer
        if response.lower().startswith(("i don't", "i'm not", "sorry")):
            return False, "Non-answer response"
        return True, "Provided answer"
    
    elif instruction_type == "completion":
        # For completion, check if it continues the prompt
        if len(response) > 5:
            return True, "Completed prompt"
        return False, "Incomplete response"
    
    elif instruction_type == "generation":
        # For generation, check if it produces content
        if len(response) > 20:
            return True, "Generated content"
        return False, "Insufficient generation"
    
    elif instruction_type == "response":
        # For response tasks, check if it responds appropriately
        if len(response) > 10:
            return True, "Provided response"
        return False, "Insufficient response"
    
    # Default: if it's not empty and not a refusal, it's probably good
    return True, "General response"

def load_test_instructions(limit=None):
    """Load our original 100 instructions for evaluation"""
    
    instructions_file = ARTIFACTS_DIR / "initial_responses.jsonl"
    
    with open(instructions_file, 'r') as f:
        instructions = [json.loads(line) for line in f]
    
    if limit:
        instructions = instructions[:limit]
    
    logger.info(f"Loaded {len(instructions)} test instructions")
    
    return instructions

def evaluate_models(base_model, trained_model, tokenizer, test_instructions):
    """Evaluate both models on the same instructions"""
    
    logger.info(f"Evaluating both models on {len(test_instructions)} instructions...")
    
    results = {
        'base_model': {'responses': [], 'successes': 0, 'total': 0},
        'trained_model': {'responses': [], 'successes': 0, 'total': 0}
    }
    
    for i, test_data in enumerate(test_instructions):
        instruction = test_data['instruction']
        instruction_type = test_data['instruction_type']
        
        print(f"\n{'='*80}")
        print(f"Example {i+1}/{len(test_instructions)} ({instruction_type})")
        print(f"Instruction: {instruction}")
        print(f"{'='*80}")
        
        # Generate responses from both models
        print("Generating base model response...")
        base_response = generate_response(base_model, tokenizer, instruction)
        
        print("Generating trained model response...")
        trained_response = generate_response(trained_model, tokenizer, instruction)
        
        # Evaluate responses
        base_success, base_reason = evaluate_response(instruction, base_response, instruction_type)
        trained_success, trained_reason = evaluate_response(instruction, trained_response, instruction_type)
        
        # Store results
        base_result = {
            'instruction': instruction,
            'instruction_type': instruction_type,
            'response': base_response,
            'success': base_success,
            'reason': base_reason
        }
        
        trained_result = {
            'instruction': instruction,
            'instruction_type': instruction_type,
            'response': trained_response,
            'success': trained_success,
            'reason': trained_reason
        }
        
        results['base_model']['responses'].append(base_result)
        results['trained_model']['responses'].append(trained_result)
        
        # Update counters
        results['base_model']['total'] += 1
        results['trained_model']['total'] += 1
        
        if base_success:
            results['base_model']['successes'] += 1
        if trained_success:
            results['trained_model']['successes'] += 1
        
        # Show comparison
        print(f"Base:    {'✅' if base_success else '❌'} {base_response[:100]}{'...' if len(base_response) > 100 else ''}")
        print(f"Trained: {'✅' if trained_success else '❌'} {trained_response[:100]}{'...' if len(trained_response) > 100 else ''}")
        
        if not base_success and trained_success:
            print("🎉 IMPROVEMENT!")
        elif base_success and not trained_success:
            print("😰 REGRESSION!")
        elif base_success and trained_success:
            print("✅ Both good")
        else:
            print("❌ Both failed")
    
    return results

def calculate_metrics(results):
    """Calculate success rates and improvements"""
    
    base_success_rate = results['base_model']['successes'] / results['base_model']['total']
    trained_success_rate = results['trained_model']['successes'] / results['trained_model']['total']
    
    improvement = trained_success_rate - base_success_rate
    
    # By instruction type
    base_by_type = defaultdict(lambda: {'successes': 0, 'total': 0})
    trained_by_type = defaultdict(lambda: {'successes': 0, 'total': 0})
    
    for response in results['base_model']['responses']:
        inst_type = response['instruction_type']
        base_by_type[inst_type]['total'] += 1
        if response['success']:
            base_by_type[inst_type]['successes'] += 1
    
    for response in results['trained_model']['responses']:
        inst_type = response['instruction_type']
        trained_by_type[inst_type]['total'] += 1
        if response['success']:
            trained_by_type[inst_type]['successes'] += 1
    
    # Calculate rates by type
    improvement_by_type = {}
    for inst_type in set(base_by_type.keys()) | set(trained_by_type.keys()):
        base_rate = base_by_type[inst_type]['successes'] / base_by_type[inst_type]['total'] if base_by_type[inst_type]['total'] > 0 else 0
        trained_rate = trained_by_type[inst_type]['successes'] / trained_by_type[inst_type]['total'] if trained_by_type[inst_type]['total'] > 0 else 0
        
        improvement_by_type[inst_type] = {
            'base_rate': base_rate,
            'trained_rate': trained_rate,
            'improvement': trained_rate - base_rate,
            'base_count': f"{base_by_type[inst_type]['successes']}/{base_by_type[inst_type]['total']}",
            'trained_count': f"{trained_by_type[inst_type]['successes']}/{trained_by_type[inst_type]['total']}"
        }
    
    metrics = {
        'timestamp': datetime.now().isoformat(),
        'overall': {
            'base_success_rate': base_success_rate,
            'trained_success_rate': trained_success_rate,
            'improvement': improvement,
            'base_count': f"{results['base_model']['successes']}/{results['base_model']['total']}",
            'trained_count': f"{results['trained_model']['successes']}/{results['trained_model']['total']}"
        },
        'by_type': improvement_by_type,
        'detailed_results': results
    }
    
    return metrics

def print_summary(metrics):
    """Print evaluation summary"""
    
    overall = metrics['overall']
    
    print("\n" + "="*80)
    print("📊 STAGE 1 DPO EVALUATION RESULTS")
    print("="*80)
    
    print(f"Base Model Success Rate:    {overall['base_success_rate']:.1%} ({overall['base_count']})")
    print(f"Trained Model Success Rate: {overall['trained_success_rate']:.1%} ({overall['trained_count']})")
    print(f"Overall Improvement:        +{overall['improvement']:.1%}")
    
    print(f"\nImprovement by Instruction Type:")
    print("-" * 60)
    
    for inst_type, data in metrics['by_type'].items():
        print(f"{inst_type.upper():12}: {data['base_rate']:.1%} → {data['trained_rate']:.1%} "
              f"(+{data['improvement']:.1%}) [{data['base_count']} → {data['trained_count']}]")
    
    print("="*80)
    
    # Success assessment
    if overall['trained_success_rate'] >= 0.90:
        print("🎉 EXCELLENT: 90%+ success rate achieved!")
    elif overall['trained_success_rate'] >= 0.80:
        print("✅ GOOD: 80%+ success rate")
    elif overall['improvement'] > 0.10:
        print("📈 PROMISING: Significant improvement (+10%)")
    else:
        print("🤔 NEEDS INVESTIGATION: Limited improvement")

def main():
    """Main evaluation function"""
    
    import argparse
    
    parser = argparse.ArgumentParser(description="Evaluate Stage 1 DPO training results")
    parser.add_argument("--quick", action="store_true", help="Quick test with 10 examples")
    parser.add_argument("--limit", type=int, help="Limit number of test examples")
    
    args = parser.parse_args()
    
    try:
        # Determine test size
        if args.quick:
            test_limit = 10
            logger.info("🧪 Running quick evaluation (10 examples)")
        elif args.limit:
            test_limit = args.limit
            logger.info(f"🧪 Running evaluation with {test_limit} examples")
        else:
            test_limit = None  # All 100
            logger.info("🧪 Running full evaluation (100 examples)")
        
        # Load models
        logger.info("Loading models...")
        base_model, trained_model, tokenizer = load_models()
        
        # Load test instructions
        test_instructions = load_test_instructions(test_limit)
        
        # Run evaluation
        results = evaluate_models(base_model, trained_model, tokenizer, test_instructions)
        
        # Calculate metrics
        metrics = calculate_metrics(results)
        
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        size_suffix = "quick" if args.quick else f"{len(test_instructions)}"
        results_file = ARTIFACTS_DIR / f"evaluation_results_{size_suffix}_{timestamp}.json"
        
        with open(results_file, 'w') as f:
            json.dump(metrics, f, indent=2)
        
        logger.info(f"Results saved to {results_file}")
        
        # Print summary
        print_summary(metrics)
        
        logger.info("🎉 Evaluation complete!")
        
        return metrics
        
    except Exception as e:
        logger.error(f"❌ Evaluation failed: {e}")
        raise
    
    finally:
        # Cleanup
        torch.cuda.empty_cache()

if __name__ == "__main__":
    main()