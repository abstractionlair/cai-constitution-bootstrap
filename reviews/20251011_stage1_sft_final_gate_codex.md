Summary: ⚠️ MODIFY – Resolve evaluation hold-out duplication/leakage and scrub the remaining truncated list outputs before SFT.

🚨 CRITICAL
- `data/test_instructions_clean.jsonl:130` (also 192, 291, 298, 332) duplicates the same prompt five times, and that prompt already appears in the training data (`data/stage1_sft_data_final_clean.jsonl:3327`). The hold-out set currently has only 137 unique instructions out of 343 rows, so McNemar statistics would be overweighted by a handful of templates and the zero-leakage guarantee in `specs/stage1_evaluation_spec.md` is violated. Please deduplicate/expand the eval set to ≥300 unique instructions, re-run the leakage audit against the training JSONL, and refresh the manifest before training.

⚠️ HIGH
- `data/stage1_sft_data_final_clean.jsonl:4025` and `data/stage1_sft_data_final_clean.jsonl:4611` still end mid-list (“Biomass Energy -”, “Professionalism -”). The Phase 3b truncation detector is missing these enumeration tails, so the current QC summary’s “Truncated responses: 0 (0.00%)” under-reports true failures. Tighten the truncation heuristic (e.g., flag numbered bullets ending with bare hyphens or colons), drop or regenerate the affected rows, and update the QC manifest so we have evidence the detector now catches this pattern.

💡 SUGGESTIONS
- Re-run the data/hold-out audits with the updated scripts and attach the new QC summary + provenance manifest to your training request so future gates can rely on the logged metrics.
- Since sentinel responses sometimes look instruction-following (e.g., Pig Latin translation) while still passing the heuristic, consider logging a short qualitative sample per run to catch template regressions sooner.
