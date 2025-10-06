#!/usr/bin/env python3
"""
Show the exact raw prompt and model response for critique generation
"""

import json
import sys
import os
import torch
from pathlib import Path

# Setup paths
BASE_DIR = Path(os.getenv('CAI_BASE_DIR', '/workspace/runs/stage1_20250911_131105/code'))
ARTIFACTS_DIR = BASE_DIR / "artifacts"
sys.path.insert(0, str(BASE_DIR / 'scripts'))

def create_narrative_critique_prompt(instruction, response):
    """Create narrative-style critique prompt"""
    
    # Clean up the response - extract just the first part
    clean_response = response.split('\n\n')[0].strip()
    
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

def show_raw_prompts():
    """Show exact prompts and responses"""
    
    # Load one response
    responses_file = ARTIFACTS_DIR / "initial_responses.jsonl"
    with open(responses_file) as f:
        responses = [json.loads(line) for line in f]
    
    # Use the first response
    resp_data = responses[0]
    instruction = resp_data['instruction']
    response = resp_data['response']
    
    print("="*80)
    print("INSTRUCTION:")
    print(f'"{instruction}"')
    print("\n" + "="*80)
    print("ORIGINAL RESPONSE FROM BASE MODEL:")
    print(f'"{response}"')
    print("\n" + "="*80)
    print("CLEANED RESPONSE (what we'll use):")
    clean_response = response.split('\n\n')[0].strip()
    print(f'"{clean_response}"')
    print("\n" + "="*80)
    print("COMPLETE CRITIQUE PROMPT WE SEND TO MODEL:")
    print("=" * 80)
    
    critique_prompt = create_narrative_critique_prompt(instruction, response)
    print(critique_prompt)
    
    print("\n" + "="*80)
    print("NOW LOADING MODEL TO GET RESPONSE...")
    print("="*80)
    
    # Load model
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    
    model_name = "Qwen/Qwen2.5-32B"
    
    bnb_config = BitsAndBytesConfig(
        load_in_8bit=True,
        llm_int8_threshold=6.0,
        llm_int8_has_fp16_weight=False
    )
    
    print("Loading model...")
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
    
    print("✅ Model loaded, generating critique...")
    
    # Generate critique
    inputs = tokenizer(critique_prompt, return_tensors='pt', truncation=True, max_length=1600)
    inputs = inputs.to(model.device)
    
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=150,  # More tokens to see full response
            temperature=0.7,
            do_sample=True,
            top_p=0.9,
            pad_token_id=tokenizer.eos_token_id,
            eos_token_id=tokenizer.eos_token_id
        )
    
    # Get the full generated text (prompt + response)
    full_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
    
    # Extract just the new tokens (the model's response)
    new_tokens = outputs[0][inputs['input_ids'].shape[1]:]
    model_response = tokenizer.decode(new_tokens, skip_special_tokens=True)
    
    print("\n" + "="*80)
    print("COMPLETE RAW RESPONSE FROM MODEL:")
    print("="*80)
    print(repr(model_response))  # Use repr to show exact whitespace/newlines
    
    print("\n" + "="*80)
    print("SAME RESPONSE (READABLE):")
    print("="*80)
    print(model_response)
    
    # Save for inspection
    result = {
        'instruction': instruction,
        'original_response': response,
        'cleaned_response': clean_response,
        'critique_prompt': critique_prompt,
        'model_response': model_response
    }
    
    output_file = ARTIFACTS_DIR / "raw_prompt_analysis.json"
    with open(output_file, 'w') as f:
        json.dump(result, f, indent=2)
    
    print(f"\n✅ Complete analysis saved to {output_file}")
    
    # Cleanup
    del model
    torch.cuda.empty_cache()

if __name__ == "__main__":
    show_raw_prompts()