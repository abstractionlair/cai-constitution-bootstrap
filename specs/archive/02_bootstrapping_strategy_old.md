# Specification: CAI Progressive Bootstrapping Pipeline

## Critical Concept: Sequential Bootstrapping
This is NOT just testing infrastructure. Each stage produces a model that is functionally better at the task, which we then use to generate training data for the next stage.

## The Bootstrapping Sequence

### Stage 0: Single-Task Model (Foundation)
**Goal**: Create a model that can reliably follow ONE specific instruction
- **Training Data**: 100-500 examples of ONE task (e.g., "Summarize this text")
- **Method**: Generate variations, critique, revise, DPO train
- **Output**: Model that can reliably do ONE thing well
- **Success Metric**: 90%+ success rate on the chosen task
- **Why**: We need a reliable base to build on

### Stage 1: Few-Task Model (2-3 tasks)
**Goal**: Expand to handle 2-3 different instruction types
- **Uses**: Stage 0 model to help generate data
- **Training Data**: 200-500 examples each of 2-3 tasks
- **Output**: Model that can switch between a few tasks
- **Success Metric**: 85%+ success on each task type
- **Why**: Learn to distinguish between instruction types

### Stage 2: Multi-Task Model (10+ tasks)
**Goal**: General instruction following
- **Uses**: Stage 1 model for data generation
- **Training Data**: 100+ examples each of 10+ task types
- **Output**: Model with broad instruction-following ability
- **Success Metric**: 80%+ average across all tasks
- **Why**: Build general capability

### Stage 3: Constitutional Model
**Goal**: Add constitutional awareness
- **Uses**: Stage 2 model as the base
- **Training Data**: 1000+ examples with critique/revision
- **Output**: Constitutionally-aligned model
- **Success Metric**: Improved safety scores, maintained capability

## Concrete Implementation Plan

### Stage 0: Single Task Focus (3-5 hours)
```python
# Pick ONE task, e.g., "Answer this factual question"
task_type = "factual_qa"

# Generate 500 examples of JUST this task
examples = []
for i in range(500):
    question = generate_factual_question()  
    answer = model.generate(question)
    critique = model.critique(answer, principle)
    revised = model.revise(answer, critique)
    examples.append({
        "prompt": question,
        "chosen": revised,
        "rejected": answer
    })

# Train intensively on this ONE task
# This model becomes our "factual QA expert"
```

**Expected Result**: A model that can reliably answer factual questions

### Stage 1: Add 2-3 More Tasks (5-8 hours)
```python
# Now we have a good factual QA model
# Add: "Summarize this text" and "Explain this concept"
task_types = ["factual_qa", "summarization", "explanation"]

# Use Stage 0 model to help generate better examples
# It's already good at one thing, now we're adding more
```

**Expected Result**: A model that can handle 3 distinct instruction types

### Stage 2: Broaden to Many Tasks (8-10 hours)
```python
task_types = [
    "factual_qa", "summarization", "explanation",
    "translation", "creative_writing", "code_generation",
    "math_problems", "advice", "analysis", "comparison"
]

# Stage 1 model helps generate training data
# It can already handle multiple instruction types
```

**Expected Result**: General instruction-following capability

### Stage 3: Add Constitutional Layer (10+ hours)
```python
# Now we have a generally capable model
# Add constitutional critique and revision
# This is where the full CAI pipeline comes in
```

## Why This Changes Everything

### NOT This:
- Test with 1 example ✗
- Test with 10 examples ✗
- Test with 100 examples ✗

### But This:
- Build a single-task expert ✓
- Expand to few-task model ✓
- Generalize to many tasks ✓
- Add constitutional alignment ✓

Each stage DEPENDS on the previous stage working well enough to help generate the next stage's training data.

## Memory and Quantization Strategy

### For Training:
- **Stage 0-1**: 4-bit QLoRA is fine (simple tasks)
- **Stage 2-3**: Consider 8-bit for better quality
- **Always**: Keep LoRA adapters in 16-bit

### For Generation:
- **During data creation**: Use 8-bit or 16-bit for best quality
- **We have 80GB**: No need to compress during inference

## Realistic Timeline

### Day 1: Stage 0
- Pick the first task (e.g., factual QA)
- Generate 500 examples
- Train model
- Validate it works
- **Cost**: ~$8-10

### Day 2: Stage 1
- Add 2-3 more tasks
- Use Stage 0 model to help
- Generate 1000+ examples
- Train multi-task model
- **Cost**: ~$15-20

### Day 3-4: Stage 2-3
- Expand to full instruction following
- Add constitutional alignment
- **Cost**: ~$30-50

**Total Budget**: ~$50-80 for complete pipeline

## Critical Success Factors

1. **Stage 0 must work well** - If the single-task model isn't reliable, everything built on it will fail

2. **Progressive complexity** - Don't jump to general instruction following; build up gradually

3. **Each model helps create the next** - This is true bootstrapping, not just testing

4. **Quality over quantity** - Better to have 500 good examples than 5000 mediocre ones

## What We're Really Testing

**Hypothesis**: Can we bootstrap from a base model to a constitutionally-aligned model through progressive self-improvement?

**Not**: Can we run a CAI pipeline?

**But**: Can each stage's model effectively contribute to creating its successor?

## Next Step

Start with Stage 0: Pick ONE task type and make the model really good at it. Suggestions:
- Factual question answering
- Text summarization
- Simple explanations

Which would you prefer to start with?
