# P0: Verify Base Model Completion Mode Cleanliness
**Assigned To**: claude_code

**Priority**: P0 (Critical - foundation for all data generation)
**Estimated Time**: 30-60 minutes

## Issue Description

We have marked "Base model completion mode verified" as done in the roadmap, but we need to actually verify:

1. Our test scripts properly prevent chat template contamination
2. Our data generation scripts use the clean approach
3. The sentinel tests from BASE_MODEL_TRUTH.md confirm base model behavior

This is critical because chat template contamination would invalidate our entire approach.

## What Needs Verification

### 1. Test Script Works (test_base_model_ultra_clean.py)
**Location**: `scripts/test_base_model_ultra_clean.py`

**Verify**:
- [ ] Script exists and is executable
- [ ] Sets `tokenizer.chat_template = None` (line 49)
- [ ] Uses `add_special_tokens=False` in tokenization (line 128)
- [ ] Implements sentinel tests from BASE_MODEL_TRUTH.md (lines 79-120)
- [ ] Can be run to generate verification report

**Action**: Run the script (if possible locally or document RunPod run plan)

### 2. Data Generation Uses Clean Approach
**Location**: `scripts/generate_stage1_sft_data.py` (most recent, Sep 12)

**Verify**:
- [x] Sets `tokenizer.chat_template = None` (line 130) ✅
- [ ] Uses `CompletionStylePrompts` for prompting (check import and usage)
- [ ] Generated data exists from this script (check artifacts/)
- [ ] No older/contaminated scripts being used accidentally

**Compare to older scripts**:
- `scripts/stage1_generate.py` (Sep 11) - Does NOT set chat_template = None ❌
- `scripts/stage1_generate_robust.py` (Sep 11) - Need to check
- `scripts/generate_stage1_data.py` (Sep 10) - Need to check

### 3. CompletionStylePrompts Implementation
**Location**: `scripts/utils/data_formatter.py`

**Verify**:
- [x] CompletionStylePrompts class exists ✅
- [x] Implements few-shot completion prompting ✅
- [ ] Actually used in current data generation pipeline
- [ ] Produces prompts that don't trigger instruction-following

## Success Criteria

### Minimum (Must Have)
- [ ] Run test_base_model_ultra_clean.py and confirm sentinel tests PASS (base model should fail instruction tests)
- [ ] Verify generate_stage1_sft_data.py is the script used for current data
- [ ] Confirm existing generated data came from clean script (check timestamps)

### Ideal (Should Have)
- [ ] Document exact command to run verification test
- [ ] Archive or clearly mark older contaminated scripts
- [ ] Add verification step to STANDARDS.md or agent checklists
- [ ] Create quick verification script that can be run before any training

## Why This Matters

From BASE_MODEL_TRUTH.md:
> "If Qwen-2.5-32B base appears to follow instructions well, you have contamination."

If we have contamination:
- Our baseline will be artificially high
- Training improvements will appear smaller
- We won't actually be teaching instruction-following (it's already there)
- Results will be invalid for publication

## Current Evidence

**Good signs**:
- BASE_MODEL_TRUTH.md documents the issue thoroughly
- test_base_model_ultra_clean.py implements proper prevention
- generate_stage1_sft_data.py (most recent) sets chat_template = None
- CompletionStylePrompts exists and implements few-shot completion

**Concerns**:
- Multiple generation scripts exist, unclear which was used
- Older scripts (stage1_generate.py) don't disable chat_template
- No verification run on record showing sentinel tests pass
- ROADMAP marks this as done without verification evidence

## Implementation Plan

1. **Check which script generated our current data**:
   ```bash
   ls -lt data/stage1/
   # Look at timestamps vs. script modification times
   ```

2. **Run verification test** (if GPU available):
   ```bash
   cd /Users/scottmcguire/MaximalCAI
   python scripts/test_base_model_ultra_clean.py
   ```
   Or document RunPod deployment plan if local GPU unavailable.

3. **Review and document findings**:
   - Which scripts are clean vs contaminated
   - Evidence that current data is clean
   - Quick verification command for future use

4. **Update documentation**:
   - Add verification evidence to BASE_MODEL_TRUTH.md
   - Update IMPLEMENTATION_REGISTRY.md with script status
   - Consider adding to STANDARDS.md verification checklist

## Dependencies

- GPU access (local or RunPod) to run verification
- Existing generated data artifacts to check timestamps
- Python environment with transformers, torch, etc.

## Related Files

- `/docs/BASE_MODEL_TRUTH.md` - The contamination documentation
- `/scripts/test_base_model_ultra_clean.py` - Verification script
- `/scripts/generate_stage1_sft_data.py` - Current (clean) generation script
- `/scripts/stage1_generate.py` - Older script (potentially contaminated)
- `/scripts/utils/data_formatter.py` - CompletionStylePrompts implementation
- `ROADMAP.md` line 43, 47 - Claims completion mode is verified

## Notes

This task is about **verification**, not implementation. The code appears to exist and be correct. We just need to:
1. Prove it works (run the test)
2. Prove we're using it (check which scripts generated our data)
3. Document the evidence (so we don't question this again)
