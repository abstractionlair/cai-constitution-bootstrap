# Codex Review Response: Stage 1 Methodology Verification
Date: 2025-09-10
Request File: 20241228_120000_stage1_methodology.md

## Methodology Assessment
1. CRITICAL — Baseline fairness and parity: baseline_assessment.py evaluates the base model with HF loaders (float16/bfloat16/float32 depending on device) while evaluate_stage1.py evaluates both base and trained models under Unsloth in 8‑bit and uses a different evaluator/spec. Mixed precision, loaders, and criteria risk confounding the claimed delta.
2. HIGH — Data diversity and leakage: Stage1DataGenerator reuses small pools (≈30 QA items, ≈20 completions, ≈20 response inputs) and recycles the same templates across train/eval (only seed differs). This invites lexical overfitting and evaluation leakage, weakening bootstrapping claims.
3. MEDIUM/HIGH — Success gate validity (95%): The gate is applied to ~100 examples without confidence intervals or paired significance tests. Single-seed sampling with stochastic decoding increases variance; false positives are plausible.
4. HIGH — Constitutional integration: constitution.yaml is loaded, but critiques do not explicitly reference or tag principles; no logging of principle usage or coverage; DPO pairs are selected on generic “instruction following” heuristics. This blurs CAI vs. generic preference learning.

## Scientific Validity
- ✅ Strengths
  - Consistent same-set comparison of base vs trained within evaluate_stage1.py (same eval set, deterministic-ish temperature=0.1).
  - Clear, automatable instruction-following criteria in utils/metrics.py; stage-level aggregation and by-type breakdown implemented.
  - Separation of data gen → critique → revise → DPO aligns with CAI pipeline phases.
- ❌ Gaps
  - Non-identical baseline methodology, precision, and loaders between baseline_assessment and stage evaluation.
  - Train/eval content overlap via small, recycled pools; lack of leakage checks or held-out lexical partitions.
  - No confidence intervals, effect sizes, or significance tests reported; single-seed evaluation; stochastic decoding enabled.
  - Principles not referenced or tagged in critiques; no measurement of principle usage, coverage, or revision-by-principle gains.
- ⚠️ Needs clarification
  - Whether the improvement claims will be anchored to (a) within-evaluator base vs trained on the same set, or (b) the separate baseline_assessment.json results; current code includes both and may confuse interpretation.
  - Whether unsloth quantization materially alters base model outputs vs HF FP16/FP32; an ablation is advisable if 8-bit is used for all evaluation.

## Statistical Concerns
- Lack of CIs: For 100 samples at 95% success, Wilson 95% CI is wide (~±5–6 pp). Report CIs per overall and per type.
- Significance vs baseline: Use paired tests across the same items (McNemar’s test on success/fail per item) between base and trained; report p-values and absolute deltas with CIs. Two-proportion z-tests are acceptable when pairs aren’t aligned, but you have paired data here.
- Seed and decoding variance: Evaluation uses temperature=0.1 with sampling. Prefer greedy (`do_sample=False`) or fixed sampling with multiple seeds and aggregate via bootstrap.
- Power/sample size: For publication claims on ≥10 pp improvements, target N≥300–500 to narrow CIs and increase power (80–90%). For MVP, run ≥3×100-seed replicates and aggregate with bootstrap CIs.

## Recommendations
- Baseline fairness (minimum changes)
  - Evaluate BOTH base and trained models under identical settings: same loader (Unsloth), same 8-bit precision, same tokenizer, same decoding (greedy, `do_sample=False`). Keep temperature=0 for eval unless strongly justified.
  - Anchor improvement claims to the paired base vs trained results within evaluate_stage1.py (same eval set). Treat baseline_assessment.py as exploratory context only, not the comparator for deltas.
  - If you must include the baseline_assessment numbers, add an explicit disclaimer and/or an ablation showing precision/loader choice changes outcomes by <1–2 pp.

- Data quality and leakage control (minimum changes)
  - Expand content pools substantially: QA ≥200 unique questions; completions ≥150 unique partials; response inputs ≥150; generation topics via combinatorics already help but ensure train/eval disjointness.
  - Enforce disjoint splits by lexical unit: reserve disjoint question/partial/input strings for eval; assert no overlap in raw fields (e.g., `raw_question`, `raw_partial`, `raw_input`). Persist split indices and check during evaluation.
  - Increase template variety: ≥10–15 surface templates per type (currently 5). Add paraphrase templates (active/passive voice, chat-style variants, natural phrasings).
  - Optional, high value: Create synthetic paraphrases via the base model (or small instruct model) and filter for semantic equivalence to multiply surface forms without content leakage.

- Success gate validity (minimum changes)
  - Switch to deterministic decoding for eval (`do_sample=False`).
  - Report Wilson 95% CIs for overall and by-type success rates.
  - Use McNemar’s test on paired base vs trained outcomes; report p-values and absolute/relative deltas.
  - Gate definition: proceed only if the lower CI bound ≥ 90% and absolute improvement vs base is ≥ 10 pp with p<0.01 on ≥300 examples or on ≥3×100-example replicates with bootstrap CI lower bound ≥ 90%.

- Constitutional integration (minimum changes)
  - Select 1–3 principles per example (sampled by category) and inject IDs into critique prompts; require the model to cite `[P:principle_id]` for violations.
  - Parse and log principle IDs referenced in critiques; store in DPO pair metadata. Track distribution across categories and principle coverage.
  - Require improvements to explicitly address cited principles (“Fix per [P:clarity_conciseness] and [P:no_misinformation]”).
  - Add evaluation of “principle usage” metrics: proportion of critiques with valid principle tags, coverage across categories, and revision success conditioned on principle.

- Nice-to-have improvements
  - Add bootstrap CIs for improvement by instruction type; plot forest plots of deltas with CIs.
  - Run an ablation: precision (8-bit vs 16-bit) and decoding (greedy vs sampled) to show robustness.
  - Add a leakage report artifact: counts of overlapping raw strings/templates between train and eval.
  - Automate an “automation level” metric: number of human interventions/time taken per 1k examples; include in results summary.

## FATAL Issues (if unaddressed)
- If improvement claims are tied to baseline_assessment numbers without matching precision/loader/evaluator, the comparative claim is invalid (FATAL for delta claims).
- If train/eval leakage is present (content overlap in QA/partials/inputs) and not reported/controlled, the 95% claim on generalization is not defensible (FATAL for generalization claim).
- If critiques do not reference constitutional principles and you claim “Constitutional AI,” reviewers can reasonably argue this is generic preference optimization (FATAL for “CAI” framing; HIGH for alignment claims).

## Minimum Patch Set to Reach Publication-Ready
1. Standardize evaluation: identical precision/loader/decoding for base and trained; use paired tests and Wilson CIs; switch to deterministic decoding.
2. Data hygiene: expand pools; enforce disjoint lexical splits; add overlap assertions and a leakage report.
3. CAI grounding: principle sampling, explicit tagging in critiques, logging and reporting of principle usage and revision-by-principle success.
4. Replication: 3 seeds × 100 examples or 1 seed × ≥300 examples; report aggregate with CIs and p-values.

These changes keep scope modest but materially upgrade scientific rigor and defendability of claims.
