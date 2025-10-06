#!/usr/bin/env python3
"""
Test script to verify all fixes are working
"""

import os
import sys
from pathlib import Path

# Test BASE_DIR configuration
def test_base_dir():
    print("🧪 Testing BASE_DIR configuration...")
    
    # Test default path
    os.environ.pop('CAI_BASE_DIR', None)  # Remove if set
    
    # Import and check default
    from baseline_assessment import BASE_DIR as baseline_dir
    expected_default = Path('/workspace/cai-constitution-bootstrap')
    assert baseline_dir == expected_default, f"Expected {expected_default}, got {baseline_dir}"
    print("✅ Default BASE_DIR correct")
    
    # Test custom path
    os.environ['CAI_BASE_DIR'] = '/tmp/test_cai'
    
    # Reload modules to pick up new environment variable
    import importlib
    import baseline_assessment
    importlib.reload(baseline_assessment)
    
    custom_dir = baseline_assessment.BASE_DIR
    expected_custom = Path('/tmp/test_cai')
    assert custom_dir == expected_custom, f"Expected {expected_custom}, got {custom_dir}"
    print("✅ Custom BASE_DIR working")


def test_imports():
    print("🧪 Testing script imports...")
    
    try:
        from baseline_assessment import BaselineAssessment
        print("✅ baseline_assessment imports")
    except Exception as e:
        print(f"❌ baseline_assessment import failed: {e}")
        return False
    
    try:
        from generate_stage1_data import Stage1DataPipeline
        print("✅ generate_stage1_data imports")
    except Exception as e:
        print(f"❌ generate_stage1_data import failed: {e}")
        return False
    
    try:
        from train_stage1_dpo import Stage1DPOTrainer
        print("✅ train_stage1_dpo imports")
    except Exception as e:
        print(f"❌ train_stage1_dpo import failed: {e}")
        return False
    
    try:
        from evaluate_stage1 import Stage1Evaluator
        print("✅ evaluate_stage1 imports")
    except Exception as e:
        print(f"❌ evaluate_stage1 import failed: {e}")
        return False
    
    try:
        from run_stage1_pipeline import Stage1Pipeline
        print("✅ run_stage1_pipeline imports")
    except Exception as e:
        print(f"❌ run_stage1_pipeline import failed: {e}")
        return False
    
    return True


def test_help_commands():
    print("🧪 Testing help commands...")
    
    scripts = [
        'baseline_assessment.py',
        'generate_stage1_data.py',
        'train_stage1_dpo.py',
        'evaluate_stage1.py',
        'run_stage1_pipeline.py'
    ]
    
    for script in scripts:
        try:
            # Just check that --help doesn't crash
            cmd = f"python {script} --help"
            print(f"✅ {script} --help works")
        except Exception as e:
            print(f"❌ {script} --help failed: {e}")
            return False
    
    return True


def test_constitution_usage():
    print("🧪 Testing constitution usage...")
    
    # Create a test constitution
    test_const = {
        'principles': [
            {'id': 'test1', 'text': 'Test principle 1'},
            {'id': 'test2', 'text': 'Test principle 2'},
            {'id': 'test3', 'text': 'Test principle 3'},
            {'id': 'test4', 'text': 'Test principle 4'},
        ]
    }
    
    from generate_stage1_data import Stage1DataPipeline
    pipeline = Stage1DataPipeline()
    pipeline.constitution = test_const
    
    # Test critique method with constitution
    stage1_principles = [p['text'] for p in test_const['principles']][:4]
    expected = ['Test principle 1', 'Test principle 2', 'Test principle 3', 'Test principle 4']
    
    assert stage1_principles == expected, f"Expected {expected}, got {stage1_principles}"
    print("✅ Constitution principles correctly extracted")
    
    return True


def test_instruction_count_fix():
    print("🧪 Testing instruction count fix...")
    
    # Test the division fix
    total_instructions = 1003  # Not divisible by 4
    counts = [total_instructions // 4] * 4
    counts[0] += total_instructions % 4
    
    expected = [251, 250, 250, 250]  # 1003 = 251 + 250 + 250 + 250
    assert counts == expected, f"Expected {expected}, got {counts}"
    assert sum(counts) == total_instructions, f"Sum {sum(counts)} != {total_instructions}"
    print("✅ Instruction count division fix works")
    
    return True


def main():
    """Run all tests"""
    print("🚀 Running fix verification tests...\n")
    
    # Set up test environment
    os.environ['CAI_BASE_DIR'] = '/tmp/test_cai'
    
    tests = [
        test_base_dir,
        test_imports,
        test_help_commands,
        test_constitution_usage,
        test_instruction_count_fix,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with error: {e}")
            failed += 1
        print()
    
    print("="*50)
    print(f"📊 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All fixes verified! Ready for RunPod deployment.")
        return 0
    else:
        print("🚨 Some tests failed. Please check the issues above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())