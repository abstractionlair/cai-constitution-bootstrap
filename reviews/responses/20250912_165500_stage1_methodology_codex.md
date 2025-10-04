# Codex Review Response: Stage 1 Constitutional AI Methodology
Date: 2025-09-12
Request File: 20250912_165500_stage1_methodology.md

## Methodology Assessment
1. HIGH: Two-stage SFT→DPO is reasonable and aligns with literature, but must be validated against a DPO-only baseline starting from the base model and from a lightly SFT-initialized model.
2. HIGH: Negative example mixture ratios are heuristic; distributions should be empirically derived from observed failure modes or tuned via validation, with ablations per category.
3. MEDIUM: The 9 evaluation criteria are sensible but partly overlapping; define precise, automatable rubrics and validate with rater agreement or an LLM-as-judge sanity check.
4. MEDIUM: Sample sizes (200 SFT, 500 prefs) are likely underpowered for publication-level claims on a 32B model; acceptable for MVP pipeline shakedown only.
5. MEDIUM: Loss masking rationale is correct; include a control where SFT masking is ablated (unmasked) to demonstrate its concrete contribution.
6. LOW: “Instruction/Response/END” format is fine; ensure inference uses identical formatting and quantify format sensitivity.
7. LOW: Clarify that Stage 1 establishes instruction following; constitutional principles proper are evaluated in later stages to avoid over-claiming “CAI” at this phase.

## Scientific Validity
- ✅ Clear staged hypothesis: SFT establishes format/following; DPO sharpens preferences.
- ✅ Proper held-out evaluation plan with base vs SFT vs DPO comparisons.
- ✅ Diverse negative types anticipate realistic failure modes.
- ❌ No explicit DPO-only and SFT-only ablations with power/calibration targets.
- ❌ Heuristic negative mix without data-driven justification or tuning.
- ❌ Multiple-comparisons control and effect-size reporting not specified.
- ⚠️ Small N risks noisy estimates; add CIs and seeds for robustness.
- ⚠️ Overlap among criteria (e.g., on_topic vs addresses_instruction) may inflate significance.

## Statistical Concerns
- Design: Use paired tests because all models answer the same prompts.
  - Binary/boolean criteria: McNemar’s test; report Cohen’s h and Wilson CIs per model.
  - Ordinal or LLM-judge scores: Wilcoxon signed-rank; report Cliff’s delta or matched-ranks effect size.
  - Pairwise preferences (wins): Binomial test with 95% Wilson/Agresti–Coull CIs; aggregate with Bradley–Terry or Elo for overall strength estimates.
- Multiple comparisons: 9 criteria × 3 pairwise comparisons → control FDR with Benjamini–Hochberg (q=0.05–0.10) or Holm–Bonferroni if you prefer stronger control.
- Power: Rough guide for two-proportion paired improvement from 0.60→0.70 at α=0.05, power 0.8 typically needs ~350–400 paired prompts; for 0.60→0.65, ~1,000+. Current N (≈200–500) is underpowered for small effects; plan sequential enlargement.
- CIs: Use stratified bootstrap (10k reps) by instruction category/length to stabilize intervals; report BCa intervals alongside point estimates.
- Seeds: Run ≥3 seeds for SFT and DPO or at least multiple preference samplings; report mean±CI and variance across seeds.

## Recommendations
- Baselines/Ablations
  - Add DPO-only from base; SFT-only; SFT (masked) vs SFT (unmasked); DPO β∈{0.1,0.5,1.0}; 1 vs 2 epochs (watch overfitting).
  - Sensitivity to negative mix: uniform vs heuristic vs data-driven (sample actual failure proportions; or simple bandit to upweight hardest negatives).
- Metrics
  - Formalize each of the 9 criteria with deterministic checks: regex for `END`, token-length bounds for verbosity, topicality via cosine similarity (embedding) threshold, factuality via retrieval checks on a small closed-book set, coherence via perplexity delta.
  - Add aggregate score: weighted sum with weights pre-registered; also report unweighted to avoid weight-tuning bias.
  - Include MT-Bench (instruction-following subset) with pairwise LLM-judge and compute win rates + Elo; report uncertainty.
- Statistical Protocol
  - Pre-register primary endpoints: e.g., “addresses_instruction” and “proper_structure” as primaries; others secondary with FDR control.
  - Use paired evaluation set (n≥400 for MVP2; target ≥1,000 for paper). Provide exact power calcs in appendix.
  - Report effect sizes (Cohen’s h, Cliff’s δ) and 95% CIs; avoid sole reliance on p-values.
- Data/Process
  - Freeze and hash datasets; log prompt IDs; enforce strict train/val/test splits with leakage checks (n-gram overlap >0.9, deduping).
  - Record config/versioning: git SHA, model checksum, tokenizer version, random seeds.
  - Automate negative generation sanity checks with spot audits; measure “meaningful critique/negative” rate.
- Cost/Automation
  - Track human interventions/time per 100 samples; report automation ratio (#auto artifacts / total) and wall-clock throughput.
  - Sequential stopping: after each +250 preference pairs, stop if posterior P(improvement>5pp) > 0.95 (Bayesian beta–binomial) or continue.
- Reporting
  - Provide clear learning curves (prefs vs win rate), per-negative-type gains, and calibration plots of refusal vs format compliance.
  - Explicitly state Stage 1 does not test constitutional principle usage; defer that claim to later stages with critique→revise.

## Experimental Design Notes
- Two-stage justification: SFT provides token-level supervision and format learning; DPO aligns sequence-level preferences and reduces refusal/format violations—consistent with prior work. Show this via ablations and by comparing loss-masked SFT to unmasked.
- Negative set construction: Prefer semi-automated mining—sample real model failures on a held-out probe set, label by type with rules/LLM, and mirror those proportions; optionally bias toward harder negatives via online mining.
- Sample size plan: MVP shakedown at 200/500; for publication, aim ≥2k SFT examples and 5k–10k preference pairs, or justify smaller N with strong effect sizes and tight CIs.

## Risks and Mitigations
- Selection/evaluation bias → Pre-register endpoints, blind the scoring where feasible (LLM-as-judge without model identity), and disclose prompts.
- Confounding by data quality → Hold data pipeline constant across variants; swap only the training stage being tested.
- Reproducibility → Release seeds, configs, and scripts; evaluate across ≥2 seeds; snapshot artifacts.

## Verdict
Methodology is directionally sound and aligned with CAI-adjacent practice for instruction following, but current N and missing ablations limit evidential strength. Acceptable for MVP; needs stronger baselines, power, and multiple-comparison controls for publication.
