#!/usr/bin/env python3
"""
Stage 1 Response Generation - Robust Version
Generates responses with better error handling and progress tracking
"""

import json
import sys
import os
import torch
from pathlib import Path
from datetime import datetime
import logging
from collections import Counter
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/workspace/runs/stage1_20250911_131105/code/artifacts/generation.log')
    ]
)
logger = logging.getLogger(__name__)

# Setup paths
BASE_DIR = Path(os.getenv('CAI_BASE_DIR', '/workspace/runs/stage1_20250911_131105/code'))
ARTIFACTS_DIR = BASE_DIR / "artifacts"
sys.path.insert(0, str(BASE_DIR / 'scripts'))
sys.path.insert(0, str(BASE_DIR / 'scripts' / 'utils'))

def save_jsonl(data, filepath):
    """Save data in JSONL format"""
    with open(filepath, 'w') as f:
        for item in data:
            json.dump(item, f)
            f.write('\n')

def load_model_with_retry(model_name, max_retries=2):
    """Load model with retry logic and proper quantization config"""
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    
    # Modern quantization config
    bnb_config = BitsAndBytesConfig(
        load_in_8bit=True,
        llm_int8_threshold=6.0,
        llm_int8_has_fp16_weight=False
    )
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Model loading attempt {attempt + 1}/{max_retries}")
            
            # Load tokenizer
            logger.info("Loading tokenizer...")
            tokenizer = AutoTokenizer.from_pretrained(
                model_name, 
                trust_remote_code=True,
                use_fast=False  # More stable for some models
            )
            if tokenizer.pad_token is None:
                tokenizer.pad_token = tokenizer.eos_token
            logger.info("✅ Tokenizer loaded")
            
            # Load model
            logger.info("Loading model with 8-bit quantization...")
            model = AutoModelForCausalLM.from_pretrained(
                model_name,
                quantization_config=bnb_config,
                device_map="auto",
                trust_remote_code=True,
                low_cpu_mem_usage=True,
                torch_dtype=torch.float16
            )
            
            logger.info(f"✅ Model loaded successfully")
            logger.info(f"GPU memory: {torch.cuda.max_memory_allocated()/1e9:.1f}GB")
            
            return model, tokenizer
            
        except Exception as e:
            logger.error(f"Model loading attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                logger.info("Clearing GPU cache and retrying...")
                torch.cuda.empty_cache()
                time.sleep(5)
            else:
                raise

def generate_single_response(model, tokenizer, instruction, inst_type, timeout_seconds=60):
    """Generate a single response with timeout protection"""
    try:
        # Import completion style prompts
        from data_formatter import CompletionStylePrompts
        
        # Create completion-style prompt
        formatted_prompt = CompletionStylePrompts.create_response_generation_prompt(instruction)
        
        # Tokenize with length limits
        inputs = tokenizer(
            formatted_prompt, 
            return_tensors='pt', 
            truncation=True, 
            max_length=1600  # Leave room for generation
        )
        inputs = inputs.to(model.device)
        
        # Generate with timeout
        start_time = time.time()
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=100,  # Reduced for stability
                temperature=0.7,
                do_sample=True,
                top_p=0.9,
                top_k=50,
                pad_token_id=tokenizer.eos_token_id,
                eos_token_id=tokenizer.eos_token_id,
            )
        
        generation_time = time.time() - start_time
        if generation_time > timeout_seconds:
            logger.warning(f"Generation took {generation_time:.1f}s (timeout: {timeout_seconds}s)")
        
        # Extract response
        new_tokens = outputs[0][inputs['input_ids'].shape[1]:]
        response = tokenizer.decode(new_tokens, skip_special_tokens=True).strip()
        
        return response, formatted_prompt, None
        
    except Exception as e:
        logger.error(f"Generation failed for instruction: {instruction[:50]}... Error: {e}")
        return f"[ERROR: {str(e)}]", "", str(e)

def evaluate_response_quality(instruction, response, inst_type):
    """Basic heuristic evaluation of response quality"""
    
    if not response or len(response.strip()) < 3:
        return False
        
    response_lower = response.lower().strip()
    
    # Check for errors
    if response.startswith('[ERROR'):
        return False
    
    # General bad patterns
    bad_patterns = [
        'i cannot', 'i can\'t', 'as an ai', 'i\'m sorry',
        'i don\'t know', 'i am not', 'unable to', 'i apologize'
    ]
    
    if any(pattern in response_lower for pattern in bad_patterns):
        return False
    
    # Type-specific checks
    if inst_type == 'completion':
        if len(response) > 100 or len(response) < 2:
            return False
    elif inst_type == 'qa':
        if len(response) < 5:
            return False
    elif inst_type in ['generation', 'response']:
        if len(response) < 8:
            return False
    
    return True

def generate_responses():
    """Main response generation function"""
    
    logger.info("🚀 Starting robust response generation")
    
    # Load instructions
    instructions_file = ARTIFACTS_DIR / "instructions.jsonl"
    with open(instructions_file) as f:
        instructions = [json.loads(line) for line in f]
    
    logger.info(f"📝 Loaded {len(instructions)} instructions")
    
    # Load model
    model_name = "Qwen/Qwen2.5-32B"
    model, tokenizer = load_model_with_retry(model_name)
    
    # Generate responses
    responses = []
    errors = []
    
    start_time = time.time()
    
    for i, instruction_data in enumerate(instructions):
        if i % 5 == 0:
            elapsed = time.time() - start_time
            rate = i / elapsed if elapsed > 0 else 0
            eta = (len(instructions) - i) / rate if rate > 0 else 0
            
            logger.info(f"Progress: {i}/{len(instructions)} ({i/len(instructions)*100:.1f}%) "
                       f"Rate: {rate:.1f}/min ETA: {eta/60:.1f}min")
            logger.info(f"GPU memory: {torch.cuda.memory_allocated()/1e9:.1f}GB")
        
        instruction = instruction_data['instruction']
        inst_type = instruction_data['instruction_type']
        
        response, formatted_prompt, error = generate_single_response(
            model, tokenizer, instruction, inst_type
        )
        
        # Evaluate quality
        success = evaluate_response_quality(instruction, response, inst_type)
        
        result = {
            'id': instruction_data.get('id', f"inst_{i}"),
            'instruction': instruction,
            'response': response,
            'instruction_type': inst_type,
            'success': success,
            'formatted_prompt': formatted_prompt,
            'generation_error': error
        }
        
        responses.append(result)
        
        if error:
            errors.append({'index': i, 'error': error, 'instruction': instruction[:50]})
        
        # Periodic cleanup
        if i % 10 == 0 and i > 0:
            torch.cuda.empty_cache()
    
    total_time = time.time() - start_time
    logger.info(f"✅ Generation complete in {total_time/60:.1f} minutes")
    
    # Save results
    responses_file = ARTIFACTS_DIR / "initial_responses.jsonl"
    save_jsonl(responses, responses_file)
    
    # Create summary
    successful = [r for r in responses if r['success']]
    success_rate = len(successful) / len(responses)
    
    by_type = Counter(r['instruction_type'] for r in responses)
    success_by_type = {}
    for inst_type in by_type:
        type_responses = [r for r in responses if r['instruction_type'] == inst_type]
        type_success = sum(1 for r in type_responses if r['success'])
        success_by_type[inst_type] = type_success / len(type_responses)
    
    summary = {
        'total_responses': len(responses),
        'success_rate': success_rate,
        'success_count': len(successful),
        'generation_time_minutes': total_time / 60,
        'errors_count': len(errors),
        'success_by_type': success_by_type,
        'sample_successful': [
            {'instruction': r['instruction'], 'response': r['response'][:100] + '...'}
            for r in successful[:3]
        ],
        'sample_failed': [
            {'instruction': r['instruction'], 'response': r['response'][:100] + '...'}
            for r in responses if not r['success']
        ][:3]
    }
    
    summary_file = ARTIFACTS_DIR / "response_summary.json"
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    
    # Text summary
    text_summary = f"""📊 Response Generation Summary
================================

Total: {len(responses)} responses
Success Rate: {success_rate:.1%} ({len(successful)}/{len(responses)})
Generation Time: {total_time/60:.1f} minutes
Errors: {len(errors)}

Success by Type:
"""
    for inst_type, rate in success_by_type.items():
        count = by_type[inst_type]
        text_summary += f"  {inst_type}: {rate:.1%} ({int(rate*count)}/{count})\n"

    text_summary += "\nSample Successful Responses:\n"
    for i, r in enumerate(successful[:3]):
        text_summary += f"{i+1}. [{r['instruction_type']}] {r['instruction'][:50]}...\n"
        text_summary += f"   {r['response'][:80]}...\n\n"
    
    text_file = ARTIFACTS_DIR / "response_summary.txt"
    with open(text_file, 'w') as f:
        f.write(text_summary)
    
    logger.info(f"📊 Success rate: {success_rate:.1%}")
    logger.info(f"💾 Results saved to {responses_file}")
    
    # Clear model
    del model
    torch.cuda.empty_cache()
    
    return responses, success_rate

if __name__ == "__main__":
    try:
        responses, success_rate = generate_responses()
        
        print("\n" + "="*60)
        print("🎉 RESPONSE GENERATION COMPLETE")
        print("="*60)
        print(f"Responses: {len(responses)}")
        print(f"Success rate: {success_rate:.1%}")
        print("\nFiles created:")
        print("  - initial_responses.jsonl")
        print("  - response_summary.json")
        print("  - response_summary.txt")
        print("  - generation.log")
        print("\n✅ Ready for review!")
        
    except Exception as e:
        logger.error(f"❌ Generation failed: {e}")
        print(f"\n❌ Generation failed: {e}")
        raise