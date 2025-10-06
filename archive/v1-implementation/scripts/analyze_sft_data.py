#!/usr/bin/env python3
"""Analyze the generated SFT data to understand what we created"""

import json
import sys

def analyze_sft_data(file_path):
    """Analyze the SFT training data"""
    
    print("=== SFT Data Analysis ===\n")
    
    type_counts = {}
    samples = []
    
    with open(file_path, 'r') as f:
        for i, line in enumerate(f):
            data = json.loads(line)
            
            # Count types
            inst_type = data.get('instruction_type', 'unknown')
            type_counts[inst_type] = type_counts.get(inst_type, 0) + 1
            
            # Collect first 5 samples
            if i < 5:
                samples.append(data)
    
    print(f"Total Examples: {sum(type_counts.values())}")
    print("\nDistribution by Type:")
    for t, count in sorted(type_counts.items()):
        print(f"  {t}: {count}")
    
    print("\n=== Sample Examples ===\n")
    
    for i, sample in enumerate(samples, 1):
        print(f"Example {i}:")
        print(f"  Type: {sample.get('instruction_type', 'unknown')}")
        print(f"  Instruction: {sample['instruction']}")
        
        # Show what prompt was actually sent to the model
        if 'prompt' in sample:
            prompt = sample['prompt']
            if prompt != f"Instruction: {sample['instruction']}\nResponse:":
                print(f"  Actual Prompt to Model: {prompt}")
        
        response = sample['response']
        if len(response) > 200:
            response = response[:200] + "..."
        print(f"  Response: {response}")
        print()
    
    # Check if responses look like they came from base model or placeholders
    print("=== Response Analysis ===\n")
    
    # Sample more responses to check quality
    with open(file_path, 'r') as f:
        responses = []
        for i, line in enumerate(f):
            if i >= 20:  # Sample first 20
                break
            data = json.loads(line)
            responses.append(data['response'])
    
    # Check for known placeholder patterns
    placeholder_count = 0
    for resp in responses:
        if any(phrase in resp for phrase in [
            "essential nutrients",
            "fundamental force",
            "careful consideration",
            "interconnected concepts",
            "comprehensive insights"
        ]):
            placeholder_count += 1
    
    print(f"Responses analyzed: {len(responses)}")
    print(f"Likely placeholder responses: {placeholder_count}/{len(responses)}")
    
    if placeholder_count > len(responses) * 0.5:
        print("\n⚠️ WARNING: Many responses appear to be placeholders, not actual model generation!")
    else:
        print("\n✅ Responses appear to be from actual model generation")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python analyze_sft_data.py <jsonl_file>")
        sys.exit(1)
    
    analyze_sft_data(sys.argv[1])