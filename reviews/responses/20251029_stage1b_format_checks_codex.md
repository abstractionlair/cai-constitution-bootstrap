# Stage 1B Held-Out Format Checks — Codex Review (2025-10-29)

## Summary
- ⚠️ MODIFY – Add targeted held-out format diagnostics so Stage 1B’s gate cannot be satisfied via the `User:`/`Assistant:` transcript alone, then document how those diagnostics feed into the go/no-go decision.

## Findings
- 🚨 CRITICAL – Current three-way evaluation in `specs/stage1b_conversation_eval_spec.md:382` only measures format sensitivity for the base model. Without an equivalent probe on the Instruct run, we could still over-credit a model that memorises the canonical transcript structure—exactly the failure mode documented in `docs/STAGE1_FINDINGS_AND_PIVOT.md:40`-`docs/STAGE1_FINDINGS_AND_PIVOT.md:83`.
- ⚠️ HIGH – The spec does not describe how heuristics or the LLM judge should score non-canonical transcripts. Adding held-out formats later would force another round of rubric work; folding them into the initial calibration keeps the scoring contract consistent (`specs/stage1b_conversation_eval_spec.md:360`-`specs/stage1b_conversation_eval_spec.md:444`).
- 💡 SUGGESTION – A single alternate scaffold (e.g., no speaker tags) plus a structured variant (JSON object per turn) is enough to detect format artifacts; no need to mirror the full 300-sample benchmark on every variant if cost is a concern.

## Recommendations
1. Extend the spec with a **Format Generalisation** subsection: run the Instruct (and optionally base-formatted) models on ≥50 stratified conversations using (a) bare newline transcripts and (b) a JSON turn schema; report success rates and judge margins alongside the primary metric.
2. Treat these held-out runs as **diagnostics, not hard gates**—flagging any ≥15 pp drop relative to canonical format for manual audit before approving the pivot—and fold their scoring into the same calibration workflow so κ ≥ 0.7 still applies.
3. Document rubric adjustments for the alternate renderers (e.g., updated heuristic entity extraction) to preserve reproducibility, and store the variant transcripts plus results in the evaluation manifest so later stages can reuse them.

## Answers to Questions
1. Necessary vs over-engineering: It is necessary; without it we risk a repeat of the Stage 1 template artefact and cannot convincingly argue the capability gap is format-independent.
2. Timing: Include from the pilot onward so calibration covers every renderer and we avoid retrofitting the scoring stack mid-stream.
3. Additional validation: Add a quick **label-swap** ablation (rename `User`/`Assistant` to `Customer`/`Agent`) and a **negative control** run that shuffles earlier turns; both should crater scores if the judge is working, providing extra sanity checks before we invest in training.

