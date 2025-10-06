# P1: Determine Existing Data Provenance
**Assigned To**: claude_code

**Priority**: P1 (High - affects whether we need to regenerate data)
**Estimated Time**: 15-30 minutes

## Issue Description

We have existing training data from Sep 10-11, but it predates our verified clean script (Sep 12). We need to determine:

1. Which script(s) generated the existing data
2. Whether that data is contaminated (chat template leakage)
3. Whether we need to regenerate before training

## Existing Data Files

| File | Size | Date | Purpose |
|------|------|------|---------|
| data/stage1/train_instructions.jsonl | 7.7K | Sep 10 | SFT training data |
| artifacts/preference_pairs.jsonl | 110K | Sep 11 | DPO preference pairs |
| artifacts/held_out_test_instructions_20250911_162708.jsonl | 18K | Sep 11 | Test instructions |
| artifacts/sft_training_data_20250913_005116.jsonl | ? | Sep 13 | SFT data (after clean script) |

## Generation Scripts Timeline

| Script | Date | Chat Template Handling | Status |
|--------|------|------------------------|--------|
| generate_stage1_data.py | Sep 10 | ❌ None | Archived (contaminated) |
| stage1_generate.py | Sep 11 | ❌ None | Archived (contaminated) |
| stage1_generate_robust.py | Sep 11 | ❌ None | Archived (contaminated) |
| generate_stage1_sft_data.py | Sep 12 | ✅ Line 130 | Current (clean) |

**Timeline concern**: Most data files (Sep 10-11) predate the clean script (Sep 12).

Exception: `sft_training_data_20250913_005116.jsonl` (Sep 13) is AFTER the clean script - this should be clean!

## Investigation Steps

### 1. Check File Contents for Clues
```bash
# Look at first few examples from each file
head -5 data/stage1/train_instructions.jsonl
head -5 artifacts/preference_pairs.jsonl
head -5 artifacts/sft_training_data_20250913_005116.jsonl

# Check if they contain metadata about generation
grep -i "generated\|script\|version" data/stage1/train_instructions.jsonl | head -5
```

### 2. Check for Generation Logs
```bash
# Look for logs from Sep 10-13
find logs -name "*202509*" -o -name "*stage1*" 2>/dev/null | sort

# Check for generation output in artifacts
ls -lah artifacts/*202509* | sort -k6,7
```

### 3. Inspect Data Format
Different scripts may have used different output formats. Check:
- Field names (instruction vs. prompt?)
- Format markers (END token? specific delimiters?)
- Metadata fields

### 4. Cross-Reference with IMPLEMENTATION_REGISTRY
Check what the registry says about which script generated which files.

## Success Criteria

- [ ] Identified which script generated `data/stage1/train_instructions.jsonl`
- [ ] Identified which script generated `artifacts/preference_pairs.jsonl`
- [ ] Identified which script generated `artifacts/held_out_test_instructions_20250911_162708.jsonl`
- [ ] Determined if Sep 13 data (`sft_training_data_20250913_005116.jsonl`) is clean
- [ ] Made recommendation: use existing data OR regenerate

## Decision Matrix

### If Sep 10-11 data was generated with contaminated scripts:
**Action**: Regenerate all data with `generate_stage1_sft_data.py`
**Reason**: Contaminated data invalidates baseline and training results

### If Sep 10-11 data was generated correctly (despite script timestamps):
**Possible**: Maybe scripts were edited to add chat_template = None, then dates changed later?
**Action**: Verify by inspecting data quality, still consider regenerating for certainty

### If Sep 13 data is clean and sufficient:
**Action**: Use `sft_training_data_20250913_005116.jsonl` as primary dataset
**Reason**: Generated after clean script creation

## Why This Matters

From VERIFICATION_STATUS.md:
> **Timeline issue**: Most data (Sep 10-11) predates the verified clean script (Sep 12).

If we train on contaminated data:
- Base model will appear to already follow instructions (high baseline)
- Training improvements will be minimal
- Results will be invalid for publication
- We'll waste ~$20-25 in GPU costs

Better to spend 30 minutes investigating now than waste GPU hours on invalid data.

## Related Files

- `/docs/DEPRECATED_SCRIPTS.md` - Documents which scripts are contaminated
- `/docs/VERIFICATION_STATUS.md` - Current verification status
- `/docs/BASE_MODEL_TRUTH.md` - Chat template contamination issue
- `scripts/archived/2025_10_03_chat_template_contaminated/` - Old scripts
- `scripts/generate_stage1_sft_data.py` - Current clean script

## Next Steps After This Task

1. If data is contaminated → Create task to regenerate data
2. If data is clean → Update VERIFICATION_STATUS.md with evidence
3. Update IMPLEMENTATION_REGISTRY.md with data provenance notes
