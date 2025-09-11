# Stage 0: Information & Explanation Task

## Task Definition
Train the model to handle ALL forms of information requests:
- Questions: "What is X?"
- Instructions: "Tell me about X"
- Commands: "Explain X"
- Queries: "How does X work?"
- Definitions: "Define X"

## Why This First?
1. **Foundation**: Everything builds on being informative
2. **Natural Variety**: Many ways to ask for the same information
3. **Clear Evaluation**: Information is correct or incorrect
4. **Easy Generation**: Can create hundreds of examples programmatically

## Example Training Data

### Input Variations (all seeking same information)
```
"What is photosynthesis?"
"Explain photosynthesis."
"Tell me about photosynthesis."
"How does photosynthesis work?"
"Define photosynthesis."
"Describe the process of photosynthesis."
"Can you explain photosynthesis?"
"I need information about photosynthesis."
```

### Expected Output Pattern
- Accurate information
- Appropriate detail level
- Clear explanation
- Responsive to the specific form (definition vs explanation)

## Generation Strategy

### 1. Topic Selection
```python
topics = [
    "scientific_concepts": ["photosynthesis", "gravity", "evolution", ...],
    "historical_events": ["World War II", "Renaissance", "Moon landing", ...],
    "technologies": ["internet", "blockchain", "machine learning", ...],
    "general_knowledge": ["capitals", "currencies", "languages", ...],
    # ... hundreds of topics
]
```

### 2. Question Form Variation
```python
question_templates = [
    "What is {topic}?",
    "Explain {topic}.",
    "Tell me about {topic}.",
    "How does {topic} work?",
    "Define {topic}.",
    "What do you know about {topic}?",
    "Describe {topic}.",
    "Can you explain {topic}?",
    "Give me information about {topic}.",
    # ... many variations
]
```

### 3. Constitutional Principles for Stage 0
Focus on information quality:
- Accuracy: Information must be correct
- Clarity: Explanations must be understandable
- Completeness: Answer the actual question asked
- Appropriateness: Right level of detail

## Training Process

### Data Generation (4-6 hours)
1. Generate 500-1000 information requests
2. Model provides initial answers
3. Critique each answer:
   - Is it accurate?
   - Is it clear?
   - Does it answer the question?
   - Is the detail level appropriate?
4. Generate revised answers
5. Create preference pairs

### DPO Training (2-3 hours)
- Train on preference pairs
- Focus on information quality
- Validate on held-out test set

### Success Metrics
- **Accuracy**: 95%+ factually correct
- **Relevance**: 90%+ answers the actual question
- **Clarity**: Human-readable and understandable
- **Consistency**: Similar quality across question forms

## Output
A model that reliably provides accurate information regardless of how the request is phrased. This becomes our foundation for Stage 1.

## Next Stage Preview
Stage 1 will add text transformation tasks (summarization, translation, etc.) using this information-capable model to help generate training data.
