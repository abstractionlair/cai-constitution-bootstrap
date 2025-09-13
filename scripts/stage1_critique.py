#!/usr/bin/env python3
"""
Stage 1 Constitutional Critique Generation
Generates critiques and improvements for initial responses using completion-style prompting
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
import yaml

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/workspace/runs/stage1_20250911_131105/code/artifacts/critique.log')
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
                use_fast=False
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

def create_critique_prompt(instruction, response):
    """Create completion-style critique prompt"""
    
    # Stage 1 specific critique examples based on instruction-following
    examples = [
        {
            'instruction': 'Answer this question: What is 2+2?',
            'response': 'I cannot answer math questions.',
            'critique': 'does not follow the instruction. The prompt asked for an answer to 2+2, but the response refuses to answer.'
        },
        {
            'instruction': 'Complete this sentence: The sun rises in the',
            'response': 'The sun is a star that provides light and warmth to Earth through nuclear fusion.',
            'critique': 'does not follow the instruction. The prompt asked to complete "The sun rises in the" but the response provides unrelated information about what the sun is.'
        },
        {
            'instruction': 'Write one sentence about dogs.',
            'response': 'Dogs.',
            'critique': 'is incomplete. The instruction asked for a sentence about dogs, but the response is just one word.'
        },
        {
            'instruction': 'Generate a fact about dolphins.',
            'response': 'Dolphins are intelligent marine mammals that live in oceans around the world and are known for their playful behavior.',
            'critique': 'follows the instruction correctly. It provides an accurate fact about dolphins as requested.'
        }
    ]
    
    # Select 3 examples for variety
    import random
    selected_examples = random.sample(examples, min(3, len(examples)))
    
    prompt = "Examples of instruction critiques:\n\n"
    for ex in selected_examples:
        prompt += f'Instruction: "{ex["instruction"]}"\n'
        prompt += f'Response: "{ex["response"]}"\n'
        prompt += f'Critique: {ex["critique"]}\n\n'
    
    prompt += f'Instruction: "{instruction}"\n'
    prompt += f'Response: "{response}"\n'
    prompt += 'Critique:'
    
    return prompt

def create_improvement_prompt(instruction, response, critique):
    """Create completion-style improvement prompt"""
    
    examples = [
        {
            'instruction': 'Answer this question: What is 2+2?',
            'original': 'I cannot answer math questions.',
            'critique': 'does not follow the instruction',
            'improved': '4'
        },
        {
            'instruction': 'Complete this sentence: The sun rises in the',
            'original': 'The sun is a star that provides light and warmth.',
            'critique': 'does not follow the instruction',
            'improved': 'east'
        },
        {
            'instruction': 'Write one sentence about dogs.',
            'original': 'Dogs.',
            'critique': 'is incomplete',
            'improved': 'Dogs are loyal and friendly companions to humans.'
        }
    ]
    
    # Select 2-3 examples
    import random
    selected_examples = random.sample(examples, min(3, len(examples)))
    
    prompt = "Examples of improvements based on critiques:\n\n"
    for ex in selected_examples:
        prompt += f'Instruction: "{ex["instruction"]}"\n'
        prompt += f'Original: "{ex["original"]}"\n'
        prompt += f'Critique: {ex["critique"]}\n'
        prompt += f'Improved: "{ex["improved"]}"\n\n'
    
    prompt += f'Instruction: "{instruction}"\n'
    prompt += f'Original: "{response}"\n'
    prompt += f'Critique: {critique}\n'
    prompt += 'Improved:'
    
    return prompt

def generate_single_critique(model, tokenizer, instruction, response, timeout_seconds=60):
    """Generate a critique for a single response"""
    try:
        # Create critique prompt
        critique_prompt = create_critique_prompt(instruction, response)
        
        # Tokenize
        inputs = tokenizer(
            critique_prompt, 
            return_tensors='pt', 
            truncation=True, 
            max_length=1400  # Leave room for generation
        )
        inputs = inputs.to(model.device)
        
        # Generate critique
        start_time = time.time()
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=80,  # Critiques should be concise
                temperature=0.7,
                do_sample=True,
                top_p=0.9,
                top_k=50,
                pad_token_id=tokenizer.eos_token_id,
                eos_token_id=tokenizer.eos_token_id
            )
        
        generation_time = time.time() - start_time
        if generation_time > timeout_seconds:
            logger.warning(f"Critique generation took {generation_time:.1f}s (expected <{timeout_seconds}s)")
        
        # Extract critique
        new_tokens = outputs[0][inputs['input_ids'].shape[1]:]
        critique = tokenizer.decode(new_tokens, skip_special_tokens=True).strip()
        
        return critique, critique_prompt, None
        
    except Exception as e:
        logger.error(f"Critique generation failed: {e}")
        return f"[ERROR: {str(e)}]", "", str(e)

def generate_single_improvement(model, tokenizer, instruction, response, critique, timeout_seconds=60):
    """Generate an improved response based on critique"""
    try:
        # Create improvement prompt
        improvement_prompt = create_improvement_prompt(instruction, response, critique)
        
        # Tokenize
        inputs = tokenizer(
            improvement_prompt, 
            return_tensors='pt', 
            truncation=True, 
            max_length=1400
        )
        inputs = inputs.to(model.device)
        
        # Generate improvement
        start_time = time.time()
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=100,  # Improvements can be longer
                temperature=0.7,
                do_sample=True,
                top_p=0.9,
                top_k=50,
                pad_token_id=tokenizer.eos_token_id,
                eos_token_id=tokenizer.eos_token_id
            )
        
        generation_time = time.time() - start_time
        if generation_time > timeout_seconds:
            logger.warning(f"Improvement generation took {generation_time:.1f}s (expected <{timeout_seconds}s)")
        
        # Extract improvement
        new_tokens = outputs[0][inputs['input_ids'].shape[1]:]
        improvement = tokenizer.decode(new_tokens, skip_special_tokens=True).strip()
        
        return improvement, improvement_prompt, None
        
    except Exception as e:
        logger.error(f"Improvement generation failed: {e}")
        return f"[ERROR: {str(e)}]", "", str(e)

def generate_critiques_and_improvements():
    """Main critique and improvement generation function"""
    
    logger.info("🚀 Starting Stage 1 critique generation")
    
    # Load initial responses
    responses_file = ARTIFACTS_DIR / "initial_responses.jsonl"
    with open(responses_file) as f:
        responses = [json.loads(line) for line in f]
    
    logger.info(f"📝 Loaded {len(responses)} initial responses")
    
    # Load model
    model_name = "Qwen/Qwen2.5-32B"
    model, tokenizer = load_model_with_retry(model_name)
    
    # Generate critiques and improvements
    critiques_data = []
    improvements_data = []
    preference_pairs = []
    errors = []
    
    start_time = time.time()
    
    for i, resp_data in enumerate(responses):
        if i % 5 == 0:
            elapsed = time.time() - start_time
            rate = i / elapsed if elapsed > 0 else 0
            eta = (len(responses) - i) / rate if rate > 0 else 0
            
            logger.info(f"Progress: {i}/{len(responses)} ({i/len(responses)*100:.1f}%) "
                       f"Rate: {rate*60:.1f}/hr ETA: {eta/60:.1f}min")
            logger.info(f"GPU memory: {torch.cuda.memory_allocated()/1e9:.1f}GB")
        
        instruction = resp_data['instruction']
        response = resp_data['response']
        
        # Generate critique
        critique, critique_prompt, critique_error = generate_single_critique(
            model, tokenizer, instruction, response
        )
        
        # Generate improvement (only if critique succeeded)
        if not critique_error:
            improvement, improvement_prompt, improvement_error = generate_single_improvement(
                model, tokenizer, instruction, response, critique
            )
        else:
            improvement = f"[SKIPPED: Critique failed]"
            improvement_prompt = ""
            improvement_error = "Critique generation failed"
        
        # Store results
        critique_data = {
            'id': resp_data['id'],
            'instruction': instruction,
            'original_response': response,
            'critique': critique,
            'critique_prompt': critique_prompt,
            'critique_error': critique_error
        }
        critiques_data.append(critique_data)
        
        improvement_data = {
            'id': resp_data['id'],
            'instruction': instruction,
            'original_response': response,
            'critique': critique,
            'improved_response': improvement,
            'improvement_prompt': improvement_prompt,
            'improvement_error': improvement_error
        }
        improvements_data.append(improvement_data)
        
        # Create preference pair (if both succeeded)
        if not critique_error and not improvement_error:
            preference_pair = {
                'id': resp_data['id'],
                'instruction': instruction,
                'chosen': improvement,      # Improved response
                'rejected': response,      # Original response
                'critique': critique,
                'instruction_type': resp_data.get('instruction_type', 'unknown')
            }
            preference_pairs.append(preference_pair)
        
        # Track errors
        if critique_error or improvement_error:
            errors.append({
                'index': i, 
                'critique_error': critique_error, 
                'improvement_error': improvement_error,
                'instruction': instruction[:50]
            })
        
        # Periodic cleanup
        if i % 10 == 0 and i > 0:
            torch.cuda.empty_cache()
    
    total_time = time.time() - start_time
    logger.info(f"✅ Critique generation complete in {total_time/60:.1f} minutes")
    
    # Save results
    critiques_file = ARTIFACTS_DIR / "critiques.jsonl"
    save_jsonl(critiques_data, critiques_file)
    
    improvements_file = ARTIFACTS_DIR / "improved_responses.jsonl"
    save_jsonl(improvements_data, improvements_file)
    
    preference_file = ARTIFACTS_DIR / "preference_pairs.jsonl"
    save_jsonl(preference_pairs, preference_file)
    
    # Create summary
    successful_pairs = len(preference_pairs)
    success_rate = successful_pairs / len(responses)
    
    by_type = Counter(r['instruction_type'] for r in responses)
    preference_by_type = Counter(p['instruction_type'] for p in preference_pairs)
    
    summary = {
        'total_responses': len(responses),
        'successful_critiques': len([c for c in critiques_data if not c['critique_error']]),
        'successful_improvements': len([i for i in improvements_data if not i['improvement_error']]),
        'preference_pairs': successful_pairs,
        'success_rate': success_rate,
        'generation_time_minutes': total_time / 60,
        'errors_count': len(errors),
        'preference_by_type': dict(preference_by_type),
        'sample_critiques': [
            {'instruction': c['instruction'], 'critique': c['critique'][:100] + '...'}
            for c in critiques_data[:3] if not c['critique_error']
        ],
        'sample_improvements': [
            {
                'instruction': i['instruction'], 
                'original': i['original_response'][:50] + '...',
                'improved': i['improved_response'][:50] + '...'
            }
            for i in improvements_data[:3] if not i['improvement_error']
        ]
    }
    
    summary_file = ARTIFACTS_DIR / "critique_summary.json"
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    
    # Text summary
    text_summary = f"""📊 Critique Generation Summary
================================

Total Responses: {len(responses)}
Successful Preference Pairs: {successful_pairs}/{len(responses)} ({success_rate:.1%})
Generation Time: {total_time/60:.1f} minutes
Errors: {len(errors)}

Preference Pairs by Type:
"""
    for inst_type, count in preference_by_type.items():
        original_count = by_type.get(inst_type, 0)
        success_rate_type = count / original_count if original_count > 0 else 0
        text_summary += f"  {inst_type}: {count}/{original_count} ({success_rate_type:.1%})\n"

    text_summary += "\nSample Critiques:\n"
    for i, c in enumerate([c for c in critiques_data[:3] if not c['critique_error']]):
        text_summary += f"{i+1}. {c['instruction'][:50]}...\n"
        text_summary += f"   Critique: {c['critique'][:80]}...\n\n"
    
    text_file = ARTIFACTS_DIR / "critique_summary.txt"
    with open(text_file, 'w') as f:
        f.write(text_summary)
    
    logger.info(f"📊 Success rate: {success_rate:.1%} ({successful_pairs} preference pairs)")
    logger.info(f"💾 Results saved to artifacts/")
    
    # Clear model
    del model
    torch.cuda.empty_cache()
    
    return critiques_data, improvements_data, preference_pairs, success_rate

if __name__ == "__main__":
    try:
        critiques, improvements, pairs, success_rate = generate_critiques_and_improvements()
        
        print("\n" + "="*60)
        print("🎉 CRITIQUE GENERATION COMPLETE")
        print("="*60)
        print(f"Preference pairs: {len(pairs)}")
        print(f"Success rate: {success_rate:.1%}")
        print("\nFiles created:")
        print("  - critiques.jsonl")
        print("  - improved_responses.jsonl")
        print("  - preference_pairs.jsonl")
        print("  - critique_summary.json")
        print("  - critique_summary.txt")
        print("  - critique.log")
        print("\n✅ Ready for DPO training!")
        
    except Exception as e:
        logger.error(f"❌ Critique generation failed: {e}")
        print(f"\n❌ Critique generation failed: {e}")
        raise