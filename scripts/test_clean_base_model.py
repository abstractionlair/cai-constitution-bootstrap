#!/usr/bin/env python3
"""
Quick test to verify our chat template contamination fix
Tests a few prompts with the truly clean base model
"""

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

# Quantization config  
bnb_config = BitsAndBytesConfig(
    load_in_8bit=True,
    bnb_8bit_use_double_quant=True,
    bnb_8bit_quant_type="nf8",
    bnb_8bit_compute_dtype=torch.bfloat16
)

# Load tokenizer
print("Loading tokenizer...")
tokenizer = AutoTokenizer.from_pretrained(
    "Qwen/Qwen2.5-32B",
    trust_remote_code=True,
    use_fast=True
)

# CRITICAL: Disable chat template to ensure pure base model behavior  
tokenizer.chat_template = None

if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token

# Load model
print("Loading model...")
model = AutoModelForCausalLM.from_pretrained(
    "Qwen/Qwen2.5-32B",
    quantization_config=bnb_config,
    device_map="auto",
    trust_remote_code=True,
    dtype=torch.bfloat16
)

# Test prompts
test_prompts = [
    "What is gravity?",
    "Create a brief explanation on the topic of food",
    "Write a sentence about learning",
    "Answer this question: How does photosynthesis work?"
]

print("\n=== Testing Clean Base Model (No Chat Template) ===")
for i, prompt in enumerate(test_prompts, 1):
    print(f"\n{i}. Prompt: {prompt}")
    
    # Tokenize WITHOUT special tokens (no template contamination)
    inputs = tokenizer(
        prompt,
        add_special_tokens=False,  # CRITICAL: prevent template
        return_tensors="pt",
        max_length=200,
        truncation=True,
        padding=False
    )
    
    # Generate response
    with torch.no_grad():
        outputs = model.generate(
            inputs['input_ids'],
            max_new_tokens=50,
            temperature=0.7,
            do_sample=True,
            pad_token_id=tokenizer.eos_token_id,
            eos_token_id=tokenizer.eos_token_id
        )
    
    # Decode (remove input prompt)
    input_length = inputs['input_ids'].shape[1]
    response = tokenizer.decode(outputs[0][input_length:], skip_special_tokens=True)
    
    print(f"   Response: {response}")
    print(f"   (Length: {len(response)})")

print("\n=== Done ===")