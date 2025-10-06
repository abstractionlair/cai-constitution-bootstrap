# Review Response: P0 Infrastructure Complete - Ready for GPU Production

**Reviewer**: codex
**Date**: 2025-10-04
**Request**: 20251004_p0_infrastructure_ready.md

## Summary
✅ Approved with minor notes

- Statistical utilities and provenance helpers look solid and align with publication-quality requirements for paired binary evaluations. Add a small enhancement for exact McNemar at low discordant counts and clarify one summary metric. Provenance coverage is strong; suggest adding dataset/checksum fields and a tiny helper to append to the session manifest.

## Issues Found

### ⚠️ HIGH
1. Exact McNemar option missing for low discordant pairs
   - File: `scripts/utils/eval_statistics.py:20` (mcnemar_test)
   - Description: Implementation uses χ² with continuity correction (good default) but does not offer an exact binomial alternative when `n01 + n10` is small (e.g., <25) or extremely imbalanced.
   - Impact: For rare per-type buckets, asymptotic p-values can be slightly miscalibrated; reviewers may expect exact tests.
   - Recommendation: Add `method="auto|exact|chi2"` with exact using binomial test on min(n01, n10) with n=n01+n10. Use `auto` to select exact when n_discordant < 25.

### 💡 SUGGESTIONS
1. “Raw significant” count semantics under BH
   - File: `scripts/utils/eval_statistics.py:474`
   - Description: `n_significant_raw` currently counts raw p-values < FDR (e.g., p<0.10). That threshold does not correspond to a family-wise decision rule and can confuse readers.
   - Recommendation: Either (a) report `n_raw_p_lt_0_05` alongside BH results, or (b) compute per-rank BH thresholds and count raw rejections at those cutpoints. Clarify naming in output.

2. Bootstrap method note and cost control
   - File: `scripts/utils/eval_statistics.py:241`
   - Suggestion: Document that percentile bootstrap is used; note option to reduce `n_bootstrap` for speed during smoke tests and increase for final analysis. If time allows later, consider BCa.

3. Provenance: dataset/held-out checksums and artifact linkage
   - File: `scripts/utils/provenance_helper.py:96`
   - Suggestion: Add optional fields in `create_artifact_metadata()` for `dataset_id`, `heldout_checksum`, and `artifact_parent_ids`. Encourages explicit linkage and leakage checks.

4. Session manifest append helper
   - Files: `scripts/utils/provenance_helper.py`, `scripts/create_session_manifest.py`
   - Suggestion: Provide `append_artifact_to_manifest(path, session_id)` that loads `session_manifest_{session_id}.json`, appends to `artifacts_generated`, and saves. Keeps updates consistent across scripts.

5. Requirements pinning guidance
   - Files: `requirements.txt`, `requirements-dev.txt`
   - Suggestion: Pin upper/lower bounds for critical libs (`torch`, `transformers`, `numpy`, `scipy`) to minimize drift; note any known-good ranges in docs.

## Verified OK
- eval_statistics
  - McNemar with continuity correction implemented correctly; clean API and docstrings.
  - BH procedure implemented with monotone adjusted p-values; outputs both adjusted p and rejection flags.
  - Cohen’s h formula correct and tested (symmetry, edge cases).
  - Wilson CI implemented with standard form; bounds in [0,1]; tests cover width vs N.
  - Bootstrap CI supports paired resampling with seeding; integration covered.
  - `paired_comparison_analysis()` composes all components sensibly; metadata block records confidence, bootstrap samples, seed.
- tests/test_eval_statistics.py
  - Comprehensive unit tests span known values, edge cases, stratification, metadata preservation, and integration (base→SFT→DPO). Good coverage for correctness.
- provenance_helper
  - Git SHA, branch, dirty state captured; artifact metadata merges loader provenance and script context; API is simple and extensible.
  - Session manifest captures environment, GPU, and planned artifacts; caller fills transformers version (reasonable separation).
- create_session_manifest.py
  - Produces a clear manifest; warnings on dirty git; outputs live in `artifacts/` with predictable naming.

## Recommendations
1. Add exact McNemar path (method="auto") for small discordant counts; keep χ²+continuity as default for typical N.
2. Clarify `n_significant_raw` semantics or switch to a more interpretable raw count (e.g., p<0.05) alongside BH-adjusted outcomes.
3. Extend provenance to include dataset IDs/hashes and held-out checksum; integrate a tiny helper to update `artifacts_generated` in the session manifest.
4. Provide quick-start examples showing how eval scripts embed statistics output and metadata into their JSONs (one snippet per major script family: baseline, SFT, DPO).
5. For production runs, standardize deterministic decoding for baselines (temperature=0) and log decoding parameters in metadata; if sampling used, ensure seeds and params are recorded.

## Overall Assessment
Approved to proceed. The statistical toolkit and provenance framework meet publication-quality needs for Stage 1. Add the small exact-McNemar enhancement and clarify the BH “raw” summary when convenient; neither should block GPU production. Ensure downstream scripts persist the new metadata and statistical outputs as designed.

