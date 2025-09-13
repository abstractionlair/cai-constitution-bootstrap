#!/usr/bin/env python3
"""
Test new narrative-style critique prompts on a few samples
"""

import json
import sys
import os
import torch
from pathlib import Path
import logging

# Setup paths
BASE_DIR = Path(os.getenv('CAI_BASE_DIR', '/workspace/runs/stage1_20250911_131105/code'))
ARTIFACTS_DIR = BASE_DIR / "artifacts"
sys.path.insert(0, str(BASE_DIR / 'scripts'))
sys.path.insert(0, str(BASE_DIR / 'scripts' / 'utils'))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_narrative_critique_prompt(instruction, response):
    """Create narrative-style critique prompt"""
    
    # Clean up the response - extract just the first part before any training examples
    clean_response = response.split('\n\n')[0].strip()  # Take first paragraph only
    
    prompt = """This is a report on the pretraining of model X. The evaluation team has critiqued the initial samples of model responses as shown below.

Instruction: "Answer this question: What is 2+2?"
Response: "I cannot help with math questions."
Critique: The response fails to follow the instruction. The question asked for a specific answer but the model refused to provide it.

Instruction: "Complete this sentence: The sun rises in the"
Response: "east"
Critique: The response correctly follows the instruction by completing the sentence appropriately.

Instruction: "Write one sentence about dogs."
Response: "Dogs."
Critique: The response is incomplete. The instruction asked for a sentence but only provided one word.

Instruction: "{instruction}"
Response: "{response}"
Critique:""".format(instruction=instruction, response=clean_response)
    
    return prompt

def create_narrative_improvement_prompt(instruction, response, critique):
    """Create narrative-style improvement prompt"""
    
    clean_response = response.split('\n\n')[0].strip()
    
    prompt = """After reviewing the critiques, the team generated improved responses.

Original: "I cannot help with math questions."
Improved: "4"

Original: "Dogs."
Improved: "Dogs are loyal companions to humans."

Original: "The sun is a star that provides energy."
Improved: "east"

Original: "{response}"
Improved:""".format(response=clean_response)
    
    return prompt

def test_narrative_prompts():
    """Test narrative prompts on a few samples"""
    
    logger.info("🧪 Testing narrative-style critique prompts")
    
    # Load a few responses
    responses_file = ARTIFACTS_DIR / "initial_responses.jsonl"
    with open(responses_file) as f:
        responses = [json.loads(line) for line in f]
    
    # Test on first 2 responses
    test_responses = responses[:2]
    
    logger.info(f"Testing on {len(test_responses)} samples")
    
    # Load model
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    
    model_name = "Qwen/Qwen2.5-32B"
    
    # Quick loading
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
    
    # Test each sample
    results = []
    
    for i, resp_data in enumerate(test_responses):
        instruction = resp_data['instruction']
        response = resp_data['response']
        
        print(f"\n{'='*60}")
        print(f"TEST {i+1}: {resp_data['instruction_type']}")
        print(f"Instruction: {instruction}")
        print(f"Original Response: {response[:100]}...")
        print(f"{'='*60}")
        
        # Test critique generation
        critique_prompt = create_narrative_critique_prompt(instruction, response)
        
        print(f"\nCRITIQUE PROMPT:")
        print(f"{critique_prompt}")
        
        # Generate critique
        inputs = tokenizer(critique_prompt, return_tensors='pt', truncation=True, max_length=1600)
        inputs = inputs.to(model.device)
        
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=80,
                temperature=0.7,
                do_sample=True,
                top_p=0.9,
                pad_token_id=tokenizer.eos_token_id,
                eos_token_id=tokenizer.eos_token_id
            )
        
        new_tokens = outputs[0][inputs['input_ids'].shape[1]:]
        critique = tokenizer.decode(new_tokens, skip_special_tokens=True).strip()
        
        print(f"\nGENERATED CRITIQUE:")
        print(f"{critique}")
        
        # Test improvement generation
        improvement_prompt = create_narrative_improvement_prompt(instruction, response, critique)
        
        print(f"\nIMPROVEMENT PROMPT:")
        print(f"{improvement_prompt}")
        
        # Generate improvement
        inputs = tokenizer(improvement_prompt, return_tensors='pt', truncation=True, max_length=1600)
        inputs = inputs.to(model.device)
        
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=100,
                temperature=0.7,
                do_sample=True,
                top_p=0.9,
                pad_token_id=tokenizer.eos_token_id,
                eos_token_id=tokenizer.eos_token_id
            )
        
        new_tokens = outputs[0][inputs['input_ids'].shape[1]:]
        improvement = tokenizer.decode(new_tokens, skip_special_tokens=True).strip()
        
        print(f"\nGENERATED IMPROVEMENT:")
        print(f"{improvement}")
        
        results.append({
            'instruction': instruction,
            'original_response': response.split('\n\n')[0].strip(),
            'critique': critique,
            'improvement': improvement
        })
    
    # Save results
    test_file = ARTIFACTS_DIR / "narrative_prompt_test.json"
    with open(test_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    logger.info(f"✅ Test complete! Results saved to {test_file}")
    
    # Cleanup
    del model
    torch.cuda.empty_cache()
    
    return results

if __name__ == "__main__":
    results = test_narrative_prompts()
    print(f"\n🎉 Tested narrative prompts on {len(results)} samples")
    print("Check the output above to see if the approach works better!")