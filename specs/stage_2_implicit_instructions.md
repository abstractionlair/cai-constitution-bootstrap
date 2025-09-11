# Stage 2: Implicit Instructions (Questions & Context)

## Core Insight
Questions ARE instructions. The model needs to learn that "What is X?" implicitly means "Tell me about X."

## Prerequisites
- Stage 1 model that follows explicit instructions with 95%+ accuracy
- This model will help us generate training data

## Task Definition
Train the model to recognize and respond to implicit instructions:

### Type 1: Direct Questions
```
"What is the capital of France?"
"How does photosynthesis work?"
"Why is the sky blue?"
"When was the internet invented?"
"Who wrote Romeo and Juliet?"
```

### Type 2: Incomplete Statements (Implicit Completion)
```
"The capital of France is..."
"2 + 2 equals..."
"The largest planet in our solar system is..."
"Water freezes at..."
```

### Type 3: Conversational Implications
```
"Hello!"  # Implicit: respond with greeting
"Thank you"  # Implicit: acknowledge appropriately
"I'm confused about quantum physics"  # Implicit: explain/help
```

### Type 4: Mathematical/Logical Prompts
```
"2 + 2 = ?"
"If A=1 and B=2, then A+B = ?"
"Complete the sequence: 1, 2, 4, 8, ..."
```

## Why Stage 2?

Stage 1 taught explicit instruction following. But real users don't always say "Answer this question:" before asking. Stage 2 bridges this gap, making the model useful for natural interaction.

## Training Data Generation

### Using Stage 1 Model
```python
# Stage 1 can follow these instructions:
stage1_model("Generate a question about science")
# -> "What causes lightning?"

stage1_model("Create a math problem")
# -> "What is 15 multiplied by 7?"

stage1_model("Write an incomplete sentence about geography")
# -> "The longest river in the world is..."
```

### Data Structure
```python
{
    "prompt": "What is gravity?",  # Implicit instruction
    "expected_behavior": "Provide an informative answer",
    "initial_response": "[Stage 1 might not respond well to bare question]",
    "improved_response": "Gravity is a fundamental force...",
    "pair": {
        "chosen": "Gravity is a fundamental force...",
        "rejected": "[Non-response or confusion]"
    }
}
```

## Constitutional Principles for Stage 2
1. **Recognize implicit instructions** - Questions need answers
2. **Respond appropriately** - Match the implicit intent
3. **Be helpful** - Don't be overly literal
4. **Maintain Stage 1 capabilities** - Still follow explicit instructions

## Implementation Plan

### Phase 1: Data Generation (3-4 hours)
1. Use Stage 1 model to generate 500+ questions
2. Generate 200+ incomplete statements
3. Add conversational prompts
4. Get initial responses (may be poor)
5. Generate improved responses
6. Create preference pairs

### Phase 2: Training (2-3 hours)
1. Start from Stage 1 checkpoint
2. QLoRA fine-tuning with DPO
3. Balance explicit and implicit instructions in training
4. Monitor both capabilities

### Phase 3: Validation (1 hour)
1. Test 100 explicit instructions (should maintain 95%+)
2. Test 100 implicit instructions (target 90%+)
3. Ensure no catastrophic forgetting

## Success Metrics

### Primary: Implicit Instruction Recognition
- **Target**: 90%+ appropriate responses to questions
- **Test**: Mix of question types
- **Evaluation**: Does it answer rather than get confused?

### Secondary: Maintained Explicit Performance
- **Target**: Still 95%+ on explicit instructions
- **Test**: Stage 1 test set
- **Evaluation**: No degradation from Stage 1

## What This Enables

With Stage 2 complete, the model can:

### Generate More Natural Data (for Stage 3)
```python
stage2_model("What kind of questions do users ask AI assistants?")
# -> Can now answer this meta-question

stage2_model("Generate a question about science")
# -> Still works from Stage 1
```

### Handle Real User Interactions
```python
stage2_model("What is machine learning?")
# -> Provides informative answer

stage2_model("Explain quantum computing")
# -> Recognizes implicit instruction to explain
```

## Common Failure Modes to Watch

1. **Over-answering**: Treating non-questions as questions
2. **Under-answering**: Still requiring explicit instructions
3. **Catastrophic forgetting**: Losing Stage 1 abilities
4. **Confusion**: Mixing explicit and implicit responses

## Mitigation Strategies

1. **Balanced training**: 50/50 explicit/implicit in training data
2. **Careful evaluation**: Test both capabilities regularly
3. **Curriculum learning**: Start with clear questions, add ambiguous ones
4. **Preserve Stage 1**: Use Stage 1 as initialization, small learning rate

## Total Time: 6-8 hours (~$12-14)

## Output
A model that handles both explicit instructions AND implicit ones (questions, context), ready to help generate training data for Stage 3.
