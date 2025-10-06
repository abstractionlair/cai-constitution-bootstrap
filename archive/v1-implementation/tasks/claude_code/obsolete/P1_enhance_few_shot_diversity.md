# P1: Enhance Few-Shot Example Diversity

**Priority**: P1 (Medium - Improves robustness)
**Estimated Time**: 30 minutes
**Created**: 2024-12-28 16:35
**Source**: Codex Review 20241228_160000_corrected_p0_implementation.md

## Problem
Current few-shot examples are simple and may lead to prompt imitation artifacts. Need more diverse examples including near-miss cases for critiques.

## Current State
Few-shot examples are functional but basic:
- Response generation: 3 simple examples
- Critique generation: 2 basic wrong/off-topic examples  
- Limited diversity in instruction types and response qualities

## Required Enhancements

### 1. Expand Response Generation Examples
In `scripts/utils/data_formatter.py`, CompletionStylePrompts class:

```python
@staticmethod
def create_response_generation_prompt(instruction: str) -> str:
    examples = [
        # Mathematical
        {'instruction': 'The answer to "What is 2+2?" is:', 'response': '4'},
        
        # Completion
        {'instruction': 'Complete this sentence: The sun rises in the', 'response': 'east'},
        
        # Factual
        {'instruction': 'Here is a fact about dogs:', 'response': 'Dogs are loyal and friendly companions to humans.'},
        
        # Creative
        {'instruction': 'Write a short sentence about winter:', 'response': 'Snow blankets the quiet landscape in pristine white.'},
        
        # Explanation  
        {'instruction': 'Explain what photosynthesis is:', 'response': 'Photosynthesis is the process by which plants convert sunlight into energy.'}
    ]
    # Use 3-4 examples randomly selected for diversity
```

### 2. Add Near-Miss Critique Examples
Enhance critique examples with subtle errors:

```python
@staticmethod 
def create_critique_generation_prompt(instruction: str, response: str, principle: str) -> str:
    examples = [
        # Completely wrong
        {
            'instruction': 'The answer to "What is the capital of France?" is:',
            'response': 'London',
            'critique': 'is incorrect. The capital of France is Paris, not London.'
        },
        
        # Off-topic
        {
            'instruction': 'Here is a fact about dogs:',
            'response': 'Cats are feline animals.',
            'critique': 'does not follow the prompt. The prompt asked for a fact about dogs, but the response is about cats.'
        },
        
        # Near-miss (partially correct but incomplete)
        {
            'instruction': 'Explain what photosynthesis is:',
            'response': 'Plants use sunlight.',
            'critique': 'is too brief and incomplete. While it mentions sunlight, it fails to explain the full process of converting sunlight, water, and CO2 into glucose and oxygen.'
        },
        
        # Accurate but too verbose
        {
            'instruction': 'What is 2+2?',
            'response': 'The mathematical operation of adding two plus two results in the sum of four, which is a fundamental arithmetic calculation...',
            'critique': 'is unnecessarily verbose. While correct, it provides excessive detail for a simple arithmetic question.'
        }
    ]
    # Use 2-3 examples to show variety of critique types
```

### 3. Diversify Improvement Examples
Add examples showing different types of improvements:

```python
@staticmethod
def create_improvement_generation_prompt(instruction: str, response: str, critique: str) -> str:
    examples = [
        # Factual correction
        {
            'instruction': 'The answer to "What is the capital of France?" is:',
            'response': 'London', 
            'critique': 'This response is incorrect. The capital of France is Paris, not London.',
            'improvement': 'Paris'
        },
        
        # Completeness improvement
        {
            'instruction': 'Explain what photosynthesis is:',
            'response': 'Plants use sunlight.',
            'critique': 'This response is too brief and incomplete.',
            'improvement': 'Photosynthesis is the process by which plants convert sunlight, water, and carbon dioxide into glucose and oxygen.'
        },
        
        # Relevance correction
        {
            'instruction': 'Write a sentence about dogs:',
            'response': 'Cats are independent animals.',
            'critique': 'This response is off-topic, discussing cats instead of dogs.',
            'improvement': 'Dogs are loyal and affectionate companions to humans.'
        }
    ]
```

### 4. Add Instruction Generation Diversity
Expand instruction generation examples per type:

```python
@staticmethod
def create_instruction_generation_prompt(instruction_type: str) -> str:
    examples = {
        'qa': [
            "The answer to 'What is 2+2?' is:",
            "When someone asks 'What is the capital of France?', the correct answer is:",
            "Q: How many days in a week? A:",
            "Question: What causes rain? Answer:",
            "The response to 'Who wrote Romeo and Juliet?' would be:"
        ],
        # ... similar expansion for other types
    }
    # Select 3-4 examples randomly for variety
```

## Files to Modify
- `scripts/utils/data_formatter.py` - CompletionStylePrompts class methods

## Success Criteria
- [ ] Response examples cover 4-5 different instruction types
- [ ] Critique examples include near-miss and edge cases
- [ ] Improvement examples show different improvement types
- [ ] Instruction generation has 4-5 diverse examples per type
- [ ] Examples selected randomly for variation across runs
- [ ] No decrease in base model completion quality

## Testing
1. Generate sample prompts using enhanced few-shot examples
2. Verify examples cover diverse scenarios and error types
3. Test that base model still follows completion patterns correctly
4. Confirm critique quality improves with near-miss examples
5. Check that improvements show various correction strategies

## Notes
- Non-blocking for Stage 1 but improves robustness
- Reduces risk of prompt imitation artifacts
- Provides better guidance for base model completion behavior
- Makes critique generation more nuanced and realistic