# P0: Add Few-Shot Examples for Completion Prompts

**Priority**: P0 (Critical - Required for base model)
**Estimated Time**: 1.5 hours
**Created**: 2024-12-28 14:35

## Problem
Base models work best with few-shot examples to establish patterns. We need to provide examples in our completion prompts to guide the model's behavior.

## Context
- Completion-style prompting requires examples to establish the pattern
- Current code has no few-shot learning setup
- Base model needs to see the pattern of instruction → response

## Required Changes

### 1. Create Few-Shot Example Banks
Create new file `scripts/utils/few_shot_examples.py`:
```python
class FewShotExamples:
    """Few-shot examples for completion prompting"""
    
    INSTRUCTION_GENERATION_EXAMPLES = {
        'qa': [
            "Answer this question: What is 2+2?",
            "Q: What is the capital of Japan? A:",
            "Question: How many days are in a week? Answer:",
        ],
        'completion': [
            "Complete this sentence: The sun rises in the",
            "Finish this: Water boils at",
            "Fill in the blank: A triangle has ___ sides",
        ],
        # etc.
    }
    
    RESPONSE_EXAMPLES = [
        {
            'instruction': "Answer this question: What is 2+2?",
            'response': "4"
        },
        {
            'instruction': "Complete this sentence: The sun rises in the",
            'response': "east"
        },
        # etc.
    ]
    
    CRITIQUE_EXAMPLES = [
        {
            'instruction': "Answer this question: What is the capital of France?",
            'response': "London",
            'critique': "is incorrect. The capital of France is Paris, not London."
        },
        {
            'instruction': "Write a sentence about dogs",
            'response': "Cats are feline animals",
            'critique': "does not follow the instruction. The instruction asked for a sentence about dogs, but the response is about cats."
        },
        # etc.
    ]
```

### 2. Update Instruction Generation
Use few-shot examples when generating new instructions:
```python
def generate_instruction_with_few_shot(self, instruction_type: str) -> str:
    examples = FewShotExamples.INSTRUCTION_GENERATION_EXAMPLES[instruction_type]
    
    prompt = f"""Here are examples of {instruction_type} instructions:
{chr(10).join(f'- {ex}' for ex in examples)}

Another {instruction_type} instruction would be:"""
    
    return generate_text(model, tokenizer, prompt, ...)
```

### 3. Update Response Generation
Use few-shot for response generation:
```python
def create_response_prompt(instruction: str) -> str:
    examples = FewShotExamples.RESPONSE_EXAMPLES[:3]  # Use 3 examples
    
    prompt = "Here are examples of instructions and their responses:\n\n"
    for ex in examples:
        prompt += f"Instruction: {ex['instruction']}\n"
        prompt += f"Response: {ex['response']}\n\n"
    
    prompt += f"Instruction: {instruction}\nResponse:"
    return prompt
```

### 4. Update Critique Generation
Use few-shot for critiques:
```python
def create_critique_prompt(instruction: str, response: str, principle: str) -> str:
    examples = FewShotExamples.CRITIQUE_EXAMPLES[:2]
    
    prompt = "Here are examples of response critiques:\n\n"
    for ex in examples:
        prompt += f"Instruction: '{ex['instruction']}'\n"
        prompt += f"Response: '{ex['response']}'\n"
        prompt += f"This response {ex['critique']}\n\n"
    
    prompt += f"Instruction: '{instruction}'\n"
    prompt += f"Response: '{response}'\n"
    prompt += f"According to the principle '{principle}', this response"
    
    return prompt
```

## Files to Create/Modify
- Create: `scripts/utils/few_shot_examples.py`
- Modify: `scripts/generate_stage1_data.py` (use few-shot examples)
- Modify: `scripts/utils/data_formatter.py` (integrate few-shot)

## Success Criteria
- [ ] Few-shot example bank created with diverse examples
- [ ] All completion prompts use 2-5 relevant examples
- [ ] Examples cover edge cases (wrong answers, off-topic, etc.)
- [ ] Model's completions follow the established pattern
- [ ] Quality of generated data improves significantly

## Testing
1. Test instruction generation with/without few-shot - compare quality
2. Test response generation with/without few-shot - measure instruction following
3. Test critique generation with/without few-shot - check relevance
4. Verify few-shot examples actually improve base model behavior

## Notes
- Few-shot examples are critical for base model performance
- Examples should be diverse but consistent in format
- Too many examples can confuse; 2-5 is usually optimal
- Examples should demonstrate both good and bad responses for critiques
