# Program Spec: Constitutional AI Bootstrap (V2)

Purpose
- Build an automated, spec-driven pipeline to transform a base model into an instruction-following model (Stage 1), then extend toward preference learning (DPO).
- Operate primarily via autonomous pod sessions driven by Claude Code with Codex methodology sign-off at gates.

Invariants (Do Not Violate)
- Completion-mode everywhere for base models; never rely on chat templates.
- Single-token A/B critics with logprob margins for automated judgments; no free-form critique for gating.
- One canonical implementation per concern (CleanModelLoader, CompletionStylePrompts, instruction_critic, instruction_generator). No reimplementation in scripts.
- Gated progression: Pilot → QC pass → Scale; training phases refuse to run without required manifests.
- Full provenance: every dataset and evaluation has a manifest with environment, SHAs, parameters, QC.

Milestones (Stage 1)
- Data Generation: model-generated instructions + logprob-based filtering to produce ~15k high-quality SFT examples.
- SFT Training: QLoRA on the base model using generated SFT data; deterministic evaluation and stats.
- Optional DPO Prep: Best-of-N sampling and hard negatives to produce preference pairs (out of scope for this spec unless explicitly enabled).

Gatekeeping & Decisions
- Data Gen Pilot (100–200 items): proceed only if all QC thresholds pass (see stage1_data_generation_spec.md).
- SFT Pilot Eval: proceed only if paired, deterministic eval shows statistically significant improvement (McNemar p < 0.01 overall) with effect sizes and CIs reported.
- DPO Pilot (if enabled): proceed only if margins and pair quality distributions meet thresholds.

Roles
- Claude Code (Sonnet 4.5): primary implementer/runner on pod; executes pilots, computes QC, scales when gates pass.
- Codex (GPT‑5): writes specs/runbooks; validates methodology at gates; answers one‑shot questions.
- User: approves budgets and hardware; unblocks environment; approves proceed/stop at gates.

Budgets & Hardware
- Default budget for Stage 1: up to $300 total (flexible). Prefer NVIDIA (H100/H200) for verification; consider MI300X after methodology verified for larger unquantized LoRA runs.

Artifacts & Layout
- /workspace is the durable root on pods (see runbooks/POD_OPERATIONS.md for env vars and cache paths).
- Artifacts stored under /workspace/artifacts, datasets under /workspace/data, checkpoints under /workspace/checkpoints, logs under /workspace/logs, results under /workspace/results.
- Each phase emits a manifest JSON documenting inputs, environment, SHAs, and QC metrics.

Change Control
- Specs are the source of truth. Claude must request Codex review when deviating from spec.
- DRY enforcement via CI grep checks forbidding manual base-model loads and duplicate critic logic.

