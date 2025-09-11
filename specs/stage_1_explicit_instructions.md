# Stage 1: Explicit Instruction Following

## 📚 IMPORTANT: Read These Clarifications First
- **Stage 1 Evaluation Philosophy**: See `specs/stage_1_evaluation_philosophy.md`
- **Sequential Bootstrapping Architecture**: See `specs/sequential_bootstrapping_architecture.md`
- **Methodology for Reviewers**: See `/reviews/codex/METHODOLOGY_CLARIFICATION.md`

## CRITICAL: Baseline Assessment First!
Before ANY training, we must establish what the base model can already do. See `specs/baseline_assessment.md` for protocol.

## Core Insight
Before we can generate examples, evaluate text, or revise responses, the model must reliably FOLLOW EXPLICIT INSTRUCTIONS.

## What Stage 1 Is and Isn't

### What It IS:
- Teaching a base model to recognize instruction patterns
- Building the foundation for all future stages
- Transforming text completion into instruction following
- Using basic principles to guide data generation

### What It ISN'T:
- Full Constitutional AI (that's Stage 6)
- Constitutional alignment or tracking
- Complex multi-step reasoning
- Value alignment

## Task Definition
Train the model to follow single-step instructions across various forms:

### Type 1: Question Answering
```
"Answer this question: What is the capital of France?"
"Question: What causes rain? Answer:"
"Q: Who wrote Romeo and Juliet? A:"
```

### Type 2: Completion
```
"Complete this sentence: The largest planet in our solar system is ___"
"Finish this: Water freezes at ___"
"Fill in the blank: The human heart has ___ chambers"
```

### Type 3: Generation with Constraint
```
"Write a sentence about dogs"
"Generate a question about space"
"Create a greeting message"
"Produce a fact about history"
```

### Type 4: Simple Transformation
```
"Respond to this: How are you today?"
"Reply to: Thank you for your help"
"React to this statement: The Earth is flat"
```

## Training Approach for Base Model

### Critical: Completion-Style Prompting
Since we're using a BASE model (not instruction-tuned), we must:
1. Use completion-style prompts for data generation
2. Include few-shot examples
3. Frame everything as text completion
4. NEVER assume the model understands instructions initially

### Data Generation Process
1. **Generate Instructions**: Use completion-style prompting
2. **Generate Responses**: Frame as "When asked X, the response is:"
3. **Generate Critiques**: "This response [complete with critique]"
4. **Generate Improvements**: "A better response would be:"
5. **Create Preference Pairs**: (chosen=improved, rejected=original)

## Evaluation Philosophy (CRITICAL)

### Both Models Get Raw Instructions
- **Base Model**: Gets "Answer this question: What is 2+2?"
- **Trained Model**: Gets "Answer this question: What is 2+2?"
- **Same test for both** - this is essential for valid comparison

### Expected Results
- **Base Model**: ~50% success (doesn't understand instructions)
- **Trained Model**: 95%+ success (learned to follow instructions)
- **The Delta**: This improvement IS what we're measuring

### Why NOT Completion-Style in Evaluation
If we gave the base model completion prompts during evaluation, we'd be:
- Testing different things for each model
- Helping the base model cheat
- Not measuring if training worked
- Making comparison invalid

## Constitutional Principles for Stage 1
These are used ONLY to guide critiques, not for alignment:
1. **Follow the instruction** - Do what was asked
2. **Be accurate** - Provide correct information
3. **Be complete** - Fully address the request
4. **Be concise** - Don't over-elaborate

Note: We don't track which principle is used. That comes in Stage 6.

## Success Metrics

### Primary Metric: Instruction Following Rate
- **Target**: 95%+ instructions followed correctly
- **Test**: Hold-out set of 100 diverse instructions
- **Evaluation**: Does the response do what was asked?
- **Method**: Both models tested with identical raw instructions

### What We're NOT Measuring (Yet)
- Constitutional adherence
- Principle tracking
- Value alignment
- Harmlessness (beyond basic instruction following)

## Relationship to Later Stages

### Stage 1 Provides Foundation For:
- Stage 2: Implicit instruction understanding
- Stage 3: Generation capabilities
- Stage 4: Evaluation capabilities
- Stage 5: Revision capabilities
- Stage 6: Constitutional integration (FULL CAI)

### Sequential Bootstrapping
Each stage uses the previous stage's model to generate training data for the next capability. This is intentional and critical to the architecture.

## Common Misunderstandings to Avoid

1. **"This should be full CAI"** - No, that's Stage 6
2. **"Track constitutional principles"** - No, that's Stage 6
3. **"Base model evaluation is unfair"** - No, that's the point
4. **"Need principle-specific critiques"** - No, just improve instruction following

## Implementation Plan

### Phase 1: Data Collection (3-4 hours)
1. Generate 1000 diverse instructions (completion-style)
2. Get initial responses (completion-style)
3. Critique against instruction following (completion-style)
4. Generate revisions (completion-style)
5. Create preference pairs

### Phase 2: Training (2-3 hours)
1. QLoRA fine-tuning with DPO
2. Monitor instruction-following accuracy
3. Validate on test set

### Phase 3: Validation (1 hour)
1. Test 100 held-out instructions (raw instructions to both models)
2. Measure success rate
3. Confirm improvement over baseline

## Total Time: 6-8 hours (~$12-14)

## Output
A model that reliably follows single-step instructions, providing the foundation for all subsequent stages. This is NOT a constitutionally aligned model yet - just one that can follow instructions.
