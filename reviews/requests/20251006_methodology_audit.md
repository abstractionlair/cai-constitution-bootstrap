# Methodology Audit - Code vs Specification Alignment

**Date**: 2025-10-06
**Requested By**: Scott McGuire
**Assigned Reviewers**: Codex, Gemini, Claude Code
**Priority**: High
**Type**: Open-Ended Code Review

---

## Purpose

Conduct an open-ended review of the Constitutional AI codebase to identify discrepancies between documentation/specifications and actual implementation. This audit will help us align the code with our intended methodology before generating 15k training examples.

---

## Review Scope

### Code to Review

**Data Generation**:
- `scripts/generate_sample_data.py`
- `scripts/generate_data_parallel.py`
- `scripts/generate_stage1_sft_data.py`
- `scripts/generate_preference_pairs_logprob.py`
- `scripts/generate_diverse_negatives.py`
- `scripts/generate_test_instructions.py`

**Training**:
- `scripts/train_stage1_sft.py`
- `scripts/train_stage1_dpo.py`
- `scripts/train_stage1_dpo_improved.py`
- `scripts/train_dpo_simple.py`

**Evaluation**:
- `scripts/evaluate_stage1_comprehensive.py`
- `scripts/evaluate_stage1_corrected.py`
- `scripts/evaluate_stage1_simple.py`
- `scripts/evaluate_instruction_following.py`
- `scripts/evaluate_capability_differentiation.py`

**Utilities**:
- `scripts/utils/data_formatter.py`
- `scripts/utils/clean_model_loader.py`
- `scripts/utils/eval_statistics.py`
- `scripts/utils/instruction_generator.py` (new)
- `scripts/utils/instruction_critic.py` (new)

**Pipeline**:
- `scripts/stage1_incremental.py`
- `scripts/run_stage1_pipeline.py`

### Documentation to Check Against

**Specifications**:
- `specs/stage_1_explicit_instructions.md`
- `specs/stage_1_evaluation.md`
- `specs/complete_pipeline.md`

**Documentation**:
- `docs/POST_TRAINING_APPROACHES.md`
- `docs/FEW_SHOT_PROMPTING.md`
- `docs/DATA_GENERATION_ARCHITECTURE.md`
- `docs/BASE_MODEL_TRUTH.md`
- `docs/IMPLEMENTATION_REGISTRY.md`
- `docs/KNOWN_BUGS_AND_FIXES.md`

---

## What to Look For

### 1. Spec-Implementation Mismatches

**Questions to ask**:
- Does the code do what the specs say it should?
- Are promised features actually implemented?
- Are documented approaches actually used?
- Do specs describe one method but code uses another?

**Examples**:
- Spec says "use completion-style prompts" but code uses instruction-style
- Spec says "use logprob-based critique" but code uses text generation
- Spec says "model-generated instructions" but code uses templates

### 2. Implementation Inconsistencies

**Questions to ask**:
- Is functionality implemented in one place but reimplemented differently elsewhere?
- Are utilities created but not used where they should be?
- Do different scripts solve the same problem in different ways?
- Is there duplication that suggests unawareness of existing code?

**Examples**:
- `generate_preference_pairs_logprob.py` has logprob method, but other scripts reimplement it
- `clean_model_loader.py` exists but some scripts load models manually
- Multiple scripts have their own instruction generation logic
- Same prompt formats defined in multiple places

### 3. Methodology Discrepancies

**Questions to ask**:
- Are we using completion-style prompts consistently for base model?
- Are we using the methods we said we'd use (e.g., logprob-based critique)?
- Are evaluation and training using consistent approaches?
- Do we handle chat template contamination consistently?

**Examples**:
- Some scripts set `chat_template = None`, others don't
- Some scripts use `add_special_tokens=False`, others use `True`
- Evaluation uses different prompt format than training
- Base model gets "help" during evaluation (shouldn't)

### 4. Missing or Incomplete Features

**Questions to ask**:
- Are there features described in docs that don't exist?
- Are there TODO comments indicating incomplete work?
- Are there obvious gaps in functionality?

**Examples**:
- Docs mention "persistent evaluation set" but it's not implemented
- Specs describe critique step but it's not in the pipeline
- IMPLEMENTATION_REGISTRY lists features that don't exist

### 5. Any Other Issues You Notice

**This is an open-ended review** - flag anything that seems:
- Inconsistent
- Duplicated
- Misaligned
- Incorrect
- Incomplete
- Confusing

Include things that work but don't match what we documented.

---

## Output Format

For each finding, provide:

```markdown
### Finding N: [Brief Title]

**File:Line**: path/to/file.py:123 (if applicable)

**Issue**: Brief description of the discrepancy

**Expected** (per docs/specs): What should be there according to documentation

**Actual** (in code): What is actually implemented

**Impact**:
- [ ] Low - Minor inconsistency, cosmetic
- [ ] Medium - Affects quality or maintainability
- [ ] High - Affects correctness or validity of results
- [ ] Critical - Invalidates experiments or training

**Recommendation**: How to fix this

**Related Files**: Other files affected by this issue
```

---

## Specific Areas of Concern

Based on recent discussions, pay special attention to:

1. **Instruction Generation**:
   - Are we using template-based (old) or model-generated (intended)?
   - `generate_sample_data.py` uses templates - is this intentional?

2. **Quality Filtering**:
   - Are we using logprob-based critique where we said we would?
   - `generate_preference_pairs_logprob.py` has the method - is it used?

3. **Chat Template Handling**:
   - Do all scripts properly disable chat templates?
   - Do all scripts use `add_special_tokens=False`?
   - See `docs/KNOWN_BUGS_AND_FIXES.md` for critical bug history

4. **Prompt Consistency**:
   - Are training prompts and evaluation prompts consistent?
   - Do we use completion-style for base model everywhere?

5. **Code Reuse**:
   - Are utilities in `scripts/utils/` actually being used?
   - Or are scripts reimplementing functionality?

---

## Deliverables

1. **Finding List**: All discrepancies found, formatted as above
2. **Severity Summary**: Count of Low/Medium/High/Critical findings
3. **Priority Recommendations**: Top 5 issues to fix before 15k generation
4. **Methodology Gaps**: Features we said we'd use but aren't

---

## Timeline

- **Review Due**: 2025-10-07 (1 day)
- **Synthesis**: 2025-10-07 (after all reviews in)
- **Fixes**: 2025-10-08 (address critical/high before generation)

---

## Notes

- This is a collaborative review - all three models will review independently
- Findings will be synthesized to identify patterns
- Issues flagged by multiple reviewers will be prioritized
- Be thorough and critical - we want to find problems before expensive GPU runs

---

**Please be comprehensive**. Look for anything that doesn't match between what we documented and what we implemented. We're about to generate 15k training examples - we need the methodology to be correct.
