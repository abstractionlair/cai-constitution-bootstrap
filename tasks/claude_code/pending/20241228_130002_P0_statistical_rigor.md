# Task: Add Statistical Rigor to Evaluation

## Task: Switch to deterministic evaluation and add statistical tests
Priority: P0 (CRITICAL - affects validity)
Estimated Time: 0.75 hours
Created: 2024-12-28 13:00
Created By: Claude (Project)

## Objective
Make evaluation deterministic and add proper statistical analysis with confidence intervals.

## Success Criteria
- [ ] Evaluation uses deterministic decoding (no sampling)
- [ ] Confidence intervals calculated for all metrics
- [ ] Paired statistical test (McNemar's) for base vs trained
- [ ] Results include p-values and effect sizes

## Files to Modify
- `scripts/evaluate_stage1.py` - Set `do_sample=False`, temperature=0
- `scripts/baseline_assessment.py` - Same deterministic settings
- `scripts/utils/metrics.py` - Add statistical functions
- Update result reporting to include CIs and p-values

## Dependencies
- Should be done after precision fix

## Implementation Notes
Current issues:
1. Using temperature=0.1 with sampling (stochastic)
2. No confidence intervals
3. No statistical significance testing

Changes needed:
```python
# In evaluate_stage1.py and baseline_assessment.py:
outputs = model.generate(
    input_ids,
    max_new_tokens=100,
    do_sample=False,  # Deterministic
    temperature=None,  # Not used with do_sample=False
    pad_token_id=tokenizer.pad_token_id
)

# In utils/metrics.py, add:
def calculate_wilson_ci(successes, total, confidence=0.95):
    """Calculate Wilson confidence interval for proportion"""
    from scipy import stats
    p_hat = successes / total
    z = stats.norm.ppf((1 + confidence) / 2)
    denominator = 1 + z**2 / total
    center = (p_hat + z**2 / (2 * total)) / denominator
    margin = z * np.sqrt((p_hat * (1 - p_hat) + z**2 / (4 * total)) / total) / denominator
    return (center - margin, center + margin)

def mcnemar_test(base_results, trained_results):
    """Paired test for model comparison"""
    # Implementation here
    pass
```

## Test Plan
1. Run evaluation twice with same inputs - should get identical results
2. Verify confidence intervals are reasonable width
3. Check p-values are calculated correctly
4. Ensure results JSON includes all statistical metrics

---

## Status Updates
[Claude Code adds updates here]
