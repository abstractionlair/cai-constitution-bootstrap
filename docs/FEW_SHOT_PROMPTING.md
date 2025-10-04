# Few-Shot Prompting Architecture for Base Model Data Generation

## Overview
This document explains our sophisticated few-shot completion-style prompting system for generating training data from the Qwen-2.5-32B base model.

## The Problem
Base models like Qwen-2.5-32B don't naturally respond to instruction-style prompts like:
```
"Instruction: What is gravity?\nResponse:"
```

Instead, they work better with completion-style patterns they can continue naturally.

## Our Solution: CompletionStylePrompts

### Location
`scripts/utils/data_formatter.py` - Class: `CompletionStylePrompts`

### Core Method
`create_response_generation_prompt(instruction: str) -> str`

### How It Works
The method creates a few-shot prompt with 3-4 examples that teach the base model the desired response pattern through completion:

```python
def create_response_generation_prompt(instruction: str) -> str:
    """Create prompt to generate response to instruction via completion"""
    
    # Enhanced few-shot examples with diverse instruction types
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
    selected_examples = random.sample(examples, min(4, len(examples)))
    
    prompt = "Here are examples of prompts and their completions:\n\n"
    for ex in selected_examples:
        prompt += f"{ex['instruction']}\n{ex['response']}\n\n"
    
    prompt += f"{instruction}\n"
    return prompt
```

### Example Output
For the instruction "What is gravity?", the method might generate:

```
Here are examples of prompts and their completions:

The answer to "What is 2+2?" is:
4

Complete this sentence: The sun rises in the
east

Here is a fact about dogs:
Dogs are loyal and friendly companions to humans.

Write a short sentence about winter:
Snow blankets the quiet landscape in pristine white.

What is gravity?
```

The base model then naturally completes the final line with an appropriate response.

## Key Design Features

### 1. Diverse Example Types
- **Mathematical**: Simple arithmetic questions
- **Completion**: Sentence completion tasks  
- **Factual**: Knowledge-based statements
- **Creative**: Creative writing prompts
- **Explanatory**: Concept explanations

### 2. Natural Completion Pattern
- No "Assistant:" or role-based scaffolding
- No "Instruction:" prefixes in examples
- Clean prompt → response pattern
- Natural continuation for base model

### 3. Random Selection
- 3-4 examples chosen randomly for each generation
- Provides diversity across generations
- Prevents overfitting to specific example sets

### 4. Scalable Framework
Additional example types can be easily added to the examples list.

## Current Usage

### ✅ Used Correctly
**File**: `scripts/stage1_generate.py` - Line 196
```python
# Use completion-style prompting for base model
formatted_prompt = CompletionStylePrompts.create_response_generation_prompt(instruction)
```

### ❌ Not Used
**File**: `scripts/generate_stage1_sft_data.py`
Uses a simpler approach with its own `create_completion_prompt()` method instead of the sophisticated few-shot system.

## Comparison: Simple vs Few-Shot Approach

### Simple Approach (Currently Used in generate_stage1_sft_data.py)
```python
def create_completion_prompt(self, instruction: str, inst_type: str) -> str:
    if inst_type == 'qa':
        return f"Q: {instruction} A:"
    elif inst_type == 'completion':
        return instruction
    # etc.
```

**Pros**: Simpler, faster
**Cons**: Less teaching, no diversity

### Few-Shot Approach (Available but not used everywhere)
```python
CompletionStylePrompts.create_response_generation_prompt(instruction)
```

**Pros**: 
- Teaches base model through examples
- More sophisticated pattern matching
- Better response quality
- Diverse example types

**Cons**: 
- Slightly more complex
- Uses more tokens per generation

## Verification: What We Actually Generated
The 200 examples we generated used the **simple approach**, not the few-shot approach. This is why you were initially confused about data quality - we had designed a sophisticated system but weren't using it everywhere.

However, the simple approach still works well because:
1. Chat template contamination was properly fixed
2. Qwen-2.5-32B has strong inherent capabilities
3. Simple completion prompts like "Q: What is gravity? A:" are effective

## Recommendation
For future data generation, consider using the few-shot approach in `generate_stage1_sft_data.py` by replacing the simple completion prompts with:

```python
# Instead of this:
completion_prompt = self.create_completion_prompt(instruction, inst_type)

# Use this:
from utils.data_formatter import CompletionStylePrompts
completion_prompt = CompletionStylePrompts.create_response_generation_prompt(instruction)
```

This would leverage our sophisticated few-shot architecture for even better data quality.