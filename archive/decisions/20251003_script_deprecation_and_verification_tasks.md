# Script Deprecation and Verification Tasks

**Date**: 2025-10-03
**Trigger**: User concern about marked-as-done items lacking verification

---

## Summary

In response to user questions about verification of "done" items in the roadmap, we:

1. **Investigated verification status** of critical claims
2. **Identified contaminated scripts** that should not be used
3. **Archived deprecated scripts** to prevent confusion
4. **Created verification tasks** for unverified claims

---

## Key Findings

### Chat Template Contamination Issue

**Discovery**: Three older data generation scripts do NOT disable `tokenizer.chat_template`:

| Script | Date | Contaminated? | Action |
|--------|------|---------------|--------|
| generate_stage1_data.py | Sep 10 | ❌ YES | Archived |
| stage1_generate.py | Sep 11 | ❌ YES | Archived |
| stage1_generate_robust.py | Sep 11 | ❌ YES | Archived |
| generate_stage1_sft_data.py | Sep 12 | ✅ Clean (line 130) | Current |

**Problem**: Existing data files (Sep 10-11) predate the verified clean script (Sep 12).

**Risk**: If trained on contaminated data, results would be invalid.

### Verification Gap

**What we claimed** (in ROADMAP.md):
- ✅ "Base model completion mode verified"
- ✅ "Chat template contamination fix applied"

**What actually exists**:
- ✅ Code exists and is correct
- ❌ Code has never been executed
- ❌ No verification output showing it works
- ❌ Data provenance uncertain

**Lesson**: Distinguished "implemented" from "verified working"

---

## Actions Taken

### 1. Created Documentation

#### `/docs/DEPRECATED_SCRIPTS.md`
- Lists deprecated scripts with reasons
- Documents archiving process
- Explains why we archive instead of delete
- Template for future deprecations

#### `/docs/VERIFICATION_STATUS.md`
- Tracks verification status of critical claims
- Documents evidence found vs. evidence missing
- Provides verification checklist
- Template for future verifications

### 2. Archived Contaminated Scripts

**Created archive directory**:
```
scripts/archived/2025_10_03_chat_template_contaminated/
├── generate_stage1_data.py
├── stage1_generate.py
└── stage1_generate_robust.py
```

**Created breadcrumb files**:
- `scripts/stage1_generate.py.DEPRECATED` (→ points to archive location)
- `scripts/stage1_generate_robust.py.DEPRECATED`
- `scripts/generate_stage1_data.py.DEPRECATED`

**Git operations**:
```bash
git mv scripts/stage1_generate.py scripts/archived/2025_10_03_chat_template_contaminated/
git mv scripts/stage1_generate_robust.py scripts/archived/2025_10_03_chat_template_contaminated/
git mv scripts/generate_stage1_data.py scripts/archived/2025_10_03_chat_template_contaminated/
```

### 3. Created Verification Tasks

#### P0: `/tasks/claude_code/pending/P0_verify_base_model_cleanliness.md`
**Purpose**: Execute verification tests to prove base model handling is clean

**Key actions**:
- Run `test_base_model_ultra_clean.py` and document results
- Verify sentinel tests pass (base model should FAIL instruction tests)
- Confirm CompletionStylePrompts is used correctly
- Document verification evidence

**Why P0**: Foundation for all training. If contaminated, entire approach is invalid.

#### P1: `/tasks/claude_code/pending/P1_determine_existing_data_provenance.md`
**Purpose**: Determine which script generated existing data (Sep 10-11)

**Key actions**:
- Investigate which script created `data/stage1/train_instructions.jsonl`
- Check if existing data is contaminated
- Decide: use existing data OR regenerate with clean script

**Why P1**: Affects whether we need to regenerate data before training (~$20-25 GPU cost at stake).

#### P2: `/tasks/claude_code/pending/P2_audit_implementation_registry.md`
**Purpose**: Verify IMPLEMENTATION_REGISTRY.md is current and accurate

**Key actions**:
- Check all scripts are listed
- Verify entries are accurate
- Mark deprecated scripts
- Reorganize if needed

**Why P2**: Maintenance task to prevent future re-implementation, but not blocking training.

---

## Current Status

### Archived Scripts
- ✅ 3 contaminated scripts moved to archive
- ✅ Breadcrumb files created
- ✅ Git operations complete

### Documentation
- ✅ DEPRECATED_SCRIPTS.md created
- ✅ VERIFICATION_STATUS.md created
- ✅ 3 verification tasks created
- 📋 Need to update IMPLEMENTATION_REGISTRY.md (covered by P2 task)

### Verification Tasks
- 📋 P0: Verify base model cleanliness (not started)
- 📋 P1: Determine data provenance (not started)
- 📋 P2: Audit IMPLEMENTATION_REGISTRY (not started)

---

## Impact on Roadmap

### Items Previously Marked as Done (Now Questioned)

**ROADMAP.md line 43**:
```markdown
- [x] Base model completion mode verified (no instruction template leakage)
```

**Should be**:
```markdown
- [x] Base model completion mode implemented (CompletionStylePrompts)
- [ ] Base model completion mode verified (need to run test)
```

**ROADMAP.md line 47**:
```markdown
- [x] Base model completion mode implementation (CompletionStylePrompts)
```

**Should be**:
```markdown
- [x] Base model completion mode implementation (CompletionStylePrompts)
- [x] Clean script created (generate_stage1_sft_data.py)
- [ ] Contaminated scripts archived
- [ ] Verification test executed
```

### Recommendation

Before proceeding to RunPod training:
1. ✅ Complete P0 verification task
2. ✅ Complete P1 data provenance task
3. ⚠️  Regenerate data if contaminated
4. Then proceed to training

---

## Lessons Learned

### 1. Distinguish "Implemented" from "Verified"

**Problem**: Marking something "done" when code exists but hasn't been tested.

**Solution**: Verification checklist in VERIFICATION_STATUS.md:
- [ ] Code/script exists
- [ ] Code is correct
- [ ] Code has been executed
- [ ] Execution results documented
- [ ] Results meet success criteria
- [ ] Evidence archived

### 2. Deprecated Code Causes Confusion

**Problem**: Multiple scripts with similar names, unclear which is current.

**Solution**:
- Archive deprecated scripts promptly
- Leave breadcrumb files
- Document in DEPRECATED_SCRIPTS.md
- Update IMPLEMENTATION_REGISTRY.md

### 3. Data Provenance Matters

**Problem**: Data exists, but we don't know which script generated it.

**Solution**:
- Include generation metadata in output files
- Save generation logs with timestamps
- Cross-reference file timestamps with script modifications
- Document in IMPLEMENTATION_REGISTRY.md

### 4. Timeline Analysis is Critical

**Problem**: Assumed data was clean because a clean script exists.

**Reality**: Data predates the clean script!

**Solution**: Always check file timestamps vs. script timestamps.

---

## Files Created/Modified

### Created
- `/docs/DEPRECATED_SCRIPTS.md`
- `/docs/VERIFICATION_STATUS.md`
- `/tasks/claude_code/pending/P0_verify_base_model_cleanliness.md`
- `/tasks/claude_code/pending/P1_determine_existing_data_provenance.md`
- `/tasks/claude_code/pending/P2_audit_implementation_registry.md`
- `/scripts/*.DEPRECATED` (3 breadcrumb files)
- `/archive/decisions/20251003_script_deprecation_and_verification_tasks.md` (this file)

### Modified (via git mv)
- `scripts/stage1_generate.py` → `scripts/archived/2025_10_03_chat_template_contaminated/`
- `scripts/stage1_generate_robust.py` → `scripts/archived/2025_10_03_chat_template_contaminated/`
- `scripts/generate_stage1_data.py` → `scripts/archived/2025_10_03_chat_template_contaminated/`

### To Be Modified (by future tasks)
- `ROADMAP.md` - Update verification status markers
- `/docs/IMPLEMENTATION_REGISTRY.md` - Mark deprecated scripts (P2 task)

---

## Next Session Expectations

When returning to this project:

1. **Read this file** to understand what happened
2. **Check task status**: `ls tasks/claude_code/pending/P*.md`
3. **Priority order**: P0 → P1 → P2
4. **Before training**: Ensure P0 and P1 are complete

---

## User Feedback

**User request 1**: "Can we deprecate or even delete (since we have git) code which is no longer current? Otherwise this is going to lead to confusion."

**Response**: ✅ Archived 3 contaminated scripts, left breadcrumbs, documented in DEPRECATED_SCRIPTS.md

**User request 2**: "Make sure we have tasks for all the missing or unverified things you discovered."

**Response**: ✅ Created 3 tasks (P0, P1, P2) covering all unverified items from VERIFICATION_STATUS.md

---

**Completion time**: ~90 minutes of work
**Impact**: Clarified project state, prevented training on potentially contaminated data, established verification standards
