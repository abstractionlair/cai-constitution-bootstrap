# P1: Create Completion-Style Test Suite
**Assigned To**: claude_code

**Priority**: P1 (High - Needed to verify fixes)
**Assigned To**: claude_code
**Estimated Time**: 1.0 hour
**Created**: 2024-12-28 14:40

## Problem
We need a test suite to verify that our completion-style prompting actually works with the base model before running the full pipeline.

## Context
- Can't test if completion prompting works without running it
- Need to verify base model behavior before expensive training runs
- Should test each component independently

## Required Changes

### 1. Create Test Script
Create `scripts/test_completion_prompting.py`:
```python
#!/usr/bin/env python3
"""Test completion-style prompting with base model"""

def test_instruction_generation():
    """Test if model can generate new instructions via completion"""
    # Load base model (8-bit for quality)
    # Create few-shot prompt
    # Generate 5 instructions
    # Manually verify they look like instructions
    pass

def test_response_generation():
    """Test if model can respond to instructions via completion framing"""
    test_instructions = [
        "Answer this question: What is 2+2?",
        "Complete this sentence: The sky is",
        "Write a fact about water"
    ]
    # For each instruction:
    #   - Create completion prompt with few-shot
    #   - Generate response
    #   - Check if response is relevant
    pass

def test_critique_generation():
    """Test if model can critique via completion"""
    test_cases = [
        {
            'instruction': "What is 2+2?",
            'response': "5",  # Wrong answer
            'expected_critique_contains': ["incorrect", "wrong", "4"]
        },
        {
            'instruction': "Write about dogs",
            'response': "Cats are great",  # Off topic
            'expected_critique_contains': ["dogs", "not about", "wrong topic"]
        }
    ]
    # Test each case
    pass

def test_improvement_generation():
    """Test if model can improve responses via completion"""
    # Take failed examples from critique test
    # Generate improvements
    # Verify improvements address the critiques
    pass

def run_small_pipeline():
    """Run mini version of full pipeline with 10 examples"""
    # Generate 10 instructions
    # Generate responses  
    # Generate critiques
    # Generate improvements
    # Create preference pairs
    # Save samples for manual review
    pass
```

### 2. Create Validation Metrics
Add to test script:
```python
def validate_instruction(text: str) -> bool:
    """Check if generated text looks like an instruction"""
    # Has imperative verb (answer, write, complete, etc.)
    # Reasonable length (5-50 words)
    # Ends with appropriate punctuation
    pass

def validate_response_relevance(instruction: str, response: str) -> float:
    """Score how relevant response is to instruction (0-1)"""
    # Check keyword overlap
    # Check if response type matches instruction type
    # Length appropriateness
    pass

def validate_critique(instruction: str, response: str, critique: str) -> bool:
    """Check if critique identifies real issues"""
    # References the instruction
    # References the response
    # Identifies specific problems
    pass
```

### 3. Create Sample Output Reviewer
```python
def save_samples_for_review(samples: list, filename: str):
    """Save samples in readable format for manual review"""
    output = []
    for i, sample in enumerate(samples):
        output.append(f"### Sample {i+1}")
        output.append(f"Instruction: {sample['instruction']}")
        output.append(f"Response: {sample['response']}")
        output.append(f"Critique: {sample['critique']}")
        output.append(f"Improvement: {sample.get('improvement', 'N/A')}")
        output.append("")
    
    with open(f"test_outputs/{filename}", 'w') as f:
        f.write('\n'.join(output))
```

## Files to Create
- `scripts/test_completion_prompting.py`
- `scripts/test_outputs/` (directory for test results)

## Success Criteria
- [ ] Test script runs without errors
- [ ] Generates valid instructions via completion
- [ ] Generates relevant responses via completion framing
- [ ] Generates meaningful critiques
- [ ] Generates improved responses
- [ ] Sample outputs look reasonable for manual review
- [ ] All tests pass with base model (not instruction-tuned)

## Testing Protocol
1. Run each test function independently
2. Review generated samples manually
3. Verify base model behavior matches expectations
4. Adjust prompts if needed based on results
5. Run full mini-pipeline test
6. Document any issues or adjustments needed

## Notes
- This test suite is essential before running expensive training
- Should take ~30 minutes to run all tests
- Manual review of outputs is critical
- If tests fail, need to adjust completion prompts before proceeding
- Save all test outputs for documentation
