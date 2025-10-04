#!/usr/bin/env python3
"""
Quick test to verify our chat template contamination fix
Tests a few prompts with the truly clean base model
"""

import torch
import sys
from pathlib import Path

# Add utils to path
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from utils.clean_model_loader import CleanModelLoader

# Load model via CleanModelLoader (guaranteed contamination-free)
print("Loading model via CleanModelLoader...")
loader = CleanModelLoader("Qwen/Qwen2.5-32B", load_in_8bit=True)
model, tokenizer, provenance = loader.load()
print(f"Loader version: {provenance['loader_version'][:8]}")

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

    # Use CleanModelLoader's generate method (guaranteed safe)
    response = loader.generate(
        model,
        tokenizer,
        prompt,
        max_new_tokens=50,
        temperature=0.7
    )

    print(f"   Response: {response}")
    print(f"   (Length: {len(response)})")

print("\n=== Done ===")