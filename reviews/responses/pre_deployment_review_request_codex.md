# Codex Review Response: Pre‑Deployment Technical Validation
Date: 2025-09-11
Request File: pre_deployment_review_request.md

## VERDICT
YELLOW LIGHT

The Stage 1 pipeline is close to deployable. Core blockers from earlier reviews are largely addressed (held‑out eval set, template fixes, consistent evaluation inputs, 95% gate). I recommend proceeding with a monitored GPU run, contingent on addressing the non‑blocking items below or accepting them as known risks for MVP.

## Blockers
- None hard blockers for an initial deployment.

## Warnings
- Paired statistical analysis not implemented: `evaluate_stage1.py` computes success rates but does not run McNemar’s test, CIs, or bootstraps. This limits publication‑grade claims. Not a runtime risk, but plan to add post‑hoc analysis scripts before publishing results.
- Persistent eval integrity depends on `train_instructions.jsonl`: The evaluation code correctly verifies overlap and uses a persistent set. Ensure the full pipeline order (generate → train → evaluate) is followed; ad‑hoc evaluation without having generated/saved train instructions will trigger the leakage check to fail.
- Memory headroom for 32B at 8‑bit (evaluation): Evaluation loads base and trained models with Unsloth `load_in_8bit=True` and merges LoRA. On A100 80GB this should fit, but KV cache and batch size spikes can push usage; keep batch size 1 during evaluation and monitor GPU stats.
- Model loader consistency (non‑critical): `scripts/utils/model_loader.py::load_trained_model` path likely won’t load PEFT adapters as intended (it calls `FastLanguageModel.from_pretrained` on the adapter directory). The evaluation flow uses `PeftModel.from_pretrained(...).merge_and_unload()` correctly, so this is only a latent inconsistency.
- Few‑shot coverage: Examples were expanded but remain simple; harmless for Stage 1, just note potential brittleness if prompts deviate.

## Suggestions
- Add analysis script for paired stats: A small `analysis/stage1_stats.py` that loads the latest `results/stage1_evaluation_*.json` and reports McNemar’s p‑value, Wilson CIs, Cohen’s h, plus bootstrap CIs overall and by type.
- Record reproducibility metadata: In the evaluation output, add generation parameters (temperature, do_sample, seeds), the exact eval set path, and file hashes (`eval_instructions.jsonl`, `overlap_report.json`). You already include methodology pointers—keep those.
- Guardrails in evaluation: Assert eval batch size = 1 and log GPU memory at start/end to catch OOM early. Consider a `--dry-run` that loads models and builds the eval set without generating to validate environment.
- Training stability knobs: Expose `gradient_accumulation_steps` and `beta` via CLI flags; log total tokens seen. For 32B@4‑bit, keep `batch_size=4` unless measurements show headroom.
- Pipeline resumability: You already skip baseline/data if artifacts exist. Optionally add `--resume-training` to pick up the last DPO checkpoint; not required for MVP.

## Confidence
8/10

Rationale: The critical methodology concerns are addressed in code:
- Held‑out eval set: Implemented (`eval_instructions.jsonl`, `overlap_report.json`, `verify_no_leakage()`), created from eval pools and filtered against `train_instructions.jsonl`.
- Evaluation inputs: Both models receive identical raw instructions with deterministic decoding (`do_sample=False`, `temperature=0.1`).
- 95% gate: Enforced in `run_stage1_pipeline.py` via latest evaluation JSON.
- Template bugs: Fixed in `data_formatter.py` (`generation` uses direct prompt; `response` uses `{input}`).
- RunPod compatibility: `CAI_BASE_DIR` used consistently; Unsloth loaders for memory efficiency; logging and result persistence are in place.

Proceed with deployment, monitor GPU memory during evaluation, and plan to add the paired statistical analysis post‑run for publication quality.
