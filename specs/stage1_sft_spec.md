# Stage 1 SFT Training Spec (QLoRA from Base Model)

Objective
- Train an instruction-following model via QLoRA using the Stage‑1 SFT dataset generated per stage1_data_generation_spec.md.

Scope
- Single‑GPU QLoRA (4‑bit base) with bf16 compute when available.
- Deterministic evaluation on a held-out set with paired tests and CIs.
- Gating on dataset quality and eval significance before scaling.

Preconditions (hard gates)
- Data generation pilot and scale have passed QC thresholds.
- Dataset manifest exists with provenance and QC summary.
- Contamination guards were applied in generation and verified.

Environment
- Same pod conventions as data generation (see runbooks/POD_OPERATIONS.md).
- Prefer NVIDIA H100/H200 for training; MI300X optional after methodology verified.

Training Configuration (reference defaults)
- Model: Qwen/Qwen2.5-32B (base), loaded via CleanModelLoader.
- Quantization: 4‑bit (nf4) with bfloat16 compute; LoRA adapters (r≈16–32, alpha≈16–32, dropout≈0.1).
- Optimizer: AdamW with LR≈2e‑4 (tune in pilot), weight decay≈0.01.
- Batch: effective batch size via gradient accumulation; start with per‑device batch=1–2, accumulation to reach 8–16.
- Epochs: 2–4; use early‑stop based on dev eval.
- Max sequence length: 1024–2048 (tune by GPU memory); apply loss masking to train only on response tokens.

Evaluation Protocol (deterministic)
- Use the same held‑out items for base vs SFT to enable paired tests.
- Decoding: temperature=0, do_sample=False (greedy) for determinism.
- Metrics: overall success rate, per‑type success rates, Wilson 95% CIs for proportions, McNemar test p‑values overall and by type (BH correction across types), Cohen’s h for effect size.
- Reporting: JSON with counts, rates, CIs, p‑values, adjusted p‑values, effect sizes, and metadata (seeds, SHAs, decoding params).

Pilot & Gates
- Pilot: run on the full held‑out set (N≈800–1200) or a deterministic subset ≥ 300 if compute-constrained.
- Gate: overall improvement significant (McNemar p<0.01) with reasonable CI widths; no regression on safety/format types beyond CI overlap.
- If gate fails: inspect data QC distributions and training logs; tune LR/epochs/sequence length; consider regenerating low‑quality slices.

Outputs
- Checkpoints: LoRA adapters under /workspace/checkpoints/stage1_sft/ with TRAINING_SUCCESS marker capturing adapter path and git SHA.
- Eval: evaluation JSON and a text summary; include seeds, environment, decoding params.
- Manifest: training manifest with hyperparameters, dataset path, SHAs, and eval linkage.

Acceptance Tests
- Training completes without OOM; adapters saved; TRAINING_SUCCESS file created.
- Deterministic eval present and statistically significant improvement (gate).
- Provenance complete: commit SHAs, loader_version, environment versions, decoding parameters.

Notes
- Keep training single‑GPU unless throughput demands otherwise; scale via accumulation not DP unless required.
- After SFT is stable and evaluated, consider enabling DPO with a separate spec.

