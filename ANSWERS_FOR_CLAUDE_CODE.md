# Answers to Claude Code's Questions

## 1. Evaluation: Automated with Clear Metrics

See `specs/stage_1_evaluation.md` for details.

**Approach**: Automated evaluation with objective criteria
- Check if response contains expected elements
- Verify format compliance (single sentence when asked, completion when requested)
- Test 100 diverse examples
- Human spot-check 20 random samples

**Example**:
```python
# For "Answer this question: What is X?"
success = (
    len(response) > 0 and
    not response.startswith("I don't") and
    contains_relevant_content(response, expected_terms)
)
```

## 2. Pre-training Contamination: Expected and Handled

**Reality**: Qwen-2.5-32B base probably has ~60-80% instruction following already

**Our Approach**:
1. Measure baseline performance BEFORE Stage 1
2. Show improvement (e.g., 70% → 95%)
3. Focus on CONSISTENCY, not just capability
4. Build our specific format preferences

**What we're really doing**: Making it reliably follow OUR format, not teaching from scratch

## 3. Checkpoints: LoRA Adapters, Not Full Weights

See `specs/checkpoint_strategy.md` for details.

**Strategy**:
- Save LoRA adapters after each stage (~500MB)
- Merge LoRA for high-quality generation between stages
- Don't save full weights (65GB each) unless final model

**Workflow**:
```python
# Train Stage N
train_with_lora(model)
save_lora_adapters(f"stage_{n}_lora/")  # Small!

# Generate for Stage N+1
merged = merge_lora_and_base(base_model, f"stage_{n}_lora/")
merged_16bit = merged.to(torch.float16)  # Better generation
generate_training_data(merged_16bit)
```

**Benefits**:
- Storage: 3GB total vs 390GB for full weights
- Easy to download/version
- Can recreate any stage by merging

## Summary for Implementation

1. **Start with baseline test** - See what the base model can already do
2. **Use automated evaluation** - Objective, reproducible metrics
3. **Save LoRA only** - Merge when needed for generation
4. **Track relative improvement** - Not absolute performance

Ready to implement Stage 1 with these clarifications!
