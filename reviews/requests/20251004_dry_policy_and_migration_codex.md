# Review Request: DRY Policy & Methodology Rigor

**Date**: 2025-10-04
**Requester**: claude_code
**Assigned Reviewers**: codex
**Priority**: High
**Type**: Methodology Review (Statistical Rigor, Reproducibility, Experimental Design)

---

## Context

**Problem**: After creating `CleanModelLoader` utility to centralize contamination-free base model loading, we initially migrated only 2/15 scripts. This created the "partial refactoring anti-pattern" - multiple implementation patterns coexisting.

**User feedback**: "I want to improve the policy documents to make the need to implement functionality in exactly one place and share it more salient."

**Methodology concern**: Having TWO patterns for contamination prevention means:
- Some evaluations use centralized safe loader
- Some evaluations use manual contamination prevention
- Future evaluations: which pattern to follow?
- **Risk**: Inconsistent contamination prevention could invalidate experimental results

**Solution**:
1. Establish explicit DRY policy
2. Complete migration to single implementation
3. Create verification procedures

---

## Scope of Review

### Committed Work (Since Oct 3)

**Key methodology-relevant files**:
- `scripts/utils/clean_model_loader.py` (NEW - centralized contamination prevention)
- `scripts/evaluate_instruction_following.py` (migrated evaluation script)
- `scripts/generate_stage1_sft_data.py` (migrated data generation)
- `docs/CLEAN_MODEL_LOADER_MIGRATION.md` (migration guide)
- `docs/RUNPOD_SESSION_PLAN.md` (9-phase execution plan with decision points)

### Current Session Work (Uncommitted)

**Policy documents**:
- `docs/STANDARDS.md` - Added DRY Principle & Single Implementation section (~180 lines)
- `docs/REFACTORING_CHECKLIST.md` (NEW - process for future refactorings)
- `docs/CLEAN_LOADER_MIGRATION_TODO.md` (NEW - migration tracking)

**Migration progress**: 4/15 scripts migrated, 11 remaining

**Status**:
- `ROADMAP.md` - Added blocker warning
- `docs/IMPLEMENTATION_REGISTRY.md` - Added migration status

---

## Review Focus Areas

### 1. Reproducibility Implications

**Question**: Does having partial migration affect reproducibility?

**Scenario 1** (Current state):
- Scripts A, B use CleanModelLoader
- Scripts C, D, E use manual contamination prevention
- Both claim "no chat template contamination"

**Concerns**:
- Are results from A,B comparable to C,D,E?
- If CleanModelLoader has bug, only A,B affected
- If manual pattern has bug, C,D,E affected
- Can we claim consistent methodology in paper?

**Review**: Should we BLOCK all GPU work until migration complete? Or is partial migration acceptable for experimentation?

### 2. Statistical Validity

**CleanModelLoader verification** (`scripts/utils/clean_model_loader.py`):

```python
def tokenize_clean(self, tokenizer, prompt: str):
    """Tokenize with contamination prevention"""
    inputs = tokenizer(prompt, add_special_tokens=False, ...)

    # Verify no contamination markers
    first_10_tokens = inputs['input_ids'][0][:10].tolist()
    token_preview = tokenizer.decode(first_10_tokens, ...)

    contamination_markers = ['<|im_start|>', '<|im_end|>', ...]
    if any(marker in token_preview for marker in contamination_markers):
        raise RuntimeError("Chat template contamination detected!")
```

**Questions**:
1. Is checking first 10 tokens sufficient? Could contamination appear later?
2. Are contamination markers comprehensive? Are we missing any?
3. Should we verify EVERY generation, or just at initialization?
4. Does this add meaningful overhead to evaluation time?

### 3. Evaluation Script Migration

**File**: `scripts/evaluate_instruction_following.py` (migrated)

**Before** (manual):
- ~30 lines of contamination prevention
- Easy to forget steps
- No verification of effectiveness

**After** (CleanModelLoader):
- ~3 lines to load model
- Automatic verification
- Centralized updates

**Methodology question**: Are we confident the migrated version produces identical results to manual version? Should we run A/B test to verify?

**Suggestion**: Run same evaluation with manual vs CleanModelLoader and compare results?

### 4. Data Generation Implications

**File**: `scripts/generate_stage1_sft_data.py` (migrated)

**Concern**: Training data was generated with this script. If migration changes behavior:
- All training data may need regeneration
- Baseline evaluations may need rerun
- Timeline impact

**Question**: Do we have versioning/checksums for generated data to detect if migration changes output?

### 5. Experimental Design: Migration Strategy

**Current plan** (from CLEAN_LOADER_MIGRATION_TODO.md):
- Migrate all 15 scripts to CleanModelLoader
- Verify no manual patterns remain
- Then proceed with GPU work

**Alternative approaches**:
1. **Parallel validation**: Run both patterns on same data, compare results
2. **Staged migration**: Migrate evaluation scripts first, data generation later
3. **Current approach**: Complete migration before GPU work

**Question**: Is current approach best for scientific rigor? Or should we validate equivalence first?

### 6. Documentation Standards

**New DRY policy** (`docs/STANDARDS.md`):

> **EVERY piece of functionality MUST exist in EXACTLY ONE place**
>
> **Partial refactoring is NO BETTER than reimplementation.**

**Methodology perspective**:
- This is good software engineering
- Is it also good for reproducibility?
- Should we version stamp which pattern was used per result?
- How do we document this in methods section of paper?

**Review**: Is this policy sufficient to prevent future inconsistencies?

### 7. RunPod Session Plan

**File**: `docs/RUNPOD_SESSION_PLAN.md` (504 lines, 9 phases)

**Review for**:
- Are decision points clearly defined?
- Are success criteria measurable?
- Are failure recovery steps adequate?
- Is there clear documentation of what was run when?
- Can we reproduce results from logs?

**Specific phases**:
- Phase 2: Baseline evaluation (uses evaluate_instruction_following.py)
- Phase 3: SFT data generation (uses generate_stage1_sft_data.py)
- Phase 5: Post-SFT evaluation

**Question**: Are we confident migrated scripts will work correctly in RunPod environment?

---

## Specific Questions

### Reproducibility
1. Does partial migration compromise reproducibility?
2. Should we version-stamp which contamination prevention pattern was used?
3. How do we document this methodology in paper?

### Statistical Rigor
4. Is contamination verification comprehensive enough?
5. Should we A/B test manual vs CleanModelLoader to prove equivalence?
6. How do we handle if migration changes results slightly?

### Experimental Design
7. Should we complete migration before ANY GPU work? (current plan)
8. Or validate equivalence first, then migrate gradually?
9. What's the scientific cost of having two patterns temporarily?

### Documentation
10. Is DRY policy sufficient to prevent future issues?
11. Do we need versioning/checksums for code used per result?
12. How detailed should methods section be about this?

### Timeline Impact
13. If migration introduces bugs, what's the recovery plan?
14. Do we have rollback strategy?
15. What's the cost-benefit of waiting for complete migration vs starting GPU work?

---

## Files to Review

### Priority 1 (Methodology Impact)
- `docs/STANDARDS.md` (DRY section, lines 174-350)
- `docs/RUNPOD_SESSION_PLAN.md` (execution plan)
- `scripts/evaluate_instruction_following.py` (migrated evaluation)
- `scripts/generate_stage1_sft_data.py` (migrated data gen)

### Priority 2 (Verification & Process)
- `docs/REFACTORING_CHECKLIST.md` (future process)
- `docs/CLEAN_MODEL_LOADER_MIGRATION.md` (migration guide)
- `docs/CLEAN_LOADER_MIGRATION_TODO.md` (tracking)
- `ROADMAP.md` (blocker section)

### Priority 3 (Implementation Details)
- `scripts/utils/clean_model_loader.py` (contamination prevention)
- `scripts/test_base_model_ultra_clean.py` (migrated test)
- `scripts/test_clean_base_model.py` (migrated test)

---

## Success Criteria

**Review is complete when**:
1. Reproducibility implications assessed
2. Statistical validity of approach confirmed
3. Migration strategy validated or alternatives suggested
4. Documentation adequacy assessed
5. Risk/benefit analysis provided for migration timeline
6. Any methodology concerns flagged

**Severity levels**:
- 🚨 **CRITICAL**: Compromises scientific validity, must address before publication
- ⚠️ **HIGH**: Should address before deployment, affects reproducibility
- 💡 **SUGGESTIONS**: Best practices for rigor

---

## Context for Review

**Budget**: ~$20 for Stage 1 (~11 hours GPU time at $1.74/hr)
- Baseline eval: ~30 min
- Data generation: ~2-4 hours
- Training: ~2-3 hours
- Post-training eval: ~30 min each (3 checkpoints)

**Timeline**: Targeting Oct 15 for Stage 1 completion

**Publication goal**: Demonstrate automated Constitutional AI at 32B scale

**At stake**:
- Scientific validity of results
- Reproducibility for future researchers
- Publication credibility
- Timeline for paper submission

---

## Key User Feedback

> "I have concerns. The state we were in after writing the central code but not updating other code to call it is similar to the state we get into when we reimplement rather than reuse existing code."

> "I want to improve the policy documents to make the need to implement functionality in exactly one place and share it more salient."

**This isn't just about code quality** - it's about ensuring our experimental methodology is consistent and reproducible.

---

Thank you for the methodology review!
