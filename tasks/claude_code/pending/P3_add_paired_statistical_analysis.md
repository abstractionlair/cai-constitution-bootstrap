# P3: Add Paired Statistical Analysis

**Source:** Codex Pre-Deployment Review (2025-09-11)
**Priority:** P3 (Low - post-deployment enhancement)
**Estimated Time:** 1-2 hours

## Issue Description

The evaluation computes success rates but does not run McNemar's test, confidence intervals, or bootstrap analysis. This limits publication-grade statistical claims.

## Location

- Create new file: `scripts/analysis/stage1_stats.py`
- Read from: `results/stage1_evaluation_*.json`

## Suggested Implementation

Create a statistical analysis script that:
1. Loads the latest evaluation JSON
2. Computes McNemar's p-value for paired comparisons
3. Calculates Wilson confidence intervals
4. Reports Cohen's h effect size
5. Provides bootstrap CIs overall and by instruction type

## Impact

Needed for publication-quality results but not blocking deployment.

## Success Criteria

- [ ] Statistical analysis script created
- [ ] McNemar's test implemented
- [ ] Confidence intervals calculated
- [ ] Results formatted for publication