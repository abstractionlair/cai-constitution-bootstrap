# Base Model Capability Assessment

## Critical First Step: Test What We're Starting With

### The Question: How much can Qwen2.5-32B base actually do?

We need to establish a clear baseline BEFORE any training. This tells us:
1. What capabilities exist already
2. What we're actually teaching
3. Whether our bootstrapping works

## Test Protocol

### Step 1: Load TRUE Base Model
```python
from transformers import AutoModelForCausalLM, AutoTokenizer

# Make sure we load BASE not Instruct
model = AutoModelForCausalLM.from_pretrained(
    "Qwen/Qwen2.5-32B",  # NOT Qwen2.5-32B-Instruct
    device_map="auto",
    torch_dtype=torch.bfloat16
)
tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-32B")
```

### Step 2: Test Different Prompt Formats

```python
test_prompts = [
    # Raw completion (should work)
    "The capital of France is",
    
    # Question (might not trigger answer)
    "What is the capital of France?",
    
    # Explicit instruction (might not understand)
    "Answer this question: What is the capital of France?",
    
    # Command format (likely to fail)
    "Tell me the capital of France.",
    
    # Chat format (probably won't work)
    "Human: What is the capital of France?\nAssistant:",
]

for prompt in test_prompts:
    response = generate(model, tokenizer, prompt)
    print(f"Prompt: {prompt}")
    print(f"Response: {response[:100]}")
    print("-" * 50)
```

## Expected Results

### If Gemini is Right (True Base Model):
```
"The capital of France is" → "Paris, and it has been..."  ✓ (completion works)
"What is the capital of France?" → "What is the capital of Germany? What is..." ✗ (continues questions)
"Answer this question:" → "Answer this question: Is it possible to..." ✗ (continues prompt)
"Tell me the capital" → "Tell me the capital requirements for..." ✗ (wrong continuation)
```

### If Some Instruction Training Exists:
```
"The capital of France is" → "Paris"  ✓
"What is the capital of France?" → "The capital of France is Paris"  ✓
"Answer this question:" → "Paris"  ✓
"Tell me the capital" → "The capital of France is Paris"  ✓
```

## Baseline Metrics

Run our Stage 1 evaluation suite on the BASE model:

```python
def assess_base_capabilities():
    results = {
        'explicit_instructions': 0,  # "Answer this:"
        'questions': 0,              # "What is X?"
        'completions': 0,            # "The X is..."
        'commands': 0,               # "Tell me X"
    }
    
    for category, prompts in test_sets.items():
        for prompt in prompts:
            response = model.generate(prompt)
            if is_appropriate_response(response, prompt):
                results[category] += 1
        
        results[category] = results[category] / len(prompts) * 100
    
    return results
```

## Likely Reality

My hypothesis:
- **Completions**: 80-90% (base models are good at this)
- **Questions**: 20-40% (might not recognize as needing answers)
- **Explicit Instructions**: 10-30% (unlikely to understand format)
- **Commands**: 10-30% (similar to instructions)

## What This Means for Our Project

### If Base Model is Truly "Raw":
- Stage 1 becomes MORE important
- We're teaching instruction-following from near-zero
- Success would be more impressive
- Bootstrapping is a bigger achievement

### If Some Capability Exists:
- We're improving consistency
- Teaching our specific formats
- Still valuable but different framing

## Updated Stage 1 Goals

Instead of assuming capability, we:
1. **Measure exactly** what base model can do
2. **Document the delta** we achieve
3. **Frame appropriately** in publication

### Success Metrics (Revised)
- Baseline: Whatever we measure (might be 10-30%)
- Target: 95%+ for explicit instructions
- Improvement: The delta is what matters

## Implementation Priority

**FIRST TASK for Claude Code**:
1. Load the TRUE base model (not Instruct)
2. Run baseline tests
3. Report what capabilities exist
4. THEN proceed with Stage 1 training

This gives us the real story of what we're accomplishing!
