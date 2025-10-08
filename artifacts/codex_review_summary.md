# Codex Gate Review: Pilot QC Decision

**Date**: 2025-10-07
**Review File**: `reviews/autonomous/20251007_175412_pilot_qc_gate.txt`
**Reviewer**: Codex (gpt-5-codex, high reasoning)
**Decision**: ITERATE

---

## Pilot Results Summary

**Generated**: 43 examples (target: 100)

**QC Failures**:
- Runaway rate: 20.9% (threshold: <5%) ⚠️
- Token limit rate: 52.2% (threshold: <10%) ⚠️

**QC Passes**:
- Delimiter leakage: 0 ✅
- Instruction acceptance: 77.6% ✅
- Pair acceptance: 93.5% ✅

**Root Causes**:
1. Responses too long/rambling (runaway)
2. Hitting max_new_tokens=80 frequently
3. Low initial instruction generation (39.7% acceptance)

---

## Codex Recommendation

### Decision: ITERATE

**Priority 1**: Retune generation hyperparameters
- Lower temperature to ≤0.3 (currently 0.4 for responses)
- Tighter top_p/repetition penalty
- Add stop strings for self-termination

**Priority 2**: Re-run pilot with augmented cleanup
- Inspect runaway/token-limit metrics
- Verify improvements

**Priority 3**: Raise instruction multiplier once QC clears
- Generate 2× instructions upfront to hit 100-example target
- Only after rates pass thresholds

**Reasoning**: Both failures trace to overly long generations, not unclear root causes. Tightening sampling parameters should bring base model back into expected completion regime.

---

## Proposed Parameter Changes

### Current Parameters (Pilot 1)
```python
# Response generation
temperature=0.4
top_p=0.9
repetition_penalty=1.1
max_new_tokens=80

# Instruction generation
temperature=0.7
top_p=0.9
repetition_penalty=1.1
```

### Iteration 1 Parameters (Codex-recommended)
```python
# Response generation
temperature=0.3  # Lower from 0.4
top_p=0.85  # Tighter from 0.9
repetition_penalty=1.15  # Higher from 1.1
max_new_tokens=80  # Keep same initially
stop_strings=["\n\n", "Instruction:", "Question:", "Q:"]  # NEW

# Instruction generation
temperature=0.6  # Lower from 0.7
top_p=0.85  # Tighter from 0.9
repetition_penalty=1.15  # Higher from 1.1
```

### Iteration 2 Parameters (If still needed)
```python
# Response generation
temperature=0.25  # Even lower
max_new_tokens=100  # Increase if still hitting limit frequently

# Instruction generation
count_multiplier=2.0  # Generate 2× to compensate for filtering
```

---

## Implementation Plan

### Step 1: Update Script Parameters (10 minutes)
Modify `generate_stage1_pilot_data.py`:
- Add temperature/top_p/repetition_penalty params to methods
- Add stop_strings parameter to response generation
- Make configurable via command-line args

### Step 2: Run Iteration 1 (30-40 minutes)
```bash
python3 scripts/generate_stage1_pilot_data.py \
  --count 100 \
  --output artifacts/pilot_iteration1 \
  --seed 43 \
  --response-temperature 0.3 \
  --response-top-p 0.85 \
  --response-repetition-penalty 1.15 \
  --instruction-temperature 0.6 \
  --instruction-top-p 0.85 \
  --instruction-repetition-penalty 1.15
```

### Step 3: Check QC (5 minutes)
```bash
python3 -m json.tool artifacts/pilot_iteration1/qc_summary.json
```

**Gate criteria**:
- Runaway rate < 5%
- Token limit rate < 10%

If pass → Proceed to scale
If fail → Try Iteration 2 with even tighter params

### Step 4: Scale (If QC Passes)
Generate 15k examples with sharding

---

## Session Budget Check

**Used so far**:
- Pilot 1: ~40 minutes GPU time ≈ $2.00
- Codex review: ~$0.20

**Remaining for iterations**:
- Iteration 1: ~40 minutes ≈ $2.00
- Iteration 2 (if needed): ~40 minutes ≈ $2.00
- Scale to 15k: ~6 hours ≈ $18.00

**Total estimated**: ~$24.20 of $300 budget ✅

---

## Next Actions

1. ✅ Codex review complete
2. ⏳ Update script with configurable parameters
3. ⏳ Run Iteration 1 with tighter parameters
4. ⏳ Check QC results
5. ⏳ Proceed based on results

**Status**: Ready to iterate
