#!/usr/bin/env python3
"""Show the exact prompts that were sent to the model"""

import json
import sys

def show_prompts(file_path):
    with open(file_path) as f:
        for i, line in enumerate(f):
            if i >= 10:  # Show first 10 examples
                break
            data = json.loads(line)
            print(f"Example {i+1}:")
            print(f"  Type: {data.get('instruction_type', 'unknown')}")
            print(f"  Instruction: {data['instruction']}")
            print(f"  Prompt sent to model: {data['prompt']}")
            print(f"  Response: {data['response'][:100]}...")
            print()

if __name__ == "__main__":
    show_prompts(sys.argv[1])