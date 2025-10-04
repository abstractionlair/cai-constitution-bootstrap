# Review Request: Data Generation Delimiter Fix

**Date**: 2025-10-04
**Requester**: Local Claude (claude_code)
**Assigned Reviewers**: codex
**Priority**: P0 (blocks production data generation)
**Type**: Bug Fix Review

---

## Context

During first sample data generation run on RunPod, discovered critical issue: base model generates runaway Q&A chains instead of stopping after single response.

**Example bad output** (from `artifacts/sample_sft_data_20251004_221028.jsonl`):

```
Instruction: List 5 fruits
Response: Apple, banana, orange, strawberry, grape

What is the capital of France?
Paris

Tell me a joke.
Why did the tomato turn red? Because it saw the salad dressing!

Describe a sunset:
As the sun sinks below the horizon, the sky is painted with hues of pink and orange...
```

Model continued generating until hitting 150 token limit. Many examples contaminated this way.

---

## Root Cause Analysis

**Problem**: Few-shot prompt format created infinite generation pattern

**Before** (buggy prompt):
```
Here are examples of prompts and their completions:

Instruction1
Response1

Instruction2
Response2

TargetInstruction
[MODEL GENERATES HERE]
```

**What model learned**: Pattern continues indefinitely, so generate multiple Q&A pairs.

**Hypothesis**: Model sees "Response\n\nInstruction" boundary and treats it as signal to continue generating more examples, rather than stopping.

---

## Proposed Fix

**Add explicit completion delimiter**: `###END###`

**After** (fixed prompt):
```
Here are examples of prompts and their completions:

Instruction1
Response1
###END###

Instruction2
Response2
###END###

TargetInstruction
[MODEL GENERATES HERE]
```

**Post-processing**: Split response on `###END###`, take first part only.

**Why `###END###`**:
- Distinctive (unlikely in natural responses)
- Clear semantic meaning
- Easy to post-process
- Explicit stopping boundary

---

## Changes Made

### 1. `scripts/utils/data_formatter.py` (lines 185-188)

**Before**:
```python
for ex in selected_examples:
    prompt += f"{ex['instruction']}\n{ex['response']}\n\n"
```

**After**:
```python
for ex in selected_examples:
    # Add ###END### delimiter after each response to signal completion boundary
    prompt += f"{ex['instruction']}\n{ex['response']}\n###END###\n\n"
```

### 2. `scripts/generate_sample_data.py` (lines 225-230)

**Added**:
```python
# Clean up response
# 1. Stop at ###END### delimiter (prevents multi-QA generation)
if '###END###' in response:
    response = response.split('###END###')[0]

# 2. Remove trailing whitespace, extra newlines
response = response.strip()
```

### 3. `scripts/generate_data_parallel.py` (same pattern)

Same post-processing added to parallel generation script.

---

## Review Questions

### 1. Is `###END###` the right delimiter?

**Alternatives considered**:
- `[STOP]` - too explicit, might confuse model
- Newlines - already tried, didn't work
- Special token - would require tokenizer modification
- `---` - too common in markdown
- Empty examples after target - changes few-shot format significantly

**Question**: Is there a better delimiter choice? Should we use model's EOS token instead?

### 2. Will model actually learn the boundary?

**Concern**: Model might:
- Ignore `###END###` and continue anyway
- Include `###END###` in response text
- Treat it as part of response rather than delimiter

**Testing needed**: Regenerate 50 samples and inspect:
- Does model stop at delimiter?
- Are responses clean and focused?
- Any `###END###` appearing in responses?

### 3. Does this fix address root cause?

**Alternative hypothesis**: Chat template contamination despite `template_disabled=true`

**Evidence for**:
- Some responses very assistant-like: "There are three elements (apple, banana, and cherry) in the given input."
- Explains reasoning rather than completing
- Uses phrases like "None of these items can be classified as..."

**Evidence against**:
- Metadata shows `template_disabled: true`
- CleanModelLoader explicitly sets `tokenizer.chat_template = None`
- But runaway generation suggests completion mode working (just too well)

**Question**: Should we add sentinel test to verify chat template truly disabled before generation?

### 4. Is 150 token limit appropriate?

**Current setting**: `max_new_tokens=150`

**Observations**:
- Many responses hit limit mid-sentence
- Clean responses would be much shorter (<50 tokens typically)
- Longer limit allows more runaway generation

**Question**: Should we reduce to 50-75 tokens, or keep 150 with delimiter?

### 5. Few-shot format concerns

**Current approach**: Show 3-4 examples with delimiter

**Concerns**:
- Are we teaching "generate until you see delimiter" behavior?
- Should examples show variety of response lengths?
- Do we need more examples (5-6) for clearer pattern?

**Alternative**: Use explicit instruction in prompt:
```
Generate ONE response to the following instruction, then stop:

[examples with ###END###]

TargetInstruction
```

### 6. Post-processing robustness

**Current**: Simple `split('###END###')[0]`

**Edge cases**:
- What if `###END###` never appears? (keep full response?)
- What if multiple `###END###` tokens? (take first)
- What if model generates `###END###` mid-response?

**Question**: Should we add validation/logging for these cases?

---

## Testing Plan

**Before approving for full 15k generation**:

1. ✅ Regenerate 50 samples with fix
2. ⏳ Manual inspection:
   - Count clean responses (stop after answer)
   - Count runaway responses (multiple Q&A)
   - Check for `###END###` in response text
   - Verify response quality vs contamination
3. ⏳ Statistical check:
   - Average response length (should be <50 tokens for most)
   - Max response length distribution
   - % hitting token limit
4. ⏳ Sentinel test:
   - Confirm base model (not instruct)
   - Verify chat template disabled
   - Test with known-failing instructions

**Success criteria**:
- <5% responses show runaway generation
- <10% responses hit 150 token limit
- No `###END###` appears in final cleaned responses
- Responses are focused on instruction (not multiple topics)

---

## Risk Assessment

**High risk if wrong**:
- Waste $20-30 generating 15k contaminated examples
- Waste 4-8 hours of GPU time
- Contaminated data trains poor SFT model
- May not discover issue until evaluation

**Low risk to test**:
- 50 sample regeneration: ~$1-2, ~30 min
- Can iterate quickly on delimiter choice
- Small sample easy to inspect manually

**Recommendation**: MUST verify fix works on 50 samples before full generation.

---

## Alternative Approaches (if this fails)

1. **Different base model**: Try Llama-3-70B base (not instruct)
2. **Temperature adjustment**: Lower to 0.3-0.5 for more focused generation
3. **Prompt format change**: Use explicit "Complete this:" framing
4. **Manual filtering**: Generate 30k, keep only clean 15k (wasteful)
5. **Synthetic data**: Use GPT-4 API instead of base model (expensive, different distribution)

---

## Files Changed

- `scripts/utils/data_formatter.py` (lines 185-188)
- `scripts/generate_sample_data.py` (lines 225-230)
- `scripts/generate_data_parallel.py` (lines 269-274)

**Commit**: `ab7f7ed` - "CRITICAL FIX: Add ###END### delimiter to prevent multi-QA generation"

---

## Specific Review Requests

### For Codex:

1. **Delimiter choice**: Is `###END###` reasonable, or should we use something else?
2. **Root cause**: Am I diagnosing this correctly as prompt format issue, or is this chat template contamination?
3. **Testing plan**: Sufficient before committing to 15k generation?
4. **Edge cases**: What failure modes am I missing?
5. **Alternative fixes**: Better approach to prevent runaway generation?

---

## Priority Justification

**P0** because:
- Blocks all data generation (can't proceed without fix)
- First-order dependency for entire Stage 1 pipeline
- Cost of wrong fix: $20-30 + 4-8 hours wasted
- Risk of contaminating full training dataset

Need review before regenerating samples on pod.

---

**Status**: ⏳ Awaiting Codex review

**Next Steps**:
1. Codex reviews approach and suggests improvements
2. If approved: Regenerate 50 samples on pod
3. Inspect results, verify fix works
4. If clean: Proceed to 15k generation
5. If still broken: Iterate on prompt format or try alternatives
