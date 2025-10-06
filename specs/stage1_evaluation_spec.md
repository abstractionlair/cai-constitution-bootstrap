# Stage 1 Evaluation Spec (Deterministic, Paired)

Objective
- Provide a deterministic, paired evaluation framework to compare base vs SFT (and later DPO) on the same items with proper statistics and provenance.

Scope
- Deterministic decoding (temperature=0) for all evals used in statistical testing.
- Paired tests across identical items; per-type analysis with BH correction.
- Provenance and reproducibility: seeds, SHAs, environment, decoding parameters.

Inputs
- Held-out instruction set (N≈800–1200 preferred) distinct from any training inputs.
- Model checkpoints: base (reference), SFT adapters (LoRA), optional DPO adapters.

Protocol
- Prompt format: Match training format unless explicitly evaluating generalization (document decision). Default: "Instruction: {instruction}\nResponse:".
- Decoding: temperature=0, do_sample=False, max_new_tokens set to avoid truncation; pad/eos IDs set correctly.
- Per example: record instruction, response, success (bool), failure reason (string), tokens_generated.

Statistics
- Overall: success rate with Wilson 95% CI; McNemar test (continuity-corrected) for paired binary outcome; Cohen’s h effect size.
- Per-type: same metrics; apply Benjamini–Hochberg (FDR=0.10) to adjusted p-values; report significant_after_bh.
- Bootstrap CI for lift (difference in proportions) if desired.

Outputs
- JSON with: counts, rates, CIs, p-values, adjusted p-values, effect sizes, discordant pairs, and metadata (labels, confidence level, bootstrap samples, seeds).
- Summary text file with overall and per-type tables; clear go/no-go recommendation per phase gate.

Acceptance
- Reproducible across runs with same seed and environment.
- For SFT pilot gate: McNemar p<0.01 overall; acceptable CI widths; no major regressions in key safety/format types.

