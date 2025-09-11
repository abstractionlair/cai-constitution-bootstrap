# Baseline Testing Protocol

## Priority: DO THIS FIRST!
Before any training, we need to know what the base model can actually do.

## Test Categories and Examples

### 1. Completions (Expected: 70-90% success)
```python
completions = [
    "The capital of France is",
    "Water boils at",
    "2 + 2 equals",
    "The sun is a",
    "Python is a programming",
]
# The model should complete these naturally
```

### 2. Direct Questions (Expected: 20-40% success)
```python
questions = [
    "What is the capital of France?",
    "How does photosynthesis work?",
    "Why is the sky blue?",
    "When was World War II?",
    "Who invented the telephone?",
]
# The model might not know to answer these
```

### 3. Explicit Instructions (Expected: 5-15% success)
```python
instructions = [
    "Answer this question: What is gravity?",
    "Complete the following: The moon orbits",
    "Tell me about the water cycle.",
    "List three primary colors.",
    "Explain what DNA is.",
]
# The model probably won't follow these
```

### 4. Commands (Expected: 5-15% success)
```python
commands = [
    "Write a sentence about dogs.",
    "Generate a fact about space.",
    "Create a short description of rain.",
    "Produce a statement about mathematics.",
    "Output information about computers.",
]
# The model likely won't understand these as commands
```

## Testing Protocol

```python
def test_baseline(model, tokenizer, category_name, prompts):
    """Test a category of prompts and score success."""
    results = []
    for prompt in prompts:
        # Generate response
        response = generate(model, tokenizer, prompt, max_tokens=50)
        
        # Manual evaluation criteria
        success = evaluate_response(prompt, response, category_name)
        results.append({
            'prompt': prompt,
            'response': response,
            'success': success
        })
    
    success_rate = sum(r['success'] for r in results) / len(results)
    return success_rate, results

def evaluate_response(prompt, response, category):
    """Simple heuristic evaluation."""
    if category == 'completions':
        # Check if it completes sensibly
        return len(response) > 5 and not response.startswith(prompt)
    
    elif category == 'questions':
        # Check if it provides an answer (not just repeating or continuing)
        return '?' not in response and len(response) > 10
    
    elif category in ['instructions', 'commands']:
        # Check if it actually follows the instruction
        # This is harder - might need manual review
        return 'Paris' in response if 'France' in prompt else len(response) > 10
```

## Expected Results

| Category | Base Model | After Stage 1 | Improvement |
|----------|-----------|---------------|-------------|
| Completions | 80% | 95% | +15% |
| Questions | 30% | 95% | +65% |
| Instructions | 10% | 95% | +85% |
| Commands | 10% | 95% | +85% |

## Output Format

Save results to: `results/baseline_assessment.json`

```json
{
    "model": "Qwen/Qwen2.5-32B",
    "timestamp": "2024-XX-XX",
    "categories": {
        "completions": {
            "success_rate": 0.80,
            "examples": [...]
        },
        "questions": {
            "success_rate": 0.30,
            "examples": [...]
        },
        "instructions": {
            "success_rate": 0.10,
            "examples": [...]
        },
        "commands": {
            "success_rate": 0.10,
            "examples": [...]
        }
    },
    "overall_success_rate": 0.325
}
```

## Why This Matters

1. **Honest Assessment**: Know what we're starting with
2. **True Improvement**: Can show real delta from training
3. **Scientific Rigor**: Baseline is essential for claims
4. **Debugging**: If base is better than expected, adjust approach
5. **Publication**: Makes our work more credible

## Action for Claude Code

1. Implement this baseline test FIRST
2. Run on the raw Qwen/Qwen2.5-32B model
3. Save results before any training
4. Report findings back
5. Then proceed with Stage 1

This baseline will take ~1 hour but is ESSENTIAL!
