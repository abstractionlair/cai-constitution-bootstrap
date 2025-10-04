#!/usr/bin/env python3
"""
Statistical analysis utilities for Constitutional AI evaluation.

Provides publication-quality statistical tests, effect sizes, and confidence
intervals for paired binary outcomes (base vs SFT vs DPO comparisons).

Key functions:
- mcnemar_test: Paired binary outcome test
- benjamini_hochberg: Multiple testing correction (FDR control)
- cohens_h: Effect size for proportion differences
- wilson_ci: Confidence interval for proportions
- bootstrap_ci: Bootstrap CI for arbitrary statistics
- paired_comparison_analysis: Complete analysis pipeline

Statistical guarantees:
- McNemar test: Exact test for paired binary data (continuity correction)
- Benjamini-Hochberg: FDR ≤ α (typically α=0.10)
- Wilson CI: Better coverage than normal approximation
- Bootstrap CI: Percentile method, bias-corrected if requested

References:
- McNemar (1947): Note on the sampling error of the difference between correlated proportions
- Benjamini & Hochberg (1995): Controlling the false discovery rate
- Cohen (1988): Statistical Power Analysis for the Behavioral Sciences
- Wilson (1927): Probable inference, the law of succession, and statistical inference
"""

import numpy as np
from scipy import stats
from typing import Dict, List, Tuple, Optional, Callable, Any
import warnings


def mcnemar_test(n01: int, n10: int, continuity: bool = True) -> Tuple[float, float]:
    """
    McNemar test for paired binary outcomes.

    Tests whether marginal proportions differ for paired data:
    - H0: P(success | model1) = P(success | model2)
    - H1: P(success | model1) ≠ P(success | model2)

    Only considers discordant pairs (where models disagree):
    - n01: Model1 failed, Model2 succeeded
    - n10: Model1 succeeded, Model2 failed

    Concordant pairs (both succeed or both fail) provide no information.

    Formula (with continuity correction):
        χ² = (|n01 - n10| - 1)² / (n01 + n10)
        df = 1

    Args:
        n01: Count of (model1=0, model2=1) - model2 wins
        n10: Count of (model1=1, model2=0) - model1 wins
        continuity: Apply continuity correction (default True)

    Returns:
        (chi2, p_value)

    Example:
        >>> # Base model: 15% success, SFT: 78% success, N=1000
        >>> # Discordant: 630 where SFT succeeds but base fails
        >>> #             0 where base succeeds but SFT fails
        >>> chi2, p = mcnemar_test(n01=630, n10=0)
        >>> print(f"χ²={chi2:.2f}, p={p:.2e}")  # Highly significant
    """
    n_discordant = n01 + n10

    if n_discordant == 0:
        # No discordant pairs = models always agree
        warnings.warn("No discordant pairs found. Models have identical predictions.")
        return 0.0, 1.0

    if continuity:
        # Continuity correction for better approximation to chi-squared distribution
        # Recommended for small counts (n01 + n10 < 25)
        chi2 = (abs(n01 - n10) - 1) ** 2 / n_discordant
    else:
        chi2 = (n01 - n10) ** 2 / n_discordant

    # Chi-squared distribution with df=1
    p_value = 1 - stats.chi2.cdf(chi2, df=1)

    return chi2, p_value


def benjamini_hochberg(
    p_values: List[float],
    fdr: float = 0.10
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Benjamini-Hochberg procedure for controlling false discovery rate.

    Controls the expected proportion of false positives among rejections.
    Less conservative than Bonferroni (which controls family-wise error rate).

    Procedure:
    1. Order p-values: p(1) ≤ p(2) ≤ ... ≤ p(m)
    2. Find largest i where p(i) ≤ (i/m) * FDR
    3. Reject H(1), ..., H(i)
    4. Adjusted p-value: min(p(j) * m/j for j >= i)

    Args:
        p_values: List of raw p-values from multiple tests
        fdr: False discovery rate threshold (default 0.10 = 10%)

    Returns:
        (adjusted_p_values, rejections)
        - adjusted_p_values: Array of BH-adjusted p-values
        - rejections: Boolean array (True = reject null hypothesis)

    Example:
        >>> p_vals = [0.001, 0.004, 0.03, 0.08, 0.15, 0.20]
        >>> adj_p, reject = benjamini_hochberg(p_vals, fdr=0.10)
        >>> print(f"Reject: {reject}")  # [True, True, True, True, False, False]
    """
    p_values = np.array(p_values)
    m = len(p_values)

    if m == 0:
        return np.array([]), np.array([], dtype=bool)

    # Sort p-values and track original indices
    sorted_indices = np.argsort(p_values)
    sorted_p = p_values[sorted_indices]

    # Compute BH thresholds: (i/m) * FDR for i=1..m
    thresholds = np.arange(1, m + 1) / m * fdr

    # Find largest i where p(i) <= threshold(i)
    comparisons = sorted_p <= thresholds
    if comparisons.any():
        # Reject all hypotheses up to and including this index
        max_idx = np.where(comparisons)[0][-1]
        rejections_sorted = np.zeros(m, dtype=bool)
        rejections_sorted[:max_idx + 1] = True
    else:
        # No rejections
        rejections_sorted = np.zeros(m, dtype=bool)

    # Compute adjusted p-values (step-down procedure)
    # adj_p(i) = min_j>=i (p(j) * m / j)
    adjusted_p_sorted = np.zeros(m)
    adjusted_p_sorted[-1] = sorted_p[-1]
    for i in range(m - 2, -1, -1):
        adjusted_p_sorted[i] = min(
            sorted_p[i] * m / (i + 1),
            adjusted_p_sorted[i + 1]
        )

    # Clip to [0, 1] (can exceed 1 due to correction)
    adjusted_p_sorted = np.clip(adjusted_p_sorted, 0, 1)

    # Unsort to match original order
    adjusted_p = np.zeros(m)
    rejections = np.zeros(m, dtype=bool)
    adjusted_p[sorted_indices] = adjusted_p_sorted
    rejections[sorted_indices] = rejections_sorted

    return adjusted_p, rejections


def cohens_h(p1: float, p2: float) -> float:
    """
    Cohen's h effect size for difference between two proportions.

    Measures effect size in units of arcsine-transformed proportions.
    Symmetric: h(p1, p2) = -h(p2, p1)

    Formula:
        h = 2 * (arcsin(√p1) - arcsin(√p2))

    Interpretation:
        |h| < 0.2:  Small effect
        |h| ≈ 0.5:  Medium effect
        |h| ≥ 0.8:  Large effect

    Args:
        p1: Proportion 1 (e.g., base model success rate)
        p2: Proportion 2 (e.g., SFT model success rate)

    Returns:
        h (effect size, can be negative)

    Example:
        >>> h = cohens_h(0.15, 0.78)  # Base 15% → SFT 78%
        >>> print(f"h = {h:.2f}")  # h ≈ 1.45 (very large effect)
    """
    # Arcsine transformation stabilizes variance for proportions
    # Clamp to [0, 1] to handle floating-point errors
    p1 = np.clip(p1, 0, 1)
    p2 = np.clip(p2, 0, 1)

    h = 2 * (np.arcsin(np.sqrt(p1)) - np.arcsin(np.sqrt(p2)))
    return h


def wilson_ci(
    successes: int,
    n: int,
    confidence: float = 0.95
) -> Tuple[float, float]:
    """
    Wilson score confidence interval for a proportion.

    More accurate than normal approximation, especially for:
    - Small sample sizes
    - Proportions near 0 or 1
    - Guarantees CI stays in [0, 1]

    Formula (using z-score for confidence level):
        center = (x + z²/2) / (n + z²)
        margin = z * sqrt((x(n-x)/n + z²/4) / (n + z²))
        CI = (center - margin, center + margin)

    Args:
        successes: Number of successes
        n: Total number of trials
        confidence: Confidence level (default 0.95 for 95% CI)

    Returns:
        (lower, upper) bounds of confidence interval

    Example:
        >>> lower, upper = wilson_ci(successes=780, n=1000)
        >>> print(f"95% CI: [{lower:.3f}, {upper:.3f}]")  # [0.753, 0.805]
    """
    if n == 0:
        return 0.0, 0.0

    # Z-score for confidence level (e.g., 1.96 for 95%)
    z = stats.norm.ppf((1 + confidence) / 2)

    p = successes / n

    # Wilson score interval
    denominator = n + z**2
    center = (successes + z**2 / 2) / denominator
    margin = z * np.sqrt((p * (1 - p) / n + z**2 / (4 * n**2)) * n / denominator)

    lower = center - margin
    upper = center + margin

    # Clamp to [0, 1] (should be guaranteed by formula, but floating-point safety)
    lower = max(0.0, lower)
    upper = min(1.0, upper)

    return lower, upper


def bootstrap_ci(
    data1: np.ndarray,
    data2: np.ndarray,
    func: Callable[[np.ndarray, np.ndarray], float],
    n_bootstrap: int = 10000,
    confidence: float = 0.95,
    random_seed: Optional[int] = None
) -> Tuple[float, float]:
    """
    Bootstrap confidence interval for arbitrary statistic of paired data.

    Uses percentile method with paired resampling (samples with replacement
    while maintaining pairing structure).

    Useful for statistics without closed-form CIs (e.g., lift = p2 - p1).

    Args:
        data1: Array of binary outcomes for model 1 (0 or 1)
        data2: Array of binary outcomes for model 2 (0 or 1)
        func: Statistic function (data1, data2) -> float
              Example: lambda d1, d2: d2.mean() - d1.mean()  # lift
        n_bootstrap: Number of bootstrap samples (default 10000)
        confidence: Confidence level (default 0.95)
        random_seed: Random seed for reproducibility (optional)

    Returns:
        (lower, upper) bounds of confidence interval

    Example:
        >>> base = np.array([0, 0, 1, 0, ...])  # N=1000
        >>> sft = np.array([1, 1, 1, 0, ...])   # N=1000
        >>> lift_func = lambda d1, d2: d2.mean() - d1.mean()
        >>> lower, upper = bootstrap_ci(base, sft, lift_func)
        >>> print(f"Lift 95% CI: [{lower:.3f}, {upper:.3f}]")
    """
    data1 = np.array(data1)
    data2 = np.array(data2)

    if len(data1) != len(data2):
        raise ValueError(f"Data arrays must have same length: {len(data1)} vs {len(data2)}")

    n = len(data1)

    if random_seed is not None:
        rng = np.random.RandomState(random_seed)
    else:
        rng = np.random.RandomState()

    # Bootstrap sampling (with replacement, preserving pairing)
    bootstrap_stats = []
    for _ in range(n_bootstrap):
        indices = rng.choice(n, size=n, replace=True)
        sample1 = data1[indices]
        sample2 = data2[indices]
        stat = func(sample1, sample2)
        bootstrap_stats.append(stat)

    bootstrap_stats = np.array(bootstrap_stats)

    # Percentile method
    alpha = 1 - confidence
    lower = np.percentile(bootstrap_stats, 100 * alpha / 2)
    upper = np.percentile(bootstrap_stats, 100 * (1 - alpha / 2))

    return lower, upper


def paired_comparison_analysis(
    model1_results: np.ndarray,
    model2_results: np.ndarray,
    labels: Tuple[str, str],
    instruction_types: Optional[np.ndarray] = None,
    fdr: float = 0.10,
    confidence: float = 0.95,
    bootstrap_samples: int = 10000,
    random_seed: Optional[int] = None
) -> Dict[str, Any]:
    """
    Complete paired comparison analysis with tests, corrections, effect sizes, CIs.

    Performs:
    1. Overall analysis (all examples pooled)
    2. Per-type analysis (stratified by instruction type)
    3. Multiple testing correction (Benjamini-Hochberg across types)

    For each comparison:
    - Success rates with Wilson CIs
    - McNemar test for significance
    - Cohen's h effect size
    - Bootstrap CI for lift (difference in rates)

    Args:
        model1_results: Binary array (0=fail, 1=success) for model 1
        model2_results: Binary array (0=fail, 1=success) for model 2
        labels: (model1_name, model2_name) for output
        instruction_types: Optional array of types for stratification
        fdr: False discovery rate for BH correction (default 0.10)
        confidence: Confidence level for CIs (default 0.95)
        bootstrap_samples: Number of bootstrap samples for lift CI
        random_seed: Random seed for bootstrap reproducibility

    Returns:
        Dictionary with structure:
        {
            'overall': {
                'n': int,
                'model1_rate': float,
                'model1_ci': [float, float],
                'model2_rate': float,
                'model2_ci': [float, float],
                'lift': float,
                'lift_ci_bootstrap': [float, float],
                'mcnemar_chi2': float,
                'mcnemar_p': float,
                'cohens_h': float,
                'discordant_pairs': {'n01': int, 'n10': int}
            },
            'by_type': {
                '<type>': {
                    ... (same as overall, plus p_adjusted)
                }
            },
            'bh_correction': {
                'fdr': float,
                'n_tests': int,
                'n_significant_raw': int,
                'n_significant_adjusted': int
            },
            'metadata': {
                'labels': [str, str],
                'confidence_level': float,
                'bootstrap_samples': int,
                'random_seed': int or None
            }
        }

    Example:
        >>> base = np.array([0, 0, 1, ...])  # N=1000
        >>> sft = np.array([1, 1, 1, ...])   # N=1000
        >>> types = np.array(['list', 'list', 'count', ...])
        >>>
        >>> analysis = paired_comparison_analysis(
        ...     base, sft, labels=('base', 'sft'),
        ...     instruction_types=types, fdr=0.10
        ... )
        >>>
        >>> print(f"Overall lift: {analysis['overall']['lift']:.3f}")
        >>> print(f"p-value: {analysis['overall']['mcnemar_p']:.2e}")
        >>> print(f"Effect size: {analysis['overall']['cohens_h']:.2f}")
    """
    model1_results = np.array(model1_results)
    model2_results = np.array(model2_results)

    if len(model1_results) != len(model2_results):
        raise ValueError(
            f"Result arrays must have same length: "
            f"{len(model1_results)} vs {len(model2_results)}"
        )

    n_total = len(model1_results)
    model1_name, model2_name = labels

    def analyze_subset(m1_res, m2_res):
        """Analyze a subset of results (overall or per-type)."""
        n = len(m1_res)

        # Success rates
        m1_successes = int(m1_res.sum())
        m2_successes = int(m2_res.sum())
        m1_rate = m1_successes / n if n > 0 else 0.0
        m2_rate = m2_successes / n if n > 0 else 0.0

        # Wilson CIs for proportions
        m1_ci = wilson_ci(m1_successes, n, confidence)
        m2_ci = wilson_ci(m2_successes, n, confidence)

        # Lift (difference in rates)
        lift = m2_rate - m1_rate

        # Bootstrap CI for lift
        if n > 0:
            lift_func = lambda d1, d2: d2.mean() - d1.mean()
            lift_ci = bootstrap_ci(
                m1_res, m2_res, lift_func,
                n_bootstrap=bootstrap_samples,
                confidence=confidence,
                random_seed=random_seed
            )
        else:
            lift_ci = (0.0, 0.0)

        # Discordant pairs for McNemar
        n01 = int(((m1_res == 0) & (m2_res == 1)).sum())  # Model2 wins
        n10 = int(((m1_res == 1) & (m2_res == 0)).sum())  # Model1 wins

        # McNemar test
        if n > 0:
            chi2, p_val = mcnemar_test(n01, n10, continuity=True)
        else:
            chi2, p_val = 0.0, 1.0

        # Cohen's h effect size
        h = cohens_h(m1_rate, m2_rate)

        return {
            'n': n,
            f'{model1_name}_rate': m1_rate,
            f'{model1_name}_successes': m1_successes,
            f'{model1_name}_ci': list(m1_ci),
            f'{model2_name}_rate': m2_rate,
            f'{model2_name}_successes': m2_successes,
            f'{model2_name}_ci': list(m2_ci),
            'lift': lift,
            'lift_ci_bootstrap': list(lift_ci),
            'mcnemar_chi2': chi2,
            'mcnemar_p': p_val,
            'cohens_h': h,
            'discordant_pairs': {'n01': n01, 'n10': n10}
        }

    # Overall analysis
    overall = analyze_subset(model1_results, model2_results)

    # Per-type analysis (if types provided)
    by_type = {}
    p_values_by_type = []
    type_names = []

    if instruction_types is not None:
        instruction_types = np.array(instruction_types)
        if len(instruction_types) != n_total:
            raise ValueError(
                f"instruction_types length ({len(instruction_types)}) "
                f"must match results length ({n_total})"
            )

        unique_types = np.unique(instruction_types)

        for itype in unique_types:
            mask = instruction_types == itype
            m1_subset = model1_results[mask]
            m2_subset = model2_results[mask]

            by_type[itype] = analyze_subset(m1_subset, m2_subset)
            p_values_by_type.append(by_type[itype]['mcnemar_p'])
            type_names.append(itype)

    # Benjamini-Hochberg correction across types
    bh_correction_info = {
        'fdr': fdr,
        'n_tests': len(p_values_by_type),
        'n_significant_raw': 0,
        'n_significant_adjusted': 0
    }

    if p_values_by_type:
        adjusted_p, rejections = benjamini_hochberg(p_values_by_type, fdr)

        bh_correction_info['n_significant_raw'] = int(
            (np.array(p_values_by_type) < fdr).sum()
        )
        bh_correction_info['n_significant_adjusted'] = int(rejections.sum())

        # Add adjusted p-values and rejection flags to by_type results
        for itype, adj_p, reject in zip(type_names, adjusted_p, rejections):
            by_type[itype]['mcnemar_p_adjusted'] = float(adj_p)
            by_type[itype]['significant_after_bh'] = bool(reject)

    # Assemble output
    result = {
        'overall': overall,
        'by_type': by_type,
        'bh_correction': bh_correction_info,
        'metadata': {
            'labels': list(labels),
            'confidence_level': confidence,
            'bootstrap_samples': bootstrap_samples,
            'random_seed': random_seed
        }
    }

    return result


# Helper function for pretty-printing results (optional, for debugging)
def format_comparison_results(analysis: Dict[str, Any]) -> str:
    """
    Format paired comparison analysis results for human reading.

    Args:
        analysis: Output from paired_comparison_analysis()

    Returns:
        Formatted string with key statistics
    """
    model1_name = analysis['metadata']['labels'][0]
    model2_name = analysis['metadata']['labels'][1]

    lines = []
    lines.append(f"Paired Comparison: {model1_name} vs {model2_name}")
    lines.append("=" * 60)

    # Overall
    overall = analysis['overall']
    lines.append("\nOverall:")
    lines.append(f"  N = {overall['n']}")
    lines.append(
        f"  {model1_name}: {overall[f'{model1_name}_rate']:.3f} "
        f"(95% CI: [{overall[f'{model1_name}_ci'][0]:.3f}, {overall[f'{model1_name}_ci'][1]:.3f}])"
    )
    lines.append(
        f"  {model2_name}: {overall[f'{model2_name}_rate']:.3f} "
        f"(95% CI: [{overall[f'{model2_name}_ci'][0]:.3f}, {overall[f'{model2_name}_ci'][1]:.3f}])"
    )
    lines.append(
        f"  Lift: {overall['lift']:.3f} "
        f"(95% CI: [{overall['lift_ci_bootstrap'][0]:.3f}, {overall['lift_ci_bootstrap'][1]:.3f}])"
    )
    lines.append(f"  McNemar: χ²={overall['mcnemar_chi2']:.2f}, p={overall['mcnemar_p']:.2e}")
    lines.append(f"  Cohen's h: {overall['cohens_h']:.2f}")

    # By type (if present)
    if analysis['by_type']:
        lines.append(f"\nBy Instruction Type (FDR={analysis['bh_correction']['fdr']}):")
        for itype, stats in analysis['by_type'].items():
            sig_marker = "***" if stats.get('significant_after_bh', False) else ""
            lines.append(f"\n  {itype} (N={stats['n']}) {sig_marker}:")
            lines.append(f"    Lift: {stats['lift']:.3f}, h={stats['cohens_h']:.2f}")
            lines.append(
                f"    McNemar: p={stats['mcnemar_p']:.2e}, "
                f"p_adj={stats.get('mcnemar_p_adjusted', 'N/A'):.2e}"
            )

    # BH summary
    bh = analysis['bh_correction']
    if bh['n_tests'] > 0:
        lines.append(
            f"\nBenjamini-Hochberg Correction: "
            f"{bh['n_significant_adjusted']}/{bh['n_tests']} significant "
            f"after correction (FDR={bh['fdr']})"
        )

    return "\n".join(lines)


if __name__ == "__main__":
    # Quick test/demo
    print("eval_statistics.py - Statistical analysis for Constitutional AI evaluation")
    print()

    # Simulate base vs SFT comparison (N=1000)
    np.random.seed(42)
    n = 1000

    # Base model: 15% success rate
    base_results = np.random.binomial(1, 0.15, size=n)

    # SFT model: 78% success rate (correlated with base)
    sft_results = np.zeros(n)
    for i in range(n):
        if base_results[i] == 1:
            # If base succeeded, SFT succeeds with high probability
            sft_results[i] = np.random.binomial(1, 0.95)
        else:
            # If base failed, SFT succeeds with moderate probability
            sft_results[i] = np.random.binomial(1, 0.74)

    # Instruction types (stratified)
    types = np.random.choice(['list', 'count', 'sort', 'filter'], size=n, p=[0.3, 0.3, 0.2, 0.2])

    # Run analysis
    print("Running paired comparison analysis...")
    analysis = paired_comparison_analysis(
        base_results, sft_results,
        labels=('base', 'sft'),
        instruction_types=types,
        fdr=0.10,
        random_seed=42
    )

    # Print formatted results
    print(format_comparison_results(analysis))
    print()
    print("Test complete. Use this module in evaluation scripts.")
