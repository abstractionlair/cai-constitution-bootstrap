#!/usr/bin/env python3
"""
Quick preview script for generated responses
"""

import json
import sys
from pathlib import Path
from collections import Counter

def preview_responses(responses_file):
    """Preview generated responses with basic stats"""
    
    with open(responses_file) as f:
        responses = [json.loads(line) for line in f]
    
    print(f"📊 Generated {len(responses)} responses")
    
    # Basic stats
    by_type = Counter(r['instruction_type'] for r in responses)
    success_count = sum(1 for r in responses if r.get('success', False))
    
    print(f"✅ Success rate: {success_count/len(responses):.1%} ({success_count}/{len(responses)})")
    print(f"\n📋 By type:")
    for inst_type, count in by_type.items():
        type_success = sum(1 for r in responses if r['instruction_type'] == inst_type and r.get('success', False))
        print(f"  {inst_type}: {count} ({type_success/count:.1%} success)")
    
    # Show samples
    print(f"\n✅ Sample successful responses:")
    successful = [r for r in responses if r.get('success', False)][:3]
    for i, resp in enumerate(successful):
        print(f"\n{i+1}. [{resp['instruction_type']}] {resp['instruction']}")
        print(f"   Response: {resp['response'][:100]}...")
    
    # Show failures
    failed = [r for r in responses if not r.get('success', False)]
    if failed:
        print(f"\n❌ Sample failed responses:")
        for i, resp in enumerate(failed[:3]):
            print(f"\n{i+1}. [{resp['instruction_type']}] {resp['instruction']}")
            print(f"   Response: {resp['response'][:100]}...")
    
    return responses

if __name__ == "__main__":
    if len(sys.argv) > 1:
        responses_file = Path(sys.argv[1])
    else:
        responses_file = Path("artifacts/initial_responses.jsonl")
    
    if not responses_file.exists():
        print(f"❌ Responses file not found: {responses_file}")
        sys.exit(1)
    
    preview_responses(responses_file)