# Stage 1 Evaluation Methodology

## Automated Evaluation for Instruction Following

### Primary Metric: Response Validity Check
For each instruction type, we have clear success criteria:

#### Type 1: Question Answering
```python
instruction = "Answer this question: What is the capital of France?"
response = model.generate(instruction)

# Success criteria:
# - Contains an answer (not empty or refusal)
# - Mentions "Paris" or "capital" 
# - Is a statement, not a question back
success = (
    len(response) > 0 and
    not response.startswith("I don't") and
    ("Paris" in response or "capital" in response.lower())
)
```

#### Type 2: Completion Tasks
```python
instruction = "Complete this sentence: The sun is a..."
response = model.generate(instruction)

# Success criteria:
# - Actually completes the sentence (doesn't repeat prompt)
# - Provides a noun/noun phrase
# - Doesn't ask for clarification
success = (
    not response.startswith("Complete") and
    len(response.split()) <= 10 and  # Completion, not essay
    "?" not in response
)
```

#### Type 3: Generation Tasks  
```python
instruction = "Write one sentence about dogs"
response = model.generate(instruction)

# Success criteria:
# - Is a single sentence (has period, no multiple sentences)
# - Mentions dogs or related terms
# - Is a statement about dogs, not a question
success = (
    response.count('.') == 1 and
    any(word in response.lower() for word in ['dog', 'canine', 'puppy', 'pet']) and
    "?" not in response
)
```

### Evaluation Set Structure
```python
eval_set = {
    "answer_questions": 30,     # 30 diverse questions
    "complete_sentences": 30,    # 30 completions
    "generate_content": 30,      # 30 generation tasks
    "respond_to_input": 10       # 10 response tasks
}
# Total: 100 test cases
```

### Success Rate Calculation
```python
def evaluate_instruction_following(model, eval_set):
    results = []
    for instruction_type, examples in eval_set.items():
        for example in examples:
            response = model.generate(example['instruction'])
            success = check_success(
                instruction_type, 
                example['instruction'], 
                response,
                example.get('expected_keywords', [])
            )
            results.append(success)
    
    success_rate = sum(results) / len(results)
    return success_rate, results
```

### Fallback: Human Spot-Checking
- Randomly sample 20 responses
- Quick human review for obvious failures
- If automated and human disagree >10%, investigate

## Why This Works
1. **Objective**: Clear pass/fail criteria
2. **Scalable**: Can test hundreds of examples
3. **Reproducible**: Same tests across stages
4. **Fast**: No human bottleneck
