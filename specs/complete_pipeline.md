# Complete Pipeline (V2) — High-Level Architecture

Phases (Stage 1 focus)
- A. Data Generation: model-generated instructions → responses → logprob-based filtering → ~15k SFT examples with manifests and QC.
- B. SFT Training: QLoRA from base; loss masks on response tokens; deterministic eval on held-out set; stats and manifests.
- C. (Optional) Preference Pairs & DPO: Best-of-N sampling and hard negatives; DPO training with margins and QC gating (spec to follow).

Invariants
- Completion-mode for base models; no chat templates.
- Single-token A/B critics (logprob decisions) for automated QC.
- One canonical implementation per concern; enforce with CI grep.
- Gated progression; pilots before scaling/training.

Execution Model
- Autonomous sessions on a GPU pod following runbooks/AGENT_RUNBOOK_STAGE1.md.
- Pods treat compute as ephemeral and /workspace as durable; every phase persists manifests and QC summaries.

Roles
- Claude Code: implement/execute per specs; stop on gates; page Codex for methodology decisions.
- Codex: write/maintain specs; sign-off at gates; answer one-shot questions.

Artifacts
- Datasets: /workspace/data
- Artifacts/QC/Manifests: /workspace/artifacts
- Checkpoints: /workspace/checkpoints
- Results/Evals: /workspace/results
- Logs: /workspace/logs

