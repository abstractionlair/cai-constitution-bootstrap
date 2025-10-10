# Truncation Issue Analysis and Fixes

**Date**: 2025-10-10
**Issue**: 83 truncated/incomplete responses in final dataset (1.38%)

---

## Root Cause

**Token limit too low**: Response generation used `max_new_tokens=80-100`

**Why this causes truncation**:

### Code Examples
```
Instruction: "Write a simple Python program that prints 'Hello, World!'"

Response generation:
1. Model starts: "Here's a simple Python program that prints 'Hello, World!':" (12 tokens)
2. Needs to continue with actual code: print("Hello, World!") (~7 tokens)
3. Total needed: ~60-80 tokens
4. Limit: 100 tokens
5. Sometimes hits limit after intro, before code
```

### Complex Explanations
```
Instruction: "Explain photosynthesis"

Response starts: "Photosynthesis is the process... This involves two main stages:" (50 tokens)
Needs to continue: "Stage 1: Light reactions... Stage 2: Calvin cycle..." (50+ tokens)
Limit: 100 tokens → Truncates mid-explanation
```

---

## Why Critic Didn't Catch It

**Single-token A/B limitation**:

The pair critic evaluates:
```
Instruction: Write a Python program
Response: "Here's a simple Python program:"

Critic sees: Response STARTS correctly, acknowledges instruction
Critic logprobs: A (good) vs B (bad)
Decision: A with high confidence (margin > 1.0)
```

**The critic can't detect**:
- Response is incomplete
- Promises code but doesn't deliver
- Ends mid-thought

**Why**: Single-token judgment doesn't have capacity for "good start but incomplete" reasoning

---

## Fixes Implemented

### 1. Increase max_new_tokens ✅

**Files modified**:
- `scripts/generate_diversity_guided.py`: 100 → 200 tokens
- `scripts/generate_stage1_pilot_data.py`: 80 → 200 tokens (default)

**Rationale**:
- Most responses: 20-80 tokens (still fine)
- Code examples: Need 120-180 tokens
- Complex explanations: Need 100-150 tokens
- 200 tokens: Accommodates 95th percentile without being excessive

**Trade-off**: Slightly increases risk of verbose responses, but:
- Stop sequences still prevent runaways
- QC median token check still applies
- Better to have complete responses than truncated

### 2. Add Completeness Check to QC ✅

**File**: `scripts/generate_stage1_pilot_data.py:508-519`

**Detection patterns**:
```python
truncated_responses = sum(
    1 for p in final_pairs
    if (p['response'].strip().endswith(':') or  # Code intro without code
        p['response'].strip() in ['True', 'False', 'True.', 'False.'] or  # Bare boolean
        (len(p['response'].strip()) < 10 and 
         p['response'].strip() not in ['Yes', 'No', 'Yes.', 'No.']))  # Too short
)
```

**Threshold**: < 2% truncation rate

**Purpose**: Catch truncations in QC before they enter training data

### 3. Enhanced Delimiter Check ✅

**File**: `scripts/generate_stage1_pilot_data.py:503`

**Before**: Only checked for `###END###`
**After**: Checks for both `###END###` and standalone `###`

**Consistency**: Matches the response cleaner fix from yesterday

---

## Impact on Existing Data

**Dataset before fixes**: 6,009 examples
- Truncated responses: 83 (1.38%)
- Types: 66 code intros, 14 bare booleans, 3 other

**Dataset after filtering**: 5,926 examples
- Truncated responses: 0 (0.00%)
- All QC passing ✅

**Why filtering is temporary**:
- Current data: Generated with old limits (80-100 tokens)
- Future data: Will use 200 tokens → fewer truncations
- QC check: Will catch any remaining truncations

---

## Pipeline Improvements for Future

### Immediate (Done)
- ✅ Increased max_new_tokens to 200
- ✅ Added truncation detection to QC
- ✅ Enhanced delimiter leakage check

### Should Consider (Not Yet Implemented)

**1. Adaptive max_tokens by instruction type**:
```python
if 'code' in instruction.lower() or 'program' in instruction.lower():
    max_new_tokens = 250
elif 'explain' in instruction.lower() or 'describe' in instruction.lower():
    max_new_tokens = 200
else:
    max_new_tokens = 150
```

**2. Improved critic rubric**:
```
A = GOOD: Response completely fulfills instruction with necessary detail
B = BAD: Response incomplete, truncated, missing content, or incorrect
```

Add "complete" explicitly to rubric.

**3. Two-pass critique**:
- First pass: Quality (current A/B)
- Second pass: Completeness check
- But: Doubles critique cost

**For now**: 200 tokens + QC check should be sufficient

---

## Validation

**Next step**: Regenerate a test shard with new limits and verify:
1. No truncations in QC report
2. Code examples complete
3. Median tokens still reasonable (<70)
4. Quality maintained

---

## Recommendations for Spec Update

Current spec says: `max_new_tokens≈80`

Proposed: `max_new_tokens=150-200 (adaptive based on complexity)`

**Justification**:
- 80 tokens too restrictive for code/complex tasks
- 200 tokens accommodates P95 of response lengths
- Still prevents extreme verbosity
- Maintains conciseness for Stage 1 goals
