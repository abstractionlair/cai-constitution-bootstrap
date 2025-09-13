# P0: Fix Completion-Style Prompting for Base Model

**Priority**: P0 (Critical - Core functionality broken)
**Estimated Time**: 2.0 hours
**Created**: 2024-12-28 14:30

## Problem
The current implementation treats the base model like an instruction-tuned model, sending raw instructions and expecting it to follow them. Base models need completion-style prompting throughout the entire pipeline.

## Context
- We're using Qwen-2.5-32B **base** model (NOT Instruct version)
- Base models do text completion, not instruction following
- Current code sends instructions like "Answer this question: What is 2+2?" directly
- This fundamentally breaks the bootstrapping concept

## Required Changes

### 1. Add Instruction Generation Module
Create new function in `scripts/utils/data_formatter.py`:
```python
def generate_instruction_completion_style(self, model, tokenizer, instruction_type: str) -> str:
    """Generate new instructions using completion-style prompting"""
    
    # Example for QA type
    prompt = """Here are examples of question-answering instructions:
- Answer this question: What is the capital of France?
- Q: What causes rain? A:
- Question: Who wrote Romeo and Juliet? Answer:

Another question-answering instruction would be:"""
    
    # Generate completion
    # Return the generated instruction
```

### 2. Fix Response Generation
In `scripts/generate_stage1_data.py`, modify `generate_initial_responses`:
```python
# OLD (WRONG):
response = generate_text(self.model, self.tokenizer, instruction, ...)

# NEW (CORRECT):
completion_prompt = f"""When given the instruction '{instruction}', a helpful assistant would respond with:"""
# OR:
completion_prompt = f"""Instruction: {instruction}
Response:"""

response = generate_text(self.model, self.tokenizer, completion_prompt, ...)
```

### 3. Fix Critique Generation
In `scripts/generate_stage1_data.py`, modify `_create_critique_prompt`:
```python
# OLD (WRONG):
prompt = f"Critique this response according to these principles..."

# NEW (CORRECT):
prompt = f"""An AI assistant was given this instruction: '{instruction}'
The assistant responded: '{response}'

According to the principle of '{principle}', a critique of this response would note that it"""
```

### 4. Fix Improvement Generation
In `scripts/generate_stage1_data.py`, modify `generate_improvements`:
```python
# OLD (WRONG):
improvement_prompt = f"Improve this response to better follow the instruction..."

# NEW (CORRECT):
improvement_prompt = f"""Instruction: '{instruction}'
Original response: '{response}'
Issues identified: '{critique}'

A better response that addresses these issues would be:"""
```

## Files to Modify
- `scripts/generate_stage1_data.py`
- `scripts/utils/data_formatter.py`
- `scripts/utils/model_loader.py` (may need helper functions)

## Success Criteria
- [ ] All prompting uses completion-style framing
- [ ] No direct instruction sending to base model
- [ ] Constitutional principles embedded in completion context
- [ ] Model can generate new instructions via completion
- [ ] Test with small sample to verify base model responds appropriately

## Testing
1. Generate 10 instructions using completion-style
2. Generate responses to those instructions using completion framing
3. Generate critiques using completion framing
4. Verify outputs make sense for a base model

## Notes
- This is CRITICAL - without this fix, the entire bootstrapping concept is invalid
- The base model doesn't understand "follow this instruction" - it only completes text
- Every interaction must be framed as text completion, not instruction following

## Status Updates
- [2024-12-28 14:50] Started implementation - Claude Code
- [2024-12-28 14:50] Analyzing current code structure for completion-style conversion
- [2024-12-28 14:55] Added CompletionStylePrompts class with few-shot examples
- [2024-12-28 14:55] Fixed response generation to use completion-style prompting
- [2024-12-28 14:55] Fixed critique generation to use completion-style prompting
- [2024-12-28 14:55] Fixed improvement generation to use completion-style prompting
- [2024-12-28 14:55] Added response cleaning to handle completion artifacts
- [2024-12-28 15:10] ✅ COMPLETED - All completion-style fixes implemented and tested
- [2024-12-28 15:10] ✅ All success criteria met - base model now uses completion prompts throughout
- [2024-12-28 15:10] ✅ Integration tested successfully with Stage 1 pipeline
