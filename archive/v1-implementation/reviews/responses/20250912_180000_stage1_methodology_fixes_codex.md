# Codex Review Response: Stage 1 Methodology After Fixes
Date: 2025-09-12
Request File: 20250912_180000_stage1_methodology_fixes.md

## Methodology Assessment
1. HIGH: Adding DPO-only establishes a proper ablation; ensure identical preference data and matched hyperparameters to isolate the SFT contribution.
2. HIGH: Using real base-model generations for SFT resolves the placeholder confound; document sampling, temperature, and decoding to ensure replicability.
3. MEDIUM: Four-way comparison (Base, SFT, DPO-only, SFT→DPO) is scientifically sound; pre-register primary endpoints to avoid garden-of-forking-paths.
4. MEDIUM: Current evaluation size (130 prompts) is underpowered for modest effects; acceptable for MVP gates but not for strong claims.
5. MEDIUM: Loss masking and data validation controls are appropriate; add a small ablation (SFT unmasked) if compute permits.
6. LOW: Sequential evaluation and consistent tokenization reduce confounds; include model and tokenizer checksum logging.

## Scientific Validity
- ✅ Baselines now include DPO-only and SFT-only components implicitly via the four-model setup.
- ✅ Controls for tokenization, loss masking, and data formatting are described and appear sufficient.
- ✅ Evaluation script for 4-model comparison exists (`scripts/evaluate_stage1_comprehensive.py`).
- ❌ Power analysis and multiple-comparison control not yet specified in the protocol.
- ❌ Single test set of 130 prompts risks high variance; no mention of category stratification or multiple seeds.
- ⚠️ Negative sampling is diverse; confirm it mirrors observed failure distribution or include a sensitivity check (uniform vs heuristic).

## Statistical Concerns
- Test design: Use paired analyses across the same prompts for all models.
  - Binary criteria (e.g., ends_with_end, addresses_instruction): McNemar’s test; report Cohen’s h and 95% Wilson CIs per model.
  - Ordinal/LLM-judge scores (if any): Wilcoxon signed-rank with Cliff’s delta.
  - Pairwise win rates (if evaluated via judge): Binomial exact tests with Agresti–Coull CIs; consider a Bradley–Terry model for overall ranking.
- Multiple comparisons: 9 criteria × 6 pairwise model contrasts → control FDR via Benjamini–Hochberg (q=0.05–0.10). Report both raw and adjusted p-values.
- Power: With n=130, detecting a 10 percentage-point paired improvement at α=0.05 yields limited power (<0.6 typical). Target n≥350–400 for Δ≈10pp; n≈1,000 for Δ≈5pp.
- Uncertainty: Provide bootstrap BCa CIs (stratify by instruction category/length) for aggregate metrics; report seed-to-seed variance if multiple runs are made.

## Recommendations
- Protocol
  - Pre-register two primary endpoints: `addresses_instruction` and `proper_structure`; treat others as secondary with FDR control.
  - Fix decoding parameters for all generations (temperature, top_p, max_tokens) and log them; store prompt/response hashes.
  - Ensure identical preference pairs for DPO-only and SFT→DPO; log β, LR, batch size, and training steps.
- Sample Size
  - For RunPod MVP, proceed with 130 tests but plan to scale to ≥400 for confirmatory results.
  - If compute allows, evaluate on two disjoint 130-prompt folds to estimate variance.
- Negatives
  - Run a sensitivity ablation: heuristic mixture vs uniform distribution across 5 negative types; report per-type gains.
  - Track “meaningful negative rate” and exclude degenerate negatives from training/eval.
- Reproducibility
  - Log seeds for data gen, SFT, and DPO; capture git SHA and model/tokenizer checksums.
  - Freeze and version datasets; add dedup/leakage checks between train and test sets.
- Reporting
  - Provide per-model metric table with point estimates, 95% CIs, and adjusted p-values.
  - Include an overall ranking (Elo or Bradley–Terry) and a calibration plot for refusals vs format compliance.

## Go/No-Go
- Go for RunPod MVP execution with the current four-model design, contingent on:
  - Using paired tests with FDR control in analysis.
  - Logging seeds/configs and freezing datasets.
  - Reporting effect sizes with 95% CIs and clearly labeling results as preliminary due to small n.
- No-Go for publication-level claims until evaluation is scaled (≥400–1,000 prompts), ablations are run, and multiple seeds are included.

## Notes on File Checks
- Referenced scripts exist: `train_stage1_sft.py`, `train_stage1_dpo_improved.py`, `train_stage1_dpo_only.py`, `evaluate_stage1_comprehensive.py`, `generate_stage1_sft_data.py`, `generate_diverse_negatives.py`.
- Please ensure parity of hyperparameters between DPO-only and SFT→DPO in `train_stage1_dpo_only.py` vs `train_stage1_dpo_improved.py` (β, LR, batch size, steps, preference set).

## Final Verdict
Methodology after fixes substantially strengthens the causal argument for SFT→DPO over DPO-only. The design is now scientifically defensible for an MVP run, provided the analysis includes paired significance tests, FDR control, and effect sizes. Scale evaluation for robust claims.
