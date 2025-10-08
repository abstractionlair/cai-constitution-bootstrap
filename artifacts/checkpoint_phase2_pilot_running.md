# Checkpoint: Phase 2 - Pilot Execution Running

**Timestamp**: 2025-10-07T17:30:XX UTC
**Phase**: Phase 2 - Pilot Execution (100 examples)
**Status**: 🔄 In Progress

---

## Current State

### Pilot Generation Running

**Command**:
```bash
python3 scripts/generate_stage1_pilot_data.py \
  --count 100 \
  --output artifacts/pilot \
  --seed 42
```

**Background PID**: Tracked in system

**Expected Duration**: 30-60 minutes (based on 10-example test taking ~5 minutes)

**Log file**: `artifacts/pilot_run.log`

**Output directory**: `artifacts/pilot/`

### Test Pilot Results (10 examples)

Successfully completed small test pilot:
- ✅ Generated 9/10 examples (90% final yield)
- ✅ Instruction acceptance: 81.8%
- ✅ Pair acceptance: 100%
- ✅ Median tokens: 32 (well under 40 threshold)
- ✅ Runaway rate: 0%
- ✅ Delimiter leakage: 0
- ⚠️ Token limit rate: 10.0% (exactly at threshold)
- ⚠️ QC Status: FAIL (due to token limit rate = 10%, need < 10%)

**Data Quality Sample**:
```json
{
  "instruction": "Name two renewable energy sources.",
  "response": "Two renewable energy sources are solar power and wind power.",
  "pair_critique": {
    "is_good": true,
    "predicted_label": "A",
    "logp_a": -0.089,
    "logp_b": -3.719,
    "margin": 3.630
  }
}
```

Quality looks excellent - just need to avoid token limit boundary.

---

## What to Do When Pilot Completes

### 1. Check Completion Status

```bash
# Check if process finished
tail -50 artifacts/pilot_run.log

# Look for completion message
grep "PILOT GENERATION COMPLETE" artifacts/pilot_run.log
```

### 2. Inspect QC Results

```bash
# Check threshold status
python3 -c "import json; qc = json.load(open('artifacts/pilot/qc_summary.json')); print('QC Passed:', qc['thresholds_passed']); print('Failed Reasons:', qc['failed_reasons'])"

# Inspect metrics
python3 -m json.tool artifacts/pilot/qc_summary.json | head -100
```

### 3. Request Codex Review (Gate Decision)

**If QC looks reasonable** (even if minor threshold fails):

```bash
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

codex exec --full-auto \
  -m "gpt-5-codex" \
  -c 'model_reasoning_effort="high"' \
  -o "reviews/autonomous/${TIMESTAMP}_pilot_qc_gate.txt" \
"You are reviewing a gate decision for Constitutional AI Bootstrap Stage 1 Data Generation.

CONTEXT:
Completed pilot generation of 100 instruction-following examples.
Full QC results in artifacts/pilot/qc_summary.json

PILOT QC SUMMARY:
$(cat artifacts/pilot/qc_summary.json)

SPEC THRESHOLDS (from stage1_data_generation_spec.md):
- Runaway rate: < 5%
- Token limit hits: < 10%
- Delimiter leakage: 0
- Median tokens: < 40
- Critic acceptance: ≥ 50%

QUESTION: Should I proceed to scale to 15k examples?

Consider:
1. Are threshold failures minor/fixable?
2. Is data quality good despite threshold failures?
3. Would scaling be productive or should I iterate on pilot?

REQUIRED RESPONSE FORMAT:
Decision: SCALE / ITERATE / INVESTIGATE
Reasoning: 2-3 sentences justifying decision
Concerns: Any risks or conditions to watch during scale
Action Items: What I should do next

Response in under 500 words."
```

**Expected Codex review time**: 5-10 minutes

### 4. Act on Codex Decision

**If SCALE**:
- Proceed to implement scale script (15k examples)
- Use sharding across seeds for diversity
- Merge shards and recompute QC

**If ITERATE**:
- Adjust parameters based on Codex feedback
- Retry pilot (max 2 retries per spec)
- Common adjustments:
  - Increase max_new_tokens to reduce token limit hits
  - Adjust temperature for better quality
  - Tune confidence_threshold

**If INVESTIGATE**:
- Manual inspection of generated examples
- Check for patterns in failures
- Report findings and request further guidance

---

## Files/Artifacts Created So Far

### Core Implementation (Phase 1)
- `scripts/utils/clean_model_loader.py` ✅
- `scripts/utils/completion_prompts.py` ✅
- `scripts/utils/instruction_critic.py` ✅
- `scripts/utils/provenance_helper.py` ✅
- `scripts/utils/__init__.py` ✅
- `scripts/generate_stage1_pilot_data.py` ✅

### Test Pilot (Phase 2)
- `artifacts/pilot_test/pilot_data.jsonl` (9 examples) ✅
- `artifacts/pilot_test/qc_summary.json` ✅
- `artifacts/pilot_test/session_manifest.json` ✅

### Full Pilot (Phase 2 - Running)
- `artifacts/pilot/pilot_data.jsonl` (🔄 generating)
- `artifacts/pilot/qc_summary.json` (🔄 generating)
- `artifacts/pilot/session_manifest.json` (🔄 generating)
- `artifacts/pilot_run.log` (🔄 logging)

### Documentation
- `docs/CODEX_AUTONOMOUS_REVIEW_GUIDE.md` ✅
- `docs/SESSION_20251007_SETUP_AND_REVIEW_PATTERNS.md` ✅
- `artifacts/checkpoint_phase1_complete.md` ✅
- `artifacts/checkpoint_phase2_pilot_running.md` (this file) ✅

---

## Progress Monitoring

To check pilot progress while waiting:

```bash
# Watch log tail (updates every 10 seconds)
watch -n 10 'tail -20 artifacts/pilot_run.log'

# Or manual checks
tail -50 artifacts/pilot_run.log

# Count generated examples so far
ls -l artifacts/pilot/ 2>/dev/null
```

**Progress indicators in log**:
- "PHASE 1: INSTRUCTION GENERATION" - Generating instructions
- "PHASE 2: RESPONSE GENERATION" - Generating responses
- "PHASE 3: PAIR FILTERING" - Filtering pairs
- "PHASE 4: QC METRICS" - Computing metrics
- "PHASE 5: SAVING ARTIFACTS" - Writing files
- "PILOT GENERATION COMPLETE" - Done!

---

## Next Session Recovery

If context is lost or session ends before pilot completes:

1. **Check pilot status**:
   ```bash
   ps aux | grep generate_stage1_pilot_data.py
   ```

2. **If still running**: Wait for completion or check log

3. **If completed**: Resume at "What to Do When Pilot Completes" above

4. **If failed**: Check logs for errors, debug, and retry

All state is in files - no context needed to resume.

---

**Status**: 🔄 Pilot running, expected completion in ~30-60 minutes
**Next Action**: Monitor log, then request Codex gate review
