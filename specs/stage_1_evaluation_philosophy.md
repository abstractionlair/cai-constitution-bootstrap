# Stage 1 Evaluation Philosophy - CLARIFICATION

**Created**: 2024-12-28 16:45
**Purpose**: Clarify evaluation approach and prevent misunderstandings

## Critical Clarification: What Stage 1 Is Testing

### The Fundamental Goal
Stage 1 teaches a **base model** (which only knows text completion) to recognize and follow instruction patterns. This is the FIRST step in our sequential bootstrapping.

### What We're Measuring
- **Baseline**: Can the base model follow instructions? (Answer: No, ~50% success)
- **After Training**: Can it now follow instructions? (Target: 95% success)
- **The Delta**: This improvement IS the learning

## Why Both Models Get Raw Instructions

### This is NOT Unfair - It's the Whole Point
1. **Base Model + Raw Instructions = Expected Failure**
   - The base model doesn't understand "Answer this question: X"
   - It just continues the text
   - ~50% success by accident

2. **Trained Model + Raw Instructions = Expected Success**
   - We trained it to recognize instruction patterns
   - It should now understand "Answer this question: X" means provide an answer
   - 95%+ success is the goal

### What Would Be Wrong
If we gave the base model completion-style prompts during evaluation:
```python
# WRONG - This would help the base model cheat:
base_prompt = "When asked 'What is 2+2?', the response is:"
trained_prompt = "What is 2+2?"
```

This would test DIFFERENT things and make comparison meaningless.

### Correct Approach
```python
# CORRECT - Same test for both:
both_get = "Answer this question: What is 2+2?"
base_response = "..."      # Likely fails or continues text
trained_response = "4"      # Should answer correctly
```

## Sequential Bootstrapping Philosophy

### Stage-by-Stage Capability Building
We're NOT doing full Constitutional AI from the start. We're building capabilities sequentially:

1. **Stage 1**: Learn to follow explicit instructions (THIS STAGE)
   - Input: Raw instructions
   - Training: Completion-style generation → critique → improve → DPO
   - Output: Model that follows instructions

2. **Stage 2**: Learn implicit instructions (NEXT)
   - Uses Stage 1 model
   - More complex patterns

3. **Stages 3-5**: Build evaluation and revision capabilities
   - Each stage uses previous stage's model
   - Gradually more sophisticated

4. **Stage 6**: Constitutional Integration (FINAL)
   - Full CAI with all principles
   - Uses all previous capabilities

### Why Constitution Tracking Doesn't Matter in Stage 1
- We're using basic principles just to guide critiques
- Not claiming constitutional alignment yet
- Just learning instruction-following patterns
- Full constitutional tracking comes in Stage 6

## Common Misunderstandings to Avoid

### Misunderstanding 1: "Base model is disadvantaged"
**Reality**: That's the point - we're measuring if it learned to follow instructions

### Misunderstanding 2: "Need to track which constitutional principle"
**Reality**: Stage 1 is just about instruction following, not constitutional alignment

### Misunderstanding 3: "Should test base model with completion prompts"
**Reality**: That would defeat the purpose of measuring improvement

### Misunderstanding 4: "This isn't real CAI"
**Reality**: Correct! It's sequential bootstrapping TOWARD CAI. Stage 6 is where CAI happens.

## Evaluation Correctness Criteria

### What Makes Our Evaluation Valid
1. **Same Test for Both Models**: Raw instructions to both
2. **Clear Success Metrics**: Did it follow the instruction or not?
3. **Appropriate Baseline**: Base model's natural performance
4. **Measurable Improvement**: Delta between base and trained

### What Would Make It Invalid
1. Different prompting styles for each model
2. Helping the base model with completion prompts
3. Unclear success criteria
4. Comparing apples to oranges

## For Reviewers

### When Reviewing Stage 1
Please remember:
- This is teaching instruction-following, NOT full CAI
- Base model failure is expected and correct
- Same test for both models is required
- Constitutional integration comes later (Stage 6)

### Key Questions to Ask
✅ Do both models get the same input? (Should be yes)
✅ Is success clearly defined? (Should be yes)
✅ Can we measure improvement? (Should be yes)
❌ Are we tracking constitutional principles? (Not needed yet)
❌ Are we helping the base model? (Should be no)

## Summary
Stage 1 evaluation is correct as designed. We test both models with raw instructions to measure whether training successfully taught instruction-following. This is the foundation for all subsequent stages.
