#!/usr/bin/env python3
"""
Unit tests for eval_statistics.py

Tests statistical functions against known values and scipy/statsmodels where applicable.
"""

import sys
import os
import unittest
import numpy as np
from scipy import stats

# Add scripts/utils to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts', 'utils'))

from eval_statistics import (
    mcnemar_test,
    benjamini_hochberg,
    cohens_h,
    wilson_ci,
    bootstrap_ci,
    paired_comparison_analysis
)


class TestMcNemarTest(unittest.TestCase):
    """Test McNemar test implementation."""

    def test_known_values(self):
        """Test against hand-calculated values."""
        # Example from McNemar (1947)
        # Discordant pairs: n01=10, n10=2
        # χ² = (|10 - 2| - 1)² / (10 + 2) = 49 / 12 = 4.083
        chi2, p = mcnemar_test(n01=10, n10=2, continuity=True)
        self.assertAlmostEqual(chi2, 4.083, places=3)
        self.assertLess(p, 0.05)  # Significant at α=0.05

    def test_no_discordant_pairs(self):
        """Test when models always agree."""
        chi2, p = mcnemar_test(n01=0, n10=0)
        self.assertEqual(chi2, 0.0)
        self.assertEqual(p, 1.0)

    def test_one_sided_discordance(self):
        """Test when only one model ever wins."""
        # Model 2 always wins disagreements
        chi2, p = mcnemar_test(n01=100, n10=0, continuity=True)
        self.assertGreater(chi2, 90)  # Very large chi2
        self.assertLess(p, 1e-20)  # Extremely significant

    def test_symmetric(self):
        """Test equal discordant pairs (no difference)."""
        # Equal wins each way = no significant difference
        chi2, p = mcnemar_test(n01=50, n10=50, continuity=True)
        self.assertLess(chi2, 0.1)  # Near zero
        self.assertGreater(p, 0.5)  # Not significant

    def test_continuity_correction(self):
        """Test with and without continuity correction."""
        n01, n10 = 15, 5
        chi2_with, _ = mcnemar_test(n01, n10, continuity=True)
        chi2_without, _ = mcnemar_test(n01, n10, continuity=False)
        # With correction should be smaller (more conservative)
        self.assertLess(chi2_with, chi2_without)


class TestBenjaminiHochberg(unittest.TestCase):
    """Test Benjamini-Hochberg correction."""

    def test_all_significant(self):
        """Test when all p-values should be rejected."""
        p_vals = [0.001, 0.002, 0.003, 0.004]
        adj_p, reject = benjamini_hochberg(p_vals, fdr=0.10)
        self.assertTrue(reject.all())

    def test_none_significant(self):
        """Test when no p-values should be rejected."""
        p_vals = [0.5, 0.6, 0.7, 0.8]
        adj_p, reject = benjamini_hochberg(p_vals, fdr=0.10)
        self.assertFalse(reject.any())

    def test_partial_rejection(self):
        """Test mixed case (some rejected, some not)."""
        # From Benjamini & Hochberg (1995) example
        p_vals = [0.01, 0.04, 0.03, 0.005, 0.1, 0.2]
        adj_p, reject = benjamini_hochberg(p_vals, fdr=0.10)
        # At FDR=0.10, expect first few to be rejected
        self.assertTrue(reject[3])  # p=0.005 should be rejected
        self.assertTrue(reject[0])  # p=0.01 should be rejected
        self.assertFalse(reject[5])  # p=0.2 should not be rejected

    def test_ordering_invariance(self):
        """Test that rejection decision is correct regardless of input order."""
        p_vals = [0.04, 0.01, 0.2, 0.005]
        adj_p1, reject1 = benjamini_hochberg(p_vals, fdr=0.05)

        # Different input order
        p_vals2 = [0.005, 0.01, 0.04, 0.2]
        adj_p2, reject2 = benjamini_hochberg(p_vals2, fdr=0.05)

        # Same p-value should have same rejection decision
        self.assertEqual(reject1[1], reject2[1])  # p=0.01
        self.assertEqual(reject1[3], reject2[0])  # p=0.005

    def test_empty_input(self):
        """Test edge case of empty input."""
        adj_p, reject = benjamini_hochberg([], fdr=0.10)
        self.assertEqual(len(adj_p), 0)
        self.assertEqual(len(reject), 0)

    def test_adjusted_p_bounds(self):
        """Test that adjusted p-values are in [0, 1]."""
        p_vals = [0.001, 0.01, 0.05, 0.1, 0.5]
        adj_p, _ = benjamini_hochberg(p_vals, fdr=0.10)
        self.assertTrue((adj_p >= 0).all())
        self.assertTrue((adj_p <= 1).all())


class TestCohensH(unittest.TestCase):
    """Test Cohen's h effect size."""

    def test_no_difference(self):
        """Test when proportions are equal."""
        h = cohens_h(0.5, 0.5)
        self.assertAlmostEqual(h, 0.0, places=10)

    def test_known_values(self):
        """Test against hand-calculated values."""
        # p1=0.3, p2=0.5
        # h = 2 * (arcsin(sqrt(0.3)) - arcsin(sqrt(0.5)))
        # h ≈ 2 * (0.5754 - 0.7854) ≈ -0.41 (medium effect)
        # Negative because p1 < p2
        h = cohens_h(0.3, 0.5)
        self.assertAlmostEqual(h, -0.41, places=2)

    def test_large_effect(self):
        """Test large effect size (base 15% to SFT 78%)."""
        h = cohens_h(0.15, 0.78)
        # Negative because p1 < p2, but large magnitude
        self.assertLess(h, -0.8)  # Large effect (negative)

    def test_symmetry(self):
        """Test that h(p1, p2) = -h(p2, p1)."""
        h1 = cohens_h(0.3, 0.7)
        h2 = cohens_h(0.7, 0.3)
        self.assertAlmostEqual(h1, -h2, places=10)

    def test_edge_cases(self):
        """Test extreme proportions."""
        # 0% to 100%
        h = cohens_h(0.0, 1.0)
        self.assertAlmostEqual(abs(h), np.pi, places=2)  # Maximum possible

        # 50% to 50%
        h = cohens_h(0.5, 0.5)
        self.assertAlmostEqual(h, 0.0, places=10)


class TestWilsonCI(unittest.TestCase):
    """Test Wilson confidence interval."""

    def test_known_values(self):
        """Test against known good values."""
        # For p=0.78 (78/100), 95% CI
        # Wilson CI ≈ [0.689, 0.853] (verified with R)
        successes = 78
        n = 100
        lower, upper = wilson_ci(successes, n, confidence=0.95)

        # Check approximate values
        self.assertGreater(lower, 0.68)
        self.assertLess(lower, 0.70)
        self.assertGreater(upper, 0.84)
        self.assertLess(upper, 0.86)

    def test_bounds(self):
        """Test that CI stays in [0, 1]."""
        # Extreme cases
        for successes in [0, 1, 50, 99, 100]:
            lower, upper = wilson_ci(successes, 100, confidence=0.95)
            self.assertGreaterEqual(lower, 0.0)
            self.assertLessEqual(upper, 1.0)
            self.assertLessEqual(lower, upper)

    def test_width_decreases_with_n(self):
        """Test that CI width decreases as sample size increases."""
        p = 0.5
        ci_100 = wilson_ci(int(50), 100)
        ci_1000 = wilson_ci(int(500), 1000)

        width_100 = ci_100[1] - ci_100[0]
        width_1000 = ci_1000[1] - ci_1000[0]

        self.assertLess(width_1000, width_100)

    def test_empty_sample(self):
        """Test edge case of n=0."""
        lower, upper = wilson_ci(0, 0)
        self.assertEqual(lower, 0.0)
        self.assertEqual(upper, 0.0)


class TestBootstrapCI(unittest.TestCase):
    """Test bootstrap confidence interval."""

    def test_lift_ci(self):
        """Test bootstrap CI for lift (difference in proportions)."""
        np.random.seed(42)
        # Two binomial samples
        data1 = np.random.binomial(1, 0.3, size=1000)
        data2 = np.random.binomial(1, 0.5, size=1000)

        lift_func = lambda d1, d2: d2.mean() - d1.mean()
        lower, upper = bootstrap_ci(
            data1, data2, lift_func,
            n_bootstrap=5000, confidence=0.95, random_seed=42
        )

        # True lift ≈ 0.2, CI should contain it
        true_lift = 0.2
        self.assertLess(lower, true_lift)
        self.assertGreater(upper, true_lift)
        self.assertLess(lower, upper)

    def test_reproducibility(self):
        """Test that results are reproducible with same seed."""
        np.random.seed(42)
        data1 = np.random.binomial(1, 0.4, size=100)
        data2 = np.random.binomial(1, 0.6, size=100)
        func = lambda d1, d2: d2.mean() - d1.mean()

        ci1 = bootstrap_ci(data1, data2, func, n_bootstrap=1000, random_seed=123)
        ci2 = bootstrap_ci(data1, data2, func, n_bootstrap=1000, random_seed=123)

        self.assertAlmostEqual(ci1[0], ci2[0], places=6)
        self.assertAlmostEqual(ci1[1], ci2[1], places=6)

    def test_mismatched_lengths(self):
        """Test error handling for mismatched array lengths."""
        data1 = np.array([1, 0, 1])
        data2 = np.array([1, 0])
        func = lambda d1, d2: d2.mean() - d1.mean()

        with self.assertRaises(ValueError):
            bootstrap_ci(data1, data2, func)


class TestPairedComparisonAnalysis(unittest.TestCase):
    """Test complete paired comparison analysis."""

    def setUp(self):
        """Set up test data."""
        np.random.seed(42)
        self.n = 1000

        # Base model: 15% success
        self.base_results = np.random.binomial(1, 0.15, size=self.n)

        # SFT model: 78% success (correlated)
        self.sft_results = np.zeros(self.n)
        for i in range(self.n):
            if self.base_results[i] == 1:
                self.sft_results[i] = np.random.binomial(1, 0.95)
            else:
                self.sft_results[i] = np.random.binomial(1, 0.74)

        # Instruction types
        self.types = np.random.choice(
            ['list', 'count', 'sort', 'filter'],
            size=self.n,
            p=[0.3, 0.3, 0.2, 0.2]
        )

    def test_overall_analysis(self):
        """Test overall analysis (no stratification)."""
        analysis = paired_comparison_analysis(
            self.base_results, self.sft_results,
            labels=('base', 'sft'),
            random_seed=42
        )

        # Check structure
        self.assertIn('overall', analysis)
        self.assertIn('by_type', analysis)
        self.assertIn('bh_correction', analysis)
        self.assertIn('metadata', analysis)

        # Check overall metrics
        overall = analysis['overall']
        self.assertEqual(overall['n'], self.n)
        self.assertIn('base_rate', overall)
        self.assertIn('sft_rate', overall)
        self.assertIn('lift', overall)
        self.assertIn('mcnemar_chi2', overall)
        self.assertIn('mcnemar_p', overall)
        self.assertIn('cohens_h', overall)

        # Sanity checks
        self.assertGreater(overall['sft_rate'], overall['base_rate'])  # SFT better
        self.assertLess(overall['mcnemar_p'], 0.05)  # Significant difference
        self.assertLess(overall['cohens_h'], -0.5)  # Medium+ effect (negative because base < sft)

    def test_stratified_analysis(self):
        """Test analysis with stratification by instruction type."""
        analysis = paired_comparison_analysis(
            self.base_results, self.sft_results,
            labels=('base', 'sft'),
            instruction_types=self.types,
            fdr=0.10,
            random_seed=42
        )

        # Check by-type results exist
        self.assertEqual(len(analysis['by_type']), 4)  # 4 types
        self.assertIn('list', analysis['by_type'])
        self.assertIn('count', analysis['by_type'])

        # Check BH correction info
        bh = analysis['bh_correction']
        self.assertEqual(bh['n_tests'], 4)
        self.assertEqual(bh['fdr'], 0.10)

        # Check adjusted p-values present
        for itype, stats in analysis['by_type'].items():
            self.assertIn('mcnemar_p_adjusted', stats)
            self.assertIn('significant_after_bh', stats)

    def test_confidence_intervals(self):
        """Test that confidence intervals are present and valid."""
        analysis = paired_comparison_analysis(
            self.base_results, self.sft_results,
            labels=('base', 'sft'),
            random_seed=42
        )

        overall = analysis['overall']

        # Check CIs exist
        self.assertIn('base_ci', overall)
        self.assertIn('sft_ci', overall)
        self.assertIn('lift_ci_bootstrap', overall)

        # Check CI validity
        base_ci = overall['base_ci']
        self.assertLessEqual(base_ci[0], overall['base_rate'])
        self.assertGreaterEqual(base_ci[1], overall['base_rate'])

        sft_ci = overall['sft_ci']
        self.assertLessEqual(sft_ci[0], overall['sft_rate'])
        self.assertGreaterEqual(sft_ci[1], overall['sft_rate'])

    def test_metadata_preservation(self):
        """Test that metadata is correctly preserved."""
        analysis = paired_comparison_analysis(
            self.base_results, self.sft_results,
            labels=('base', 'sft'),
            confidence=0.95,
            bootstrap_samples=5000,
            random_seed=12345
        )

        meta = analysis['metadata']
        self.assertEqual(meta['labels'], ['base', 'sft'])
        self.assertEqual(meta['confidence_level'], 0.95)
        self.assertEqual(meta['bootstrap_samples'], 5000)
        self.assertEqual(meta['random_seed'], 12345)

    def test_mismatched_lengths(self):
        """Test error handling for mismatched result lengths."""
        with self.assertRaises(ValueError):
            paired_comparison_analysis(
                self.base_results[:100],
                self.sft_results,
                labels=('base', 'sft')
            )

    def test_mismatched_types_length(self):
        """Test error handling for mismatched instruction_types length."""
        with self.assertRaises(ValueError):
            paired_comparison_analysis(
                self.base_results,
                self.sft_results,
                labels=('base', 'sft'),
                instruction_types=self.types[:100]  # Wrong length
            )


class TestIntegration(unittest.TestCase):
    """Integration tests for complete workflow."""

    def test_three_way_comparison(self):
        """Test base → SFT → DPO progression."""
        np.random.seed(42)
        n = 500

        # Simulate progression: base (15%) → SFT (70%) → DPO (85%)
        base = np.random.binomial(1, 0.15, size=n)
        sft = np.random.binomial(1, 0.70, size=n)
        dpo = np.random.binomial(1, 0.85, size=n)

        # Analyze base vs SFT
        analysis_1 = paired_comparison_analysis(
            base, sft, labels=('base', 'sft'), random_seed=42
        )

        # Analyze SFT vs DPO
        analysis_2 = paired_comparison_analysis(
            sft, dpo, labels=('sft', 'dpo'), random_seed=42
        )

        # Both should show significant improvements
        self.assertLess(analysis_1['overall']['mcnemar_p'], 0.01)
        self.assertLess(analysis_2['overall']['mcnemar_p'], 0.01)

        # SFT lift > DPO lift (base→SFT is bigger jump)
        lift_1 = analysis_1['overall']['lift']
        lift_2 = analysis_2['overall']['lift']
        self.assertGreater(lift_1, lift_2)


def run_tests():
    """Run all tests."""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
