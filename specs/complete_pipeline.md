# Progressive Bootstrapping Pipeline - Complete Specification

## Overview
Each stage builds a functional model that helps generate training data for the next stage. This is true self-bootstrapping where each model contributes to creating its successor.

## Stage Progression

### Stage 1: Explicit Instruction Following (6-8 hours)
**Goal**: Learn to follow explicit, unambiguous instructions

**Examples**:
```python
"Answer this question: What is the capital of France?"
"Complete this sentence: The largest planet is..."
"Generate a fact about: dolphins"
"Respond to this greeting: Hello!"
"Write one sentence about: weather"
```

**Output**: Model that reliably follows explicit instructions (95%+ success)

---

### Stage 2: Implicit Instructions (4-6 hours)
**Goal**: Learn that questions and contexts imply instructions

**Examples**:
```python
"What is the capital of France?"  # Implicit: provide answer
"How are you today?"               # Implicit: respond appropriately
"2 + 2 = ?"                       # Implicit: solve this
"The sun is a..."                 # Implicit: complete this
"Paris is the capital of..."      # Implicit: complete this
```

**Uses Stage 1 Model**: To help generate training data (it can follow "Generate a question" instructions)

**Output**: Model that handles both explicit and implicit instructions

---

### Stage 3: Generation Tasks (6-8 hours)
**Goal**: Learn to generate examples of specific types

**Examples**:
```python
"Generate a question about science"
"Create a user message asking for help"
"Write an example of a polite request"
"Produce a factual statement about history"
"Generate an instruction for an AI"
```

**Uses Stage 2 Model**: To help create diverse generation tasks

**Output**: Model that can create examples on demand

---

### Stage 4: Evaluation Tasks (6-8 hours)
**Goal**: Learn to judge and evaluate text

**Examples**:
```python
"Is this answer correct: [answer to check]"
"Is this response helpful: [response to evaluate]"
"Does this violate the principle: [principle + text]"
"Rate this response from 1-5: [text to rate]"
"Which is better, A or B: [two options]"
```

**Uses Stage 3 Model**: To generate examples to evaluate

**Output**: Model that can evaluate text quality

---

### Stage 5: Revision Tasks (6-8 hours)
**Goal**: Learn to improve existing text

**Examples**:
```python
"Make this more helpful: [text to improve]"
"Fix the errors in: [text with errors]"
"Rewrite this more clearly: [unclear text]"
"Improve this response: [weak response]"
"Revise according to feedback: [text + feedback]"
```

**Uses Stage 4 Model**: To identify what needs improvement

**Output**: Model that can revise and improve text

---

### Stage 6: Constitutional Integration (10+ hours)
**Goal**: Combine all abilities with constitutional principles

**Process**:
1. Use Stage 3 to generate diverse user prompts
2. Use Stage 2 to answer them
3. Use Stage 4 to critique against constitutional principles
4. Use Stage 5 to revise based on critiques
5. Create preference pairs (revised > original)
6. Train with DPO for constitutional alignment

**Output**: Constitutionally aligned model

---

## Why This Progression Works

### Dependencies Are Clear
- Stage 2 needs Stage 1 (must follow instructions to learn implicit ones)
- Stage 3 needs Stage 2 (must handle questions to generate them)
- Stage 4 needs Stage 3 (need examples to evaluate)
- Stage 5 needs Stage 4 (need evaluation to know what to improve)
- Stage 6 needs ALL previous stages

### Each Stage Is Focused
- One new capability per stage
- Clear success metrics
- Manageable training time
- Builds on previous success

### Training Data Quality Improves
- Stage 1: Human-generated instructions
- Stage 2: Stage 1 helps generate questions
- Stage 3: Stage 2 helps create generation tasks
- Stage 4: Stage 3 provides examples to evaluate
- Stage 5: Stage 4 identifies what to improve
- Stage 6: All stages contribute to CAI data

## Resource Requirements

### Per Stage
- **Compute**: 4-10 hours @ $1.74/hour = $7-17 per stage
- **Data**: 500-1000 examples per stage
- **Time**: 1 day per stage (including validation)

### Total Project
- **Stages 1-5**: ~$35-85
- **Stage 6**: ~$20-30
- **Total**: ~$55-115 (well within budget)

## Implementation Order

1. Start with Stage 1 (explicit instructions)
2. Validate it works (95%+ instruction following)
3. Proceed to Stage 2 (add implicit instructions)
4. Continue through stages sequentially
5. Each stage must work before proceeding

## Key Principles

1. **Don't skip stages** - Each builds on the previous
2. **Validate thoroughly** - Bad Stage N ruins Stage N+1
3. **Save everything** - Models, data, metrics from each stage
4. **Use previous models** - Each stage uses earlier models to generate data
5. **Quality over quantity** - Better to have 500 good examples than 5000 bad ones

## Success Criteria

### Stage 1: 95%+ explicit instruction following
### Stage 2: 90%+ implicit instruction understanding  
### Stage 3: 85%+ appropriate generation
### Stage 4: 80%+ accurate evaluation
### Stage 5: 80%+ meaningful improvement
### Stage 6: Improved safety + maintained capability
