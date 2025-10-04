# P0: Fix Evaluation Prompt Mismatch

**Priority**: P0 (HIGH - Biases results)
**Assigned To**: claude_code
**Estimated Time**: 30 minutes
**Created**: 2024-12-28 16:15
**Source**: Codex Review 20241228_153500_p0_fixes.md

## Problem
Evaluation sends raw instructions to the base model, but the base model was never trained on raw instructions - it expects completion-style prompts. This unfairly penalizes the base model in comparisons.

## Current Issue
```python
# Current evaluation (WRONG for base model):
response = generate_text(model, tokenizer, instruction, ...)
```

The base model receives: "Answer this question: What is 2+2?"
But it expects: "When asked 'What is 2+2?', the response is:"

## Required Fix

### 1. Import Completion Prompts
In `evaluate_stage1.py`, add import:
```python
from utils.data_formatter import CompletionStylePrompts
```

### 2. Modify Evaluation Function
```python
def evaluate_model(model, tokenizer, instructions: List[Dict], 
                   model_type: str = "base", max_examples: int = 100) -> Dict[str, Any]:
    """
    Evaluate model on instruction following
    
    Args:
        model: The model to evaluate
        tokenizer: Model tokenizer
        instructions: Test instructions
        model_type: "base" or "trained" - determines prompting style
        max_examples: Maximum examples to evaluate
    """
    
    # Initialize completion prompts for base model
    completion_prompts = CompletionStylePrompts() if model_type == "base" else None
    
    results = []
    evaluator = InstructionFollowingEvaluator()
    
    for instruction_data in tqdm(instructions[:max_examples], desc=f"Evaluating {model_type} model"):
        instruction = instruction_data['instruction']
        instruction_type = instruction_data['instruction_type']
        
        # CRITICAL FIX: Use appropriate prompting for model type
        if model_type == "base":
            # Base model needs completion-style prompt
            prompt = completion_prompts.create_response_prompt(instruction)
        else:
            # Trained model can handle raw instructions
            prompt = instruction
        
        # Generate response with deterministic settings
        response = generate_text(
            model, 
            tokenizer, 
            prompt,  # Now using appropriate prompt style
            max_new_tokens=150,
            temperature=0.1,  # Low temperature for consistency
            do_sample=False   # Deterministic for fair comparison
        )
        
        # Evaluate the response
        success, reason, details = evaluator.evaluate_response(
            instruction, response, instruction_type
        )
        
        results.append({
            'instruction': instruction,
            'prompt_used': prompt,  # Log what prompt was actually used
            'response': response,
            'success': success,
            'reason': reason,
            'details': details,
            'instruction_type': instruction_type,
            'model_type': model_type
        })
    
    # ... rest of evaluation code ...
```

### 3. Update Baseline Assessment
Similarly update `baseline_assessment.py`:
```python
def assess_baseline(model_name: str = "Qwen/Qwen2.5-32B"):
    # ... existing code ...
    
    # Add completion prompts
    completion_prompts = CompletionStylePrompts()
    
    # In evaluation loop:
    for instruction_data in eval_instructions:
        instruction = instruction_data['instruction']
        
        # Use completion-style for base model
        prompt = completion_prompts.create_response_prompt(instruction)
        
        response = generate_text(
            model, tokenizer, prompt,  # Use completion-style prompt
            max_new_tokens=150,
            temperature=0.1,
            do_sample=False
        )
        # ... rest of evaluation ...
```

### 4. Add Comparison Mode (Optional but Recommended)
Add a function to compare both prompting styles:
```python
def compare_prompting_styles(model, tokenizer, instructions, max_examples=50):
    """Compare raw vs completion-style prompting on base model"""
    
    completion_prompts = CompletionStylePrompts()
    evaluator = InstructionFollowingEvaluator()
    
    raw_results = []
    completion_results = []
    
    for instruction_data in instructions[:max_examples]:
        instruction = instruction_data['instruction']
        instruction_type = instruction_data['instruction_type']
        
        # Test raw instruction
        raw_response = generate_text(
            model, tokenizer, instruction,
            max_new_tokens=150, temperature=0.1, do_sample=False
        )
        raw_success, _, _ = evaluator.evaluate_response(
            instruction, raw_response, instruction_type
        )
        raw_results.append(raw_success)
        
        # Test completion-style
        completion_prompt = completion_prompts.create_response_prompt(instruction)
        completion_response = generate_text(
            model, tokenizer, completion_prompt,
            max_new_tokens=150, temperature=0.1, do_sample=False
        )
        comp_success, _, _ = evaluator.evaluate_response(
            instruction, completion_response, instruction_type
        )
        completion_results.append(comp_success)
    
    print(f"Raw instruction success: {sum(raw_results)}/{len(raw_results)} = {sum(raw_results)/len(raw_results)*100:.1f}%")
    print(f"Completion-style success: {sum(completion_results)}/{len(completion_results)} = {sum(completion_results)/len(completion_results)*100:.1f}%")
    
    return raw_results, completion_results
```

## Files to Modify
- `scripts/evaluate_stage1.py`
- `scripts/baseline_assessment.py`

## Success Criteria
- [ ] Base model evaluated with completion-style prompts
- [ ] Trained model evaluated with raw instructions
- [ ] Prompt style logged in results
- [ ] Deterministic evaluation (temperature=0.1, do_sample=False)
- [ ] Fair comparison between base and trained models

## Testing
1. Run evaluation on 10 instructions with base model using both styles
2. Verify completion-style performs better than raw for base model
3. Run full evaluation with appropriate prompting for each model type
4. Check that results JSON includes `prompt_used` field
5. Verify improved base model performance with proper prompting
