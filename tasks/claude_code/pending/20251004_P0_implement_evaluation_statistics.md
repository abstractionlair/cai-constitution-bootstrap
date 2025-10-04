# Task: Implement Publication-Quality Evaluation Statistics

**Priority**: P0 (CRITICAL - Blocks GPU work)
**Created**: 2025-10-04
**Assigned To**: claude_code
**Estimated Time**: 3-4 hours
**From Review**: reviews/responses/20251004_roadmap_and_budget_codex.md

---

## Problem

Current evaluation (N=12) insufficient for publication claims. Need paired statistical design with proper tests, corrections, effect sizes, and confidence intervals.

**Codex requirement**:
> "Use a paired design across identical items for base vs SFT vs DPO; N ≥ 200 (prefer 300–500) stratified by instruction type. Tests: McNemar for paired binary outcomes per type + overall; Benjamini–Hochberg correction across types. Report Wilson CIs and Cohen's h (overall and per type)."

---

## Requirements

### 1. Evaluation Protocol

**Sample size**: N = 800-1200 (target 1000)
- Stratified by instruction type
- Paired design: identical items for base/SFT/DPO comparisons

**Decoding**:
- Default: deterministic (temperature=0, greedy) for baselines
- If sampling: fix seeds, log all params

**Outputs**:
- Per-example: instruction, response, success (binary), instruction_type
- Summary: overall + per-type statistics

### 2. Statistical Tests

**Primary test**: McNemar for paired binary outcomes
- Compare: base↔SFT, SFT↔DPO, base↔DPO
- Run: overall + per instruction type

**Multiple testing correction**: Benjamini-Hochberg (FDR=0.10)
- Apply across instruction types
- Report: raw p-values + adjusted p-values

### 3. Effect Sizes

**Cohen's h**: For proportion differences
- Formula: 2 * (arcsin(sqrt(p1)) - arcsin(sqrt(p2)))
- Report: overall + per-type

**Interpretation**:
- |h| < 0.2: small
- |h| ≈ 0.5: medium
- |h| ≥ 0.8: large

### 4. Confidence Intervals

**Wilson CIs**: For proportions (95% confidence)
- More accurate than normal approximation for binary data
- Report: overall + per-type success rates

**Bootstrap CIs**: For deltas where helpful
- Use if Wilson doesn't apply cleanly
- 10,000 bootstrap samples

**Power targets** (at N=1000, p≈0.7-0.9):
- Overall CI width: ±2.5-3.0%
- Per-type: wider, depends on stratification

---

## Implementation Plan

### Phase 1: Create Statistical Analysis Utility

**File**: `scripts/utils/eval_statistics.py`

**Functions**:
```python
def mcnemar_test(n01, n10):
    """McNemar test for paired binary outcomes

    Args:
        n01: Count of (model1=0, model2=1)
        n10: Count of (model1=1, model2=0)

    Returns:
        chi2, p_value
    """

def benjamini_hochberg(p_values, fdr=0.10):
    """Benjamini-Hochberg correction for multiple testing

    Args:
        p_values: List of p-values
        fdr: False discovery rate (default 0.10)

    Returns:
        adjusted_p_values, rejections (boolean array)
    """

def cohens_h(p1, p2):
    """Cohen's h effect size for proportions

    Args:
        p1, p2: Proportions to compare

    Returns:
        h (effect size)
    """

def wilson_ci(successes, n, confidence=0.95):
    """Wilson confidence interval for proportion

    Args:
        successes: Number of successes
        n: Total trials
        confidence: Confidence level (default 0.95)

    Returns:
        (lower, upper)
    """

def bootstrap_ci(data1, data2, func, n_bootstrap=10000, confidence=0.95):
    """Bootstrap confidence interval for statistic

    Args:
        data1, data2: Arrays of binary outcomes
        func: Function to compute statistic (e.g., lambda d1, d2: d1.mean() - d2.mean())
        n_bootstrap: Number of bootstrap samples
        confidence: Confidence level

    Returns:
        (lower, upper)
    """

def paired_comparison_analysis(model1_results, model2_results, labels,
                               instruction_types=None, fdr=0.10):
    """Complete paired comparison with tests, corrections, effect sizes, CIs

    Args:
        model1_results: Array of binary outcomes for model 1
        model2_results: Array of binary outcomes for model 2
        labels: (model1_name, model2_name)
        instruction_types: Optional array of types for stratification
        fdr: False discovery rate for BH correction

    Returns:
        {
            'overall': {...},
            'by_type': {...},
            'metadata': {...}
        }
    """
```

### Phase 2: Update Evaluation Scripts

**Files to update**:
- `scripts/evaluate_stage1_comprehensive.py`
- `scripts/evaluate_final.py`
- `scripts/evaluate_capability_differentiation_sequential.py`

**Changes**:
1. Increase N to 1000 (or make configurable)
2. Add `--deterministic` flag (default True for baselines)
3. Save per-example results with instruction_type
4. After evaluation, run statistical analysis:
   ```python
   from utils.eval_statistics import paired_comparison_analysis

   analysis = paired_comparison_analysis(
       base_results, sft_results,
       labels=('base', 'sft'),
       instruction_types=instruction_types,
       fdr=0.10
   )
   ```
5. Include analysis in output JSON under `statistics` key

### Phase 3: Output Format

**Evaluation JSON structure**:
```json
{
  "metadata": {
    "git_commit": "...",
    "eval_seed": 42,
    "n_examples": 1000,
    "deterministic": true,
    "temperature": 0,
    "stratification": ["list", "count", "sort", ...]
  },
  "results": [
    {
      "instruction": "...",
      "instruction_type": "list",
      "base_response": "...",
      "base_success": true,
      "sft_response": "...",
      "sft_success": true,
      "dpo_response": "...",
      "dpo_success": true
    },
    ...
  ],
  "summary": {
    "base_accuracy": 0.15,
    "sft_accuracy": 0.78,
    "dpo_accuracy": 0.91
  },
  "statistics": {
    "base_vs_sft": {
      "overall": {
        "mcnemar_chi2": 450.2,
        "mcnemar_p": 1.2e-99,
        "cohens_h": 1.45,
        "base_rate": 0.15,
        "base_ci": [0.13, 0.17],
        "sft_rate": 0.78,
        "sft_ci": [0.75, 0.81],
        "lift": 0.63,
        "lift_ci_bootstrap": [0.60, 0.66]
      },
      "by_type": {
        "list": {
          "mcnemar_chi2": 85.3,
          "mcnemar_p_raw": 3.4e-20,
          "mcnemar_p_adjusted": 2.4e-19,
          "significant_after_bh": true,
          "cohens_h": 1.52,
          ...
        },
        ...
      },
      "bh_correction": {
        "fdr": 0.10,
        "n_tests": 12,
        "n_significant": 11
      }
    },
    "sft_vs_dpo": { ... },
    "base_vs_dpo": { ... }
  }
}
```

### Phase 4: Testing

**Unit tests**: `tests/test_eval_statistics.py`
- Test each statistical function with known inputs
- Verify McNemar against statsmodels/scipy
- Verify BH correction
- Verify Wilson CI
- Verify Cohen's h

**Integration test**: Small eval (N=100) with mocked results
- Verify end-to-end pipeline
- Verify JSON output structure

---

## Dependencies

```python
# Add to requirements if not present
scipy>=1.7.0  # For statistical tests
numpy>=1.21.0
statsmodels>=0.13.0  # Optional, for verification
```

---

## Success Criteria

- [ ] `eval_statistics.py` created with all required functions
- [ ] Unit tests pass for all statistical functions
- [ ] At least one eval script updated (recommend: evaluate_final.py)
- [ ] Output JSON includes `statistics` section with:
  - [ ] McNemar tests (overall + per-type)
  - [ ] BH correction with adjusted p-values
  - [ ] Cohen's h effect sizes
  - [ ] Wilson CIs for proportions
  - [ ] Bootstrap CIs for lifts
- [ ] Documentation: docstrings explain formulas and interpretation
- [ ] Verification: Compare against R/statsmodels for small test case

---

## References

**McNemar test**:
- Formula: χ² = (|n01 - n10| - 1)² / (n01 + n10)
- Continuity correction applied
- df = 1

**Benjamini-Hochberg**:
- Order p-values: p(1) ≤ p(2) ≤ ... ≤ p(m)
- Find largest i where p(i) ≤ (i/m) * FDR
- Reject H(1), ..., H(i)

**Cohen's h**:
- h = 2 * (arcsin(√p1) - arcsin(√p2))
- Interpretation: |h| < 0.2 small, ≈0.5 medium, ≥0.8 large

**Wilson CI**:
- More complex formula than normal approximation
- Better coverage for extreme proportions
- See: scipy.stats.proportion_confint with method='wilson'

**Codex review**: reviews/responses/20251004_roadmap_and_budget_codex.md

---

## Notes

- This blocks GPU work because we need proper eval infrastructure before generating production data
- Expect SFT lift: +40-60pp over base
- Expect DPO lift: +10-20pp over SFT on constraints
- At N=1000, overall CI ≈ ±2.5-3.0%
- Can start with one eval script, then migrate others once pattern is proven
