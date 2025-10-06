# Deprecated Scripts

This document tracks scripts that are no longer current and should not be used.

**Policy**: Deprecated scripts are moved to `scripts/archived/` with a note explaining why. We use git, so nothing is truly deleted, but keeping deprecated code in the main directory causes confusion.

**Last Updated**: 2025-10-03

---

## Stage 1 Data Generation Scripts

### ❌ `stage1_generate.py` - DEPRECATED (CONTAMINATED)

**Created**: Sep 11, 2025
**Deprecated**: Oct 3, 2025
**Reason**: **Chat template contamination** - does not disable tokenizer.chat_template

**Problem**:
- Line 165: Loads tokenizer without disabling chat_template
- Line 199: Uses tokenizer() without add_special_tokens=False
- This causes the base model to behave like an instruction-tuned model
- Would invalidate baseline evaluation

**Correct version**: Use `generate_stage1_sft_data.py` instead

**Action**: Move to `scripts/archived/2025_10_03_contaminated/`

---

### ❌ `stage1_generate_robust.py` - DEPRECATED (SUPERSEDED)

**Created**: Sep 11, 2025
**Deprecated**: Oct 3, 2025
**Reason**: Superseded by `generate_stage1_sft_data.py`

**Status**: Need to check for chat_template handling before archiving

**Action**: Review script, then move to `scripts/archived/2025_10_03_superseded/`

---

### ❌ `generate_stage1_data.py` - DEPRECATED (SUPERSEDED)

**Created**: Sep 10, 2025
**Deprecated**: Oct 3, 2025
**Reason**: Superseded by `generate_stage1_sft_data.py`

**Status**: Need to check for chat_template handling before archiving

**Note**: This is the oldest generation script. Likely was used to generate the Sep 10 data in data/stage1/.

**Action**: Review script, check if it generated existing data, then move to `scripts/archived/2025_10_03_superseded/`

---

## Current (Canonical) Scripts

These are the scripts that SHOULD be used:

### ✅ `generate_stage1_sft_data.py` - PRIMARY SFT DATA GENERATOR

**Purpose**: Generate clean SFT training data
**Status**: Current, verified clean
**Key features**:
- Line 130: `tokenizer.chat_template = None` ✅
- Line 273: `add_special_tokens=False` ✅
- Uses CompletionStylePrompts ✅

**Generated**: `artifacts/sft_training_data_20250913_005116.jsonl` (200 examples)

### ✅ `test_base_model_ultra_clean.py` - BASE MODEL VERIFICATION

**Purpose**: Verify no chat template contamination
**Status**: Current, not yet executed
**Key features**:
- Line 49: `tokenizer.chat_template = None` ✅
- Line 128: `add_special_tokens=False` ✅
- Implements sentinel tests from BASE_MODEL_TRUTH.md ✅

### ✅ `train_stage1_sft.py` - SFT TRAINING

**Purpose**: Train SFT model
**Status**: Current

### ✅ `train_stage1_dpo_improved.py` - DPO TRAINING

**Purpose**: Train DPO model
**Status**: Current

### ✅ `create_preference_pairs_improved.py` - PREFERENCE PAIR GENERATION

**Purpose**: Generate preference pairs for DPO
**Status**: Current

---

## Archiving Process

When deprecating a script:

1. **Document why** in this file
2. **Create archive directory**: `scripts/archived/YYYY_MM_DD_reason/`
3. **Move script**: `git mv scripts/old_script.py scripts/archived/YYYY_MM_DD_reason/`
4. **Leave breadcrumb**: Create `scripts/old_script.py.DEPRECATED` with pointer
5. **Update IMPLEMENTATION_REGISTRY.md**: Mark as deprecated
6. **Commit**: `git commit -m "Archive deprecated script: reason"`

### Breadcrumb File Format

Create `scripts/[script_name].py.DEPRECATED`:

```
This script has been deprecated and moved to scripts/archived/YYYY_MM_DD_reason/

Reason: [Brief explanation]

Use instead: [current_script.py]

See docs/DEPRECATED_SCRIPTS.md for details.
```

---

## Scripts Pending Review

These scripts need to be checked before deciding to deprecate:

- [ ] `stage1_generate_robust.py` - Check chat_template handling
- [ ] `generate_stage1_data.py` - Check chat_template handling, determine if it generated Sep 10 data
- [ ] `evaluate_stage1_corrected.py` - Is this current or superseded?
- [ ] `evaluate_stage1_comprehensive.py` - Is this current or superseded?
- [ ] `evaluate_stage1_readiness.py` - Is this current or superseded?
- [ ] `test_clean_base_model.py` - Is this superseded by test_base_model_ultra_clean.py?
- [ ] `test_base_model_definitive.py` - Is this superseded by test_base_model_ultra_clean.py?

---

## Why We Archive Instead of Delete

1. **Git preserves history** - Nothing is truly deleted, but...
2. **Confusion reduction** - Developers won't accidentally use old scripts
3. **Clear current state** - Easy to see what's canonical
4. **Audit trail** - DEPRECATED breadcrumbs explain what happened
5. **Recovery option** - Can restore from archive if needed

---

## Related Documents

- `/docs/BASE_MODEL_TRUTH.md` - Chat template contamination issue
- `/docs/IMPLEMENTATION_REGISTRY.md` - Current script catalog
- `/docs/VERIFICATION_STATUS.md` - What's verified vs. claimed
- `/tasks/claude_code/pending/P0_verify_base_model_cleanliness.md` - Verification task
