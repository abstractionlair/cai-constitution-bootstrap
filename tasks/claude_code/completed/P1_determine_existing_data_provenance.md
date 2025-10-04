# P1: Data Provenance Investigation - COMPLETED

**Assigned To**: claude_code
**Completed**: 2025-10-03
**Priority**: P1 (High)

## Investigation Summary

Investigated the provenance of existing training data (Sep 10-11) to determine if it's clean or contaminated.

---

## Findings

### Existing Data Files

| File | Size | Date | Fields | Count |
|------|------|------|--------|-------|
| data/stage1/train_instructions.jsonl | 7.7K | Sep 10 | id, instruction, instruction_type, pool, raw_partial, template | ~100 |
| artifacts/preference_pairs.jsonl | 110K | Sep 11 | id, instruction, chosen, rejected, critique, instruction_type | ~188 |
| artifacts/held_out_test_instructions_20250911_162708.jsonl | 18K | Sep 11 | instruction, instruction_type, topic, id, generated_for, seed | ~130 |

### Data Format Analysis

**train_instructions.jsonl** structure:
```json
{
  "id": "completion_4",
  "instruction": "2 + 2 equals",
  "instruction_type": "completion",
  "raw_partial": "2 + 2 equals",
  "template": "{partial}",
  "pool": "train"
}
```

**Key observations**:
1. ❌ No `response` field - this is instructions ONLY, not full SFT data
2. ❌ No generation script metadata (`script`, `generated_by`, `version` fields absent)
3. ❌ Has `template` and `raw_partial` fields suggesting older formatting approach
4. ✅ Has `pool` field (train/test) suggesting train/test split was done

**Expected format from clean script** (`generate_stage1_sft_data.py`):
```json
{
  "instruction": "...",
  "response": "...",
  "formatted_text": "...",
  "prompt": "...",
  "completion": "...",
  "instruction_type": "..."
}
```

### Script Timeline vs Data Timeline

| Script | Date | Has chat_template=None? | Output format |
|--------|------|------------------------|---------------|
| generate_stage1_data.py | Sep 10 | ❌ NO | Unknown (uses model_loader) |
| stage1_generate.py | Sep 11 | ❌ NO | Unknown |
| stage1_generate_robust.py | Sep 11 | ❌ NO | Unknown |
| **generate_stage1_sft_data.py** | **Sep 12** | **✅ YES** | **instruction+response+formatted_text** |

**Data files** (Sep 10-11) **predate clean script** (Sep 12)

### What We Don't Have

1. ❌ No generation logs found
2. ❌ No generation script metadata in data files
3. ❌ Sep 13 file mentioned in registry (`sft_training_data_20250913_005116.jsonl`) does NOT exist
4. ❌ No way to definitively prove which script generated the data

---

## Conclusions

### 1. Existing Data is Instruction-Only (Not Full SFT Data)

The `train_instructions.jsonl` file contains **instructions without responses**. This is NOT full SFT training data.

**What this means**:
- This data was intended to be fed to a model to GENERATE responses
- Not ready for training as-is
- Need to generate responses for each instruction

### 2. Data May Be Contaminated

**Evidence of potential contamination**:
- Data predates clean script (Sep 12) by 1-2 days
- All three earlier scripts (Sep 10-11) do NOT disable chat_template
- No verification that clean approach was used

**However**:
- Data format suggests it came from an instruction GENERATION script
- These scripts might not have loaded the model directly (they just generate instructions)
- Contamination would occur when GENERATING RESPONSES, not when generating instructions

### 3. Preference Pairs Also Questionable

`artifacts/preference_pairs.jsonl`:
- Date: Sep 11 (before clean script)
- Has full responses in `chosen`/`rejected` fields
- These responses WOULD be affected by chat template contamination
- Should regenerate these with clean script

### 4. Test Instructions May Be OK

`held_out_test_instructions_20250911_162708.jsonl`:
- Just instructions, no responses
- Has proper metadata (`generated_for`, `seed`)
- Contamination risk: LOW (it's just instructions)
- **Could potentially reuse** these if we verify format is compatible

---

## Recommendations

### Immediate Action: **Regenerate All Training Data**

**Reason**: Cannot verify existing data is clean; better to be certain.

### What to Generate

1. **SFT Training Data**:
   - Use `scripts/generate_stage1_sft_data.py` (verified clean, line 130)
   - Generate 5-10k examples (per POST_TRAINING_APPROACHES.md for 32B model)
   - This will generate both instructions AND responses cleanly

2. **Preference Pairs**:
   - Use existing preference pair generation scripts
   - Target 10-30k pairs (10k minimum for clear win)
   - Use BoN sampling, confidence filtering, hard negatives

3. **Test Instructions**:
   - **Option A**: Reuse `held_out_test_instructions_20250911_162708.jsonl` (130 instructions)
   - **Option B**: Regenerate with clean script for consistency
   - **Recommendation**: Option A is probably safe (just instructions, has proper metadata)

### Why Regenerate Rather Than Use Existing

**Pros of regenerating**:
- ✅ Guaranteed clean (no chat template contamination)
- ✅ Full SFT format (instruction + response + formatted)
- ✅ Proper scale (5-10k instead of ~100)
- ✅ Matches POST_TRAINING_APPROACHES.md recommendations
- ✅ Peace of mind for publication

**Cons**:
- ⏱️ Requires RunPod GPU time (~2-4 hours for data generation)
- 💰 Cost: ~$3-7 for data generation

**Verdict**: **Regeneration is worth it**. Cost is small compared to risk of training on contaminated data (~$20-25 wasted).

---

## Action Items for Next Steps

### Before RunPod Session

- [x] Investigate data provenance (THIS TASK)
- [ ] Write instruction-following eval
- [ ] Plan RunPod workflow

### RunPod Session Sequence

1. **Verification** (30 min, ~$1)
   - Run `test_base_model_ultra_clean.py`
   - Verify sentinel tests pass
   - Document baseline behavior

2. **Data Generation** (2-4 hours, ~$3-7)
   - Run `generate_stage1_sft_data.py` for 5-10k examples
   - Generate preference pairs with BoN sampling
   - Save all artifacts

3. **Evaluation** (1 hour, ~$2)
   - Run instruction-following eval on base model
   - Establish baseline performance
   - Document results

4. **Training** (if data looks good) (4-8 hours, ~$7-14)
   - SFT training
   - DPO training
   - Final evaluation

**Total estimated cost**: ~$13-24 (well within ~$25 Stage 1 budget)

---

## Files to Archive/Ignore

Since we're regenerating, mark these as superseded:
- `data/stage1/train_instructions.jsonl` - Incomplete, potentially contaminated
- `artifacts/preference_pairs.jsonl` - Potentially contaminated
- Can keep test instructions if needed

---

## Related Documents

- `/docs/VERIFICATION_STATUS.md` - Update with these findings
- `/docs/POST_TRAINING_APPROACHES.md` - Sample size guidance
- `/docs/BASE_MODEL_TRUTH.md` - Chat template contamination issue
- `/scripts/generate_stage1_sft_data.py` - Clean script to use
- `ROADMAP.md` - Update data generation plans

---

**Conclusion**: Existing data is incomplete (instructions only) and potentially contaminated (predates clean script). **Recommendation: Regenerate all training data with verified clean script on RunPod.**
