#!/usr/bin/env python3
"""
Test GOOD/BAD format with exact pattern matching
"""

import json
import sys
import os
import torch
from pathlib import Path
import logging
from collections import Counter

# Setup paths
BASE_DIR = Path(os.getenv('CAI_BASE_DIR', '/workspace/runs/stage1_20250911_131105/code'))
ARTIFACTS_DIR = BASE_DIR / "artifacts"
sys.path.insert(0, str(BASE_DIR / 'scripts'))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_good_bad_prompt(instruction, response):
    """Create GOOD/BAD evaluation prompt with exact format matching"""
    
    # Clean up the response
    clean_response = response.split('\n\n')[0].strip()
    
    prompt = """This document evaluates instruction-following quality for language model responses.

Section 2: Evaluation Examples

Instruction: "Answer this question: What is 2+2?"
Response: "I cannot help with math questions."
Was the judgment GOOD or BAD? BAD

Instruction: "Answer this question: What is 2+2?"
Response: "4"
Was the judgment GOOD or BAD? GOOD

Instruction: "Complete this sentence: The sun rises in the"
Response: "east"
Was the judgment GOOD or BAD? GOOD

Instruction: "Write one sentence about dogs."
Response: "Dogs."
Was the judgment GOOD or BAD? BAD

Instruction: "Write one sentence about dogs."
Response: "Dogs are loyal companions to humans."
Was the judgment GOOD or BAD? GOOD

Section 3: Current Evaluation

Instruction: "{instruction}"
Response: "{response}"
Was the judgment GOOD or BAD? """.format(instruction=instruction, response=clean_response)
    
    return prompt

def generate_evaluation(model, tokenizer, prompt, temperature=0.0):
    """Generate a GOOD/BAD evaluation"""
    
    inputs = tokenizer(prompt, return_tensors='pt', truncation=True, max_length=1600)
    inputs = inputs.to(model.device)
    
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=3,  # Just need "GOOD" or "BAD"
            temperature=temperature,
            do_sample=temperature > 0,
            top_p=0.9 if temperature > 0 else None,
            pad_token_id=tokenizer.eos_token_id,
            eos_token_id=tokenizer.eos_token_id
        )
    
    new_tokens = outputs[0][inputs['input_ids'].shape[1]:]
    response = tokenizer.decode(new_tokens, skip_special_tokens=True).strip()
    
    return response

def extract_judgment(response):
    """Extract GOOD or BAD from response"""
    response_upper = response.upper().strip()
    
    if response_upper.startswith('GOOD'):
        return 'GOOD'
    elif response_upper.startswith('BAD'):
        return 'BAD'
    else:
        return f'unclear: "{response}"'

def test_good_bad_format():
    """Test GOOD/BAD evaluation format"""
    
    logger.info("🧪 Testing GOOD/BAD format with exact pattern matching")
    
    # Load a few responses to test
    responses_file = ARTIFACTS_DIR / "initial_responses.jsonl"
    with open(responses_file) as f:
        responses = [json.loads(line) for line in f]
    
    # Test on first 3 responses
    test_responses = responses[:3]
    
    logger.info(f"Testing on {len(test_responses)} samples")
    
    # Load model
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    
    model_name = "Qwen/Qwen2.5-32B"
    
    bnb_config = BitsAndBytesConfig(
        load_in_8bit=True,
        llm_int8_threshold=6.0,
        llm_int8_has_fp16_weight=False
    )
    
    logger.info("Loading model...")
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
        
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True,
        low_cpu_mem_usage=True,
        torch_dtype=torch.float16
    )
    
    logger.info("✅ Model loaded")
    
    results = []
    
    for i, resp_data in enumerate(test_responses):
        instruction = resp_data['instruction']
        response = resp_data['response']
        
        print(f"\n{'='*80}")
        print(f"TEST {i+1}: {resp_data['instruction_type']}")
        print(f"Instruction: {instruction}")
        print(f"Response: {response.split(chr(10)+chr(10))[0].strip()[:100]}...")
        print(f"Original Success: {'✅' if resp_data.get('success', False) else '❌'}")
        print(f"{'='*80}")
        
        # Create prompt
        prompt = create_good_bad_prompt(instruction, response)
        
        print(f"\nPROMPT (last few lines):")
        prompt_lines = prompt.split('\n')
        for line in prompt_lines[-5:]:
            print(f"  {line}")
        
        # Test Temperature 0 (deterministic)
        print(f"\n🌡️  TEMPERATURE 0:")
        temp0_response = generate_evaluation(model, tokenizer, prompt, temperature=0.0)
        temp0_judgment = extract_judgment(temp0_response)
        print(f"Raw response: '{temp0_response}'")
        print(f"Judgment: {temp0_judgment}")
        
        # Test Temperature 0.3 with majority voting (3 tries)
        print(f"\n🌡️  TEMPERATURE 0.3 + MAJORITY VOTING (3 tries):")
        temp03_responses = []
        temp03_judgments = []
        
        for trial in range(3):
            response_trial = generate_evaluation(model, tokenizer, prompt, temperature=0.3)
            judgment_trial = extract_judgment(response_trial)
            temp03_responses.append(response_trial)
            temp03_judgments.append(judgment_trial)
            print(f"  Trial {trial+1}: '{response_trial}' → {judgment_trial}")
        
        # Get majority vote
        good_count = sum(1 for j in temp03_judgments if j == 'GOOD')
        bad_count = sum(1 for j in temp03_judgments if j == 'BAD')
        unclear_count = len(temp03_judgments) - good_count - bad_count
        
        if good_count > bad_count:
            majority_judgment = 'GOOD'
        elif bad_count > good_count:
            majority_judgment = 'BAD'
        else:
            majority_judgment = 'unclear'
            
        print(f"  Counts: GOOD={good_count}, BAD={bad_count}, unclear={unclear_count}")
        print(f"  Majority: {majority_judgment}")
        
        # Store results
        result = {
            'instruction': instruction,
            'response': response.split('\n\n')[0].strip(),
            'instruction_type': resp_data['instruction_type'],
            'success_in_original': resp_data.get('success', False),
            'temp0': {
                'raw_response': temp0_response,
                'judgment': temp0_judgment
            },
            'temp03_majority': {
                'trials': list(zip(temp03_responses, temp03_judgments)),
                'majority_judgment': majority_judgment,
                'counts': {'good': good_count, 'bad': bad_count, 'unclear': unclear_count}
            },
            'agreement': temp0_judgment == majority_judgment
        }
        
        results.append(result)
        
        print(f"\n📊 COMPARISON:")
        print(f"  Temperature 0: {temp0_judgment}")
        print(f"  Temp 0.3 majority: {majority_judgment}")
        print(f"  Agreement: {'✅' if temp0_judgment == majority_judgment else '❌'}")
    
    # Analysis
    clear_temp0 = sum(1 for r in results if r['temp0']['judgment'] in ['GOOD', 'BAD'])
    clear_temp03 = sum(1 for r in results if r['temp03_majority']['majority_judgment'] in ['GOOD', 'BAD'])
    
    print(f"\n{'='*80}")
    print(f"📊 OVERALL ANALYSIS")
    print(f"{'='*80}")
    print(f"Clear judgments (GOOD/BAD only):")
    print(f"  Temperature 0: {clear_temp0}/{len(results)} ({clear_temp0/len(results):.1%})")
    print(f"  Temp 0.3 majority: {clear_temp03}/{len(results)} ({clear_temp03/len(results):.1%})")
    
    # Save results
    output_file = ARTIFACTS_DIR / "good_bad_format_test.json"
    with open(output_file, 'w') as f:
        json.dump({
            'results': results,
            'analysis': {
                'clear_temp0_rate': clear_temp0 / len(results),
                'clear_temp03_rate': clear_temp03 / len(results)
            }
        }, f, indent=2)
    
    logger.info(f"✅ Test complete! Results saved to {output_file}")
    
    # Cleanup
    del model
    torch.cuda.empty_cache()
    
    return results

if __name__ == "__main__":
    results = test_good_bad_format()
    print(f"\n🎉 Tested GOOD/BAD format on {len(results)} samples")
    print("Check if the exact pattern matching works better!")