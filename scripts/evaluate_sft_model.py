#!/usr/bin/env python3
"""
Quick evaluation of the trained SFT model vs base model
Tests instruction following capability on a few examples
"""

import torch
import time
from pathlib import Path
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import PeftModel
import sys
import os

# Setup paths
BASE_DIR = Path(os.getenv('CAI_BASE_DIR', '/workspace/runs/stage1_20250911_131105/code'))
SFT_CHECKPOINT = BASE_DIR / "checkpoints/stage1_sft/final"

def load_base_model():
    """Load base Qwen2.5-32B model"""
    print("🤖 Loading base model...")
    
    # Quantization for memory efficiency
    bnb_config = BitsAndBytesConfig(
        load_in_8bit=True,
        bnb_8bit_use_double_quant=True,
        bnb_8bit_quant_type="nf8",
        bnb_8bit_compute_dtype=torch.bfloat16
    )
    
    tokenizer = AutoTokenizer.from_pretrained(
        "Qwen/Qwen2.5-32B",
        trust_remote_code=True,
        padding_side='right'
    )
    
    # Disable chat template - use raw base model
    tokenizer.chat_template = None
    
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    
    model = AutoModelForCausalLM.from_pretrained(
        "Qwen/Qwen2.5-32B",
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True,
        dtype=torch.bfloat16
    )
    
    print("✅ Base model loaded")
    return model, tokenizer

def load_sft_model():
    """Load SFT-trained model"""
    print("🎯 Loading SFT model...")
    
    # Load base first
    base_model, tokenizer = load_base_model()
    
    # Add SFT LoRA adapters
    sft_model = PeftModel.from_pretrained(base_model, str(SFT_CHECKPOINT))
    
    print("✅ SFT model loaded")
    return sft_model, tokenizer

def generate_response(model, tokenizer, instruction, max_length=150):
    """Generate response for an instruction"""
    # Format exactly like training data
    prompt = f"Instruction: {instruction}\nResponse:"
    
    inputs = tokenizer(
        prompt,
        return_tensors="pt",
        truncation=True,
        max_length=256
    ).to(model.device)
    
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_length,
            temperature=0.7,
            do_sample=True,
            pad_token_id=tokenizer.pad_token_id,
            eos_token_id=tokenizer.eos_token_id,
            stop_strings=["END", "\n\n", "Instruction:"],
            tokenizer=tokenizer
        )
    
    # Decode only the new tokens
    response = tokenizer.decode(outputs[0][inputs['input_ids'].shape[1]:], skip_special_tokens=True)
    response = response.strip().split("END")[0].strip()
    
    return response

def run_evaluation():
    """Run side-by-side evaluation"""
    
    # Test instructions
    test_instructions = [
        "What is the capital of France?",
        "Explain what photosynthesis is in simple terms.",
        "Write a short poem about the ocean.",
        "How do you make scrambled eggs?",
        "What is 15 + 27?"
    ]
    
    print("🚀 Starting SFT Model Evaluation")
    print("=" * 50)
    
    # Load models
    print("\n📥 Loading models...")
    base_model, base_tokenizer = load_base_model()
    sft_model, sft_tokenizer = load_sft_model()
    
    print(f"\n🧪 Testing {len(test_instructions)} instructions...")
    print("=" * 50)
    
    # Test each instruction
    for i, instruction in enumerate(test_instructions, 1):
        print(f"\n[{i}/{len(test_instructions)}] Instruction: {instruction}")
        print("-" * 40)
        
        # Base model response
        print("🔵 Base Model:")
        start_time = time.time()
        base_response = generate_response(base_model, base_tokenizer, instruction)
        base_time = time.time() - start_time
        print(f"   {base_response}")
        print(f"   (⏱️ {base_time:.1f}s)")
        
        # SFT model response  
        print("\n🟢 SFT Model:")
        start_time = time.time()
        sft_response = generate_response(sft_model, sft_tokenizer, instruction)
        sft_time = time.time() - start_time
        print(f"   {sft_response}")
        print(f"   (⏱️ {sft_time:.1f}s)")
        
        print("-" * 40)
    
    print("\n✅ Evaluation complete!")
    print("\n💡 Key observations to look for:")
    print("   - SFT model should follow instruction format better")
    print("   - SFT model should be more direct and responsive")
    print("   - SFT model should avoid rambling or off-topic content")
    
    # Cleanup
    del base_model, sft_model
    torch.cuda.empty_cache()

if __name__ == "__main__":
    run_evaluation()