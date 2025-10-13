# Stage 1B Conversation Evaluation Spec — Codex Review (2025-10-13)

## Summary
- ⚠️ MODIFY – Solid framing and gating, but the current scoring design and baseline configuration leave too much ambiguity to guarantee a defensible capability gap.

## Issues
- 🚨 CRITICAL – Automated heuristics cannot reliably support the gating logic as written (specs/stage1b_conversation_eval_spec.md:200, specs/stage1b_conversation_eval_spec.md:381). The proposed string checks cover only a handful of lexical patterns, yet the conversations span diverse contexts (dietary restrictions, professional facts, pronoun resolution). Requiring heuristics and the LLM judge to agree on every conversation (specs/stage1b_conversation_eval_spec.md:247) will systematically mark good conversations as failures and makes it impossible to hit the ≥80 % agreement gate. The spec needs either (a) tightly templated conversations with explicit per-item heuristics, or (b) heuristics downgraded to diagnostics rather than gates.
- ⚠️ HIGH – The “base-raw” prompting path is underspecified for multi-turn evaluation (specs/stage1b_conversation_eval_spec.md:278, specs/stage1b_conversation_eval_spec.md:479, specs/stage1b_conversation_eval_spec.md:153). Without clear turn delimiters, it is ambiguous how prior assistant responses are fed back, so we cannot guarantee that the raw baseline faces the same multi-turn task as the formatted runs. This threatens the entire gap argument.

## Recommendations
1. Constrain the benchmark templates so every conversation has machine-checkable slots (e.g., fill-in-the-blank entities, whitelist of acceptable recipe ingredients) and encode those expectations alongside the data; otherwise, move heuristics to a “triage” role and gate on the LLM judge plus human calibration.
2. Specify the exact generation loop for all four model settings, including how transcripts are constructed after each turn and how CleanModelLoader disables chat templates (completion mode, `add_special_tokens=False`). The “base-raw” condition should still preserve explicit separators (e.g., blank lines or `User` tags) so the task is well-defined while avoiding helpful system cues.
3. Treat heuristics vs judge disagreements as audit triggers rather than automatic failures; require ≤10 % disagreement and resolve via human adjudication sampled from each category to satisfy the reliability gate.
4. Keep the 30–40 conversation pilot, but pre-compute expected power: with base 0.3 vs instruct 0.8 over 200 paired samples, McNemar has >0.99 power at α=0.01; document that calculation to answer reviewer questions about adequacy. Per-category slices (~50 items each) will still yield Wilson CI half-width ≈0.12, which is acceptable for directional checks.
5. Use Claude 3.5 Sonnet as primary judge for cost/performance, and spot-audit 10 % of samples with GPT-4 to monitor drift; log κ against the calibration set every run.
6. Prefer Llama 3.1 8B as the alternate base (closest capability + strong open weights). If time allows, sample 20 pilot conversations with Mistral 7B to confirm the sanity check generalises.

## Specific Answers
- Conversation format: Keep `User:`/`Assistant:` labels for all evaluated runs; the raw baseline can omit an initial Assistant seed but still needs consistent turn delimiters to avoid collapsing into single-turn completions.
- Conversation difficulty: Current templates are appropriate once templated; ensure the dataset intentionally mixes easy/medium difficulty within each category.
- Scoring design: Dual scoring is good, but heuristics must become conversation-specific or non-gating. Majority vote is unnecessary if you treat heuristics as diagnostics and audit disagreements.
- Sample sizes: Pilot 30–40 is adequate to validate the gap; 200 full conversations give enough power for h≈0.5 and per-category slices. Document the power calc.
- Alternative base: Start with Llama 3.1 8B; expand to Mistral only if the sanity check is inconclusive.
- Gate thresholds: Base ≤30 % / Instruct ≥80 % align with the hypothesised gap; retain them once scoring is reliable.
- Missing elements: Need explicit transcript construction algorithm, contamination safeguards (CleanModelLoader), and storage of per-conversation expectation metadata to make the heuristics auditable.

## Approval
- **Decision**: MODIFY – Address scoring reliability and baseline configuration before implementation.
