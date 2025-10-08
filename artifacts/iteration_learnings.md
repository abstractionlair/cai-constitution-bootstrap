# Iteration Learnings: Parameter Tuning for Base Model Generation

**Date**: 2025-10-07
**Context**: Tuning generation parameters for Stage 1 data generation
**Iterations**: 3 (pilot 1 + iteration 1 + iteration 2)

---

## Summary of Iterations

| Metric | Pilot 1 | Iteration 1 | Iteration 2 | Target |
|--------|---------|-------------|-------------|--------|
| Examples | 43 | 13 | ? | 100 |
| Runaway rate | 20.9% | 53.8% ↑↑ | ? | <5% |
| Token limit | 52.2% | 15.0% ↓ | ? | <10% |
| Inst acceptance | 77.6% | 64.6% ↓ | ? | ≥50% |
| Raw inst accept | 39.7% | 24.4% ↓↓ | ? | - |

### Parameters

| Parameter | Pilot 1 | Iteration 1 | Iteration 2 |
|-----------|---------|-------------|-------------|
| Inst temp | 0.7 | 0.6 ↓ | 0.7 (reverted) |
| Inst top_p | 0.9 | 0.85 ↓ | 0.9 (reverted) |
| Inst rep_pen | 1.1 | 1.15 ↑ | 1.1 (reverted) |
| Resp temp | 0.4 | 0.3 ↓ | 0.4 (reverted) |
| Resp top_p | 0.9 | 0.85 ↓ | 0.9 (reverted) |
| Resp rep_pen | 1.1 | 1.15 ↑ | 1.1 (reverted) |
| Max tokens | 80 | 80 | **100 ↑** |
| **Stop sequences** | ❌ None | ❌ None | ✅ Added |

---

## Key Learnings

### Learning 1: Tighter Sampling Made Things Worse

**Hypothesis**: Lower temperature → shorter, more focused responses
**Reality**: Lower temperature → low-entropy repetitive continuations

**Why it failed**:
- Low temperature (0.3) + low top_p (0.85) + high repetition penalty (1.15) = deterministic list continuations
- Base model generated repetitive numbered lists instead of diverse instructions
- These triggered runaway detection (long deterministic patterns)
- Instruction quality collapsed (24.4% acceptance vs 39.7%)

**Lesson**: Base model needs moderate temperature (0.4-0.7) for quality generation

### Learning 2: Critics React to Degraded Input

**Observation**: Critics worked correctly, but had worse input to judge
- Iteration 1 generated worse instructions (lower temps)
- Critics correctly rejected more (24.4% acceptance)
- Problem was upstream (generation), not downstream (critique)

**Lesson**: QC metrics reflect generation quality, not just critic strictness

### Learning 3: Stop Sequences vs Temperature

**Codex insight**: Stop runaway with explicit stop tokens, not temperature
- Temperature controls diversity/quality
- Stop sequences control when to terminate
- These are independent concerns

**Lesson**: Use stop sequences for runaway prevention, not temperature reduction

### Learning 4: max_new_tokens Is a Hard Limit

**Issue**: 52% of responses hit 80-token limit in pilot 1
**Solution**: Increase to 100 tokens (allows longer valid responses)
**Tradeoff**: Slightly more GPU time, but prevents truncation

**Lesson**: Set max_new_tokens above expected response length to avoid truncation

---

## Codex Reviews: Excellent Guidance

### Review 1 (After Pilot 1)
**Recommendation**: Tighten parameters (temp ≤0.3)
**Outcome**: ❌ Made things worse
**Learning**: Codex's first instinct wasn't perfect, but gave us data

### Review 2 (After Iteration 1)
**Recommendation**: Revert params, add stop sequences
**Reasoning**: Over-constrained sampling caused low-entropy continuations
**Outcome**: ✅ Clear diagnosis of root cause
**Learning**: Codex quickly identified the problem and course-corrected

**Total cost**: ~$0.40 for 2 reviews
**Value**: Prevented multiple wasted iterations

---

## Root Cause Analysis (Codex-validated)

**Why iteration 1 failed**:

1. **Low-entropy sampling** (temp 0.3, top_p 0.85, rep_pen 1.15):
   - Base model defaulted to deterministic continuations
   - Generated repetitive numbered lists
   - Collapsed instruction diversity

2. **Runaway detection triggered falsely**:
   - Long deterministic patterns flagged as "runaway"
   - Actually just repetitive continuations, not instruction-following failures
   - Heuristics designed for diverse responses, not repetitive patterns

3. **Upstream quality collapse**:
   - Instruction generation quality degraded (24.4% acceptance)
   - Fewer good instructions → fewer final pairs
   - Critics correctly rejected bad inputs

**Real solution**:
- Keep moderate temperature for quality
- Add stop sequences to prevent actual runaways
- Increase max_tokens to avoid truncation

---

## Iteration 2 Configuration (Codex-recommended)

### Parameters (Reverted to Pilot 1 + Adjustments)
```python
# Instruction generation
instruction_temperature = 0.7      # Reverted from 0.6
instruction_top_p = 0.9           # Reverted from 0.85
instruction_repetition_penalty = 1.1  # Reverted from 1.15

# Response generation
response_temperature = 0.4        # Reverted from 0.3
response_top_p = 0.9             # Reverted from 0.85
response_repetition_penalty = 1.1   # Reverted from 1.15
response_max_new_tokens = 100     # Increased from 80

# NEW: Stop sequences
stop_sequences = ["\nInstruction", "\nQ:", "\n###", "\nUser:", "\nResponse:"]
```

### Expected Improvements
1. ✅ Instruction acceptance back to ~40% (like pilot 1)
2. ✅ Stop sequences prevent runaway (target <5%)
3. ✅ max_tokens=100 reduces token limit hits (target <10%)
4. ✅ Overall: Should pass QC thresholds

### Smoke Test Plan (Codex-recommended)
Before full run, generate 20-30 examples and:
1. Inspect 10 flagged "runaway" samples
2. Check if stop sequences are firing
3. Verify cleaning heuristics aren't over-trimming
4. Confirm metrics normalize

---

## Next Steps

### Immediate (When Iteration 2 Completes)
1. Check QC results
2. If QC passes: Proceed to scale (15k)
3. If QC still fails: Implement smoke test audit (Option 6)

### If Iteration 2 Fails
- Audit cleaning heuristics (are we cutting good responses?)
- Enrich few-shot examples (Option 4)
- Request another Codex review

### If Iteration 2 Passes
- ✅ Proceed to scale generation (15k examples, sharded)
- Use iteration 2 parameters for scale
- Merge and validate

---

## Cost Tracking

**Iterations run**:
- Pilot 1: ~40 min GPU ≈ $2.00
- Iteration 1: ~30 min GPU ≈ $1.50
- Iteration 2: ~40 min GPU (est) ≈ $2.00

**Codex reviews**: 2 × ~$0.20 = $0.40

**Total used**: ~$5.90 of $300 budget
**Remaining**: $294.10
**Status**: ✅ Excellent - learning iterations are cheap

---

## Strategic Insights

### Value of Iteration
- Each iteration costs ~$1.50-2.00
- Each iteration provides data for better decisions
- Codex reviews (~$0.20) guide iterations efficiently
- **Total cost to find good parameters**: ~$6 (2% of budget)
- **Value**: Prevents training on bad data (would waste $20+)

### Autonomous Decision Quality
- First Codex recommendation wasn't perfect (made things worse)
- But second recommendation was excellent (root cause analysis)
- This is normal research iteration process
- Having Codex in the loop accelerates learning

### Base Model Characteristics
- Needs moderate temperature (0.4-0.7) for quality
- Can't be over-constrained or defaults to repetitive patterns
- Stop sequences are better than temperature for controlling length
- Few-shot prompting may be critical (worth enriching if needed)

---

**Status**: 🔄 Iteration 2 running with high confidence it will improve
**Next**: Analyze iteration 2 results when complete
