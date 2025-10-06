# Task: Upgrade Evaluation Statistics to Publication Quality

**Priority**: P0 (CRITICAL - Required for publication)
**Created**: 2025-10-04
**Assigned To**: claude_code
**Status**: Pending (Deferred - needs dedicated session)
**From Review**: reviews/responses/20251004_dry_policy_and_migration_codex.md

---

## Problem

Current evaluation (`scripts/evaluate_instruction_following.py`) uses only 12 examples with no statistical tests, confidence intervals, or effect sizes.

**Codex finding** (CRITICAL #2):
> "Evaluation sample size and statistics insufficient for claims. Results are too brittle to support claims (e.g., 'base 10–30%, SFT 70–80%, DPO 90–95%'). Noise and prompt idiosyncrasies can dominate."

---

## Impact

- **Scientific validity**: Cannot support quantitative claims in paper
- **Publication**: Reviewers will reject insufficient sample size and statistics
- **Reproducibility**: No confidence intervals or significance tests

---

## Current State

**Sample size**: 12 examples
**Statistics**: Single success rate percentage
**Testing**: None
**CIs**: None
**Effect sizes**: None

**Example claim** (unsupported):
> "Base 10-30%, SFT 70-80%, SFT+DPO 90-95%"

---

## Solution

Upgrade evaluation to publication-quality statistics.

### 1. Increase Sample Size

**Target**: N ≥ 200 held-out instructions (stratified by type)
**Benefit**: ~±5% Wilson CI on overall rates

**Implementation**:
- Expand from 12 to 200+ diverse instructions
- Stratify across instruction types (QA, completion, format, multi-step, etc.)
- Ensure balanced coverage

### 2. Add Paired Statistical Tests

**Method**: McNemar test for paired binary outcomes
**Comparisons**:
- Base vs SFT
- SFT vs DPO
- Base vs DPO

**Apply**: Benjamini-Hochberg correction for multiple testing across instruction types

**Report**: p-values with correction, per comparison

### 3. Add Effect Sizes

**Metric**: Cohen's h for proportions
**Compute**: Overall and per instruction type
**Report**: Effect size with interpretation (small/medium/large)

### 4. Add Confidence Intervals

**Method**: Wilson CIs (better for proportions than normal approximation)
**Level**: 95% CI
**Compute via**: Bootstrap if needed

**Report**: All rates with [lower, upper] bounds

### 5. Improve Determinism

**Default**: temperature=0 (greedy decoding) for baseline comparability
**If sampling**: Fix RNG seed and log it
**Log**: All library versions, CUDA version, GPU model

**Save**: All settings in JSON output

### 6. Full Logging

**Per evaluation**:
- transformers version
- bitsandbytes version
- torch version
- CUDA version
- GPU name
- Script SHA
- Seeds used
- All generation parameters (temperature, top_p, max_tokens, etc.)

---

## Implementation Plan

**Scope**: Large (separate session needed)

**Files to modify**:
- `scripts/evaluate_instruction_following.py` - Main changes
- Create expanded instruction set (200+ examples)
- Add statistical test utilities
- Update output format to include statistics

**Structure**:
```python
class InstructionFollowingEvaluator:
    def __init__(self, n_examples=200, stratified=True):
        # Load stratified 200+ examples
        ...

    def evaluate_model(self, model_path):
        # Run evaluation
        results = self._evaluate_all()

        # Compute statistics
        stats = self._compute_statistics(results)

        # Save with full logging
        self._save_results(results, stats)

    def _compute_statistics(self, results):
        # Overall success rate + Wilson CI
        # Per-type success rates + CIs
        # Return structured stats dict

    def compare_models(self, base_results, sft_results):
        # McNemar test
        # Cohen's h effect size
        # BH correction across types
        # Return comparison stats
```

---

## Completion Criteria

- [ ] N ≥ 200 held-out instructions (stratified)
- [ ] Paired statistical tests (McNemar) with BH correction
- [ ] Effect sizes (Cohen's h) with interpretation
- [ ] 95% Wilson CIs for all rates
- [ ] Deterministic evaluation (temperature=0 default)
- [ ] Full version logging in output
- [ ] Documentation updated with statistical methodology

---

## Deferred

**Reason**: Large scope, needs dedicated focused session
**Blocks**: Publication claims, but NOT immediate GPU work
**Priority**: High for publication, but migration is more urgent

**When to do**: After migration complete and initial GPU runs done

---

## References

- reviews/responses/20251004_dry_policy_and_migration_codex.md - Codex review (CRITICAL #2, recommendations)
- scripts/evaluate_instruction_following.py - Current implementation
- Statistical methods:
  - McNemar test (paired binary)
  - Cohen's h (effect size for proportions)
  - Wilson CI (confidence intervals)
  - Benjamini-Hochberg (multiple testing correction)
