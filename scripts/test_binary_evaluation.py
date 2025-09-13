#!/usr/bin/env python3
"""
Test binary good/bad evaluation with temperature 0 vs low temp + majority voting
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

def create_binary_evaluation_prompt(instruction, response):
    """Create binary good/bad evaluation prompt"""
    
    # Clean up the response
    clean_response = response.split('\n\n')[0].strip()
    
    prompt = """This document evaluates instruction-following quality for language model responses.

Section 2: Evaluation Rubric
The following examples show good vs bad instruction following:

Instruction: "Answer this question: What is 2+2?"
Response: "I cannot help with math questions."
Judgment: bad

Instruction: "Answer this question: What is 2+2?"
Response: "4"
Judgment: good

Instruction: "Complete this sentence: The sun rises in the"
Response: "east"
Judgment: good

Instruction: "Write one sentence about dogs."
Response: "Dogs."
Judgment: bad

Instruction: "Write one sentence about dogs."
Response: "Dogs are loyal companions to humans."
Judgment: good

Section 3: Current Evaluation
We evaluated one message using the rubric in section 2.

Instruction: "{instruction}"
Response: "{response}"
The response was judged to be """.format(instruction=instruction, response=clean_response)
    
    return prompt

def generate_evaluation(model, tokenizer, prompt, temperature=0.0):
    """Generate a single good/bad evaluation"""
    
    inputs = tokenizer(prompt, return_tensors='pt', truncation=True, max_length=1600)
    inputs = inputs.to(model.device)
    
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=5,  # Just need "good" or "bad"
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
    """Extract 'good' or 'bad' from response"""
    response_lower = response.lower().strip()
    
    if response_lower.startswith('good'):
        return 'good'
    elif response_lower.startswith('bad'):
        return 'bad'
    else:
        # Try to find good/bad anywhere in the response
        if 'good' in response_lower:
            return 'good'
        elif 'bad' in response_lower:
            return 'bad'
        else:
            return 'unclear'

def test_binary_evaluation():
    """Test binary evaluation approaches"""
    
    logger.info("🧪 Testing binary good/bad evaluation approaches")
    
    # Load a few responses to test
    responses_file = ARTIFACTS_DIR / "initial_responses.jsonl"
    with open(responses_file) as f:
        responses = [json.loads(line) for line in f]
    
    # Test on first 5 responses
    test_responses = responses[:5]
    
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
        print(f"{'='*80}")
        
        # Create prompt
        prompt = create_binary_evaluation_prompt(instruction, response)
        
        # Test 1: Temperature 0 (deterministic)
        print(f"\n🌡️  TEMPERATURE 0 (deterministic):")
        temp0_response = generate_evaluation(model, tokenizer, prompt, temperature=0.0)
        temp0_judgment = extract_judgment(temp0_response)
        print(f"Raw response: '{temp0_response}'")
        print(f"Judgment: {temp0_judgment}")
        
        # Test 2: Temperature 0.3 with majority voting (5 tries)
        print(f"\n🌡️  TEMPERATURE 0.3 + MAJORITY VOTING (5 tries):")
        temp03_responses = []
        temp03_judgments = []
        
        for trial in range(5):
            response_trial = generate_evaluation(model, tokenizer, prompt, temperature=0.3)
            judgment_trial = extract_judgment(response_trial)
            temp03_responses.append(response_trial)
            temp03_judgments.append(judgment_trial)
            print(f"  Trial {trial+1}: '{response_trial}' → {judgment_trial}")
        
        # Get majority vote
        judgment_counts = Counter(temp03_judgments)
        majority_judgment = judgment_counts.most_common(1)[0][0]
        majority_count = judgment_counts.most_common(1)[0][1]
        
        print(f"  Majority: {majority_judgment} ({majority_count}/5)")
        
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
                'majority_count': majority_count,
                'unanimous': majority_count == 5
            },
            'agreement': temp0_judgment == majority_judgment
        }
        
        results.append(result)
        
        print(f"\n📊 COMPARISON:")
        print(f"  Temperature 0: {temp0_judgment}")
        print(f"  Temp 0.3 majority: {majority_judgment}")
        print(f"  Agreement: {'✅' if temp0_judgment == majority_judgment else '❌'}")
        print(f"  Original success: {'✅' if resp_data.get('success', False) else '❌'}")
    
    # Analysis
    agreement_count = sum(1 for r in results if r['agreement'])
    agreement_rate = agreement_count / len(results)
    
    unanimous_count = sum(1 for r in results if r['temp03_majority']['unanimous'])
    unanimous_rate = unanimous_count / len(results)
    
    print(f"\n{'='*80}")
    print(f"📊 OVERALL ANALYSIS")
    print(f"{'='*80}")
    print(f"Agreement between temp0 and temp0.3 majority: {agreement_count}/{len(results)} ({agreement_rate:.1%})")
    print(f"Unanimous temp0.3 votes: {unanimous_count}/{len(results)} ({unanimous_rate:.1%})")
    
    # Check alignment with original success ratings
    temp0_alignment = sum(1 for r in results if 
                         (r['temp0']['judgment'] == 'good') == r['success_in_original'])
    temp03_alignment = sum(1 for r in results if 
                          (r['temp03_majority']['majority_judgment'] == 'good') == r['success_in_original'])
    
    print(f"\nAlignment with original success ratings:")
    print(f"  Temperature 0: {temp0_alignment}/{len(results)} ({temp0_alignment/len(results):.1%})")
    print(f"  Temp 0.3 majority: {temp03_alignment}/{len(results)} ({temp03_alignment/len(results):.1%})")
    
    # Save results
    output_file = ARTIFACTS_DIR / "binary_evaluation_test.json"
    with open(output_file, 'w') as f:
        json.dump({
            'results': results,
            'analysis': {
                'agreement_rate': agreement_rate,
                'unanimous_rate': unanimous_rate,
                'temp0_alignment': temp0_alignment / len(results),
                'temp03_alignment': temp03_alignment / len(results)
            }
        }, f, indent=2)
    
    logger.info(f"✅ Test complete! Results saved to {output_file}")
    
    # Cleanup
    del model
    torch.cuda.empty_cache()
    
    return results

if __name__ == "__main__":
    results = test_binary_evaluation()
    print(f"\n🎉 Tested binary evaluation on {len(results)} samples")
    print("Check the output above to compare temperature 0 vs majority voting approaches!")