# Agent Runbook: Stage 1 (Data Gen → SFT → Eval)

Overview
- This runbook is the execution playbook for Claude Code on a pod. It encodes commands, timeouts, QC gates, manifests, and stop conditions.

Bootstrap (once per session)
- Source pod bootstrap script if present; otherwise export envs:
  - HOME=/workspace/home
  - XDG_CONFIG_HOME=/workspace/.config
  - HF_HOME=/workspace/.cache/huggingface
  - TRANSFORMERS_CACHE=/workspace/.cache/huggingface/transformers
  - HF_DATASETS_CACHE=/workspace/.cache/huggingface/datasets
  - TORCH_HOME=/workspace/.cache/torch
- Ensure directories exist: /workspace/{artifacts,results,logs,data,checkpoints}.
- Preflight: verify at least one GPU present, writeable /workspace, and model snapshot or HF connectivity.

Phase A: Data Generation Pilot (100–200)
- Implement per specs/stage1_data_generation_spec.md using canonical utilities only.
- Run pilot; write outputs to /workspace/artifacts/data_gen_pilot_YYYYMMDD_HHMMSS/{dataset.jsonl,qc_summary.json,session_manifest.json}.
- Validate QC thresholds; if any fail, adjust temperature/max_new_tokens/heuristics and rerun (max 2 retries).
- If still failing: stop and request codex review.

Phase B: Scale Data Generation (~15k)
- Shard instructions across GPUs/seeds; write one manifest per shard under /workspace/artifacts/data_gen_shards/.
- Merge shards to /workspace/data/stage1_sft_data.jsonl; recompute QC across union; store qc_summary.json and merged manifest.
- Gate: thresholds must pass. If fail: fix or stop for review.

Phase C: SFT Training Pilot
- Train QLoRA per specs/stage1_sft_spec.md using the merged dataset.
- Save adapters to /workspace/checkpoints/stage1_sft/; write TRAINING_SUCCESS with adapter path & SHA.
- Evaluate deterministically on held-out set; write eval JSON + text summary under /workspace/results/sft_eval/.
- Gate: McNemar p<0.01 overall; reasonable CI widths. If fail: tune and retry pilot.

Phase D: (Optional) DPO Pilot
- Only if enabled by spec; otherwise skip.

Stop Conditions
- Any contamination sentinel failure.
- CI/grep checks find manual base-model loads or duplicate critic logic.
- QC thresholds not met after allotted retries.
- Missing manifests or incomplete provenance.

Manifests & Logging
- Every phase creates a manifest in its artifact directory with environment, commands, parameters, SHAs, and outcomes (pass/fail, reasons).
- Append artifacts to a session-level manifest at /workspace/artifacts/session_manifest_*.json.

Paging Codex (one‑shot)
- Use the autonomous review template when: a gate fails twice; methodology ambiguity; stats questions; contamination or DRY violations.

