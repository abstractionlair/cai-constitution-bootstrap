Summary: ❌ NO-GO – Stage 1 SFT training should wait for data + evaluation fixes.

🚨 CRITICAL
- `artifacts/scale/qc_summary_merged.json`: thresholds_passed=false due to runaway_rate=34.7% ≥ 5% (legacy heuristic). Gate spec forbids training until merged QC passes; regenerate summary with fixed heuristic or re-run QC.
- `data/stage1_sft_data.jsonl`: all entries have `"sentinel_tests_passed": false` because the simple completion sentinel fails (`scripts/utils/clean_model_loader.py`). Spec requires contamination sentinels to pass; adjust sentinel tolerance (length check) or investigate genuine contamination.
- `data/stage1_sft_data.jsonl`: only 1,311 unique instructions out of 3,968; top item repeats 273×. Heavy duplication undermines Stage 1 goals and reduces statistical power. Deduplicate or generate more diverse instructions before training.
- `data/stage1_sft_data.jsonl`: 1,510/3,968 responses end with `"###"` stop marker. Cleaning step left artifacts, which risks imprinting delimiters during SFT. Strip markers and re-run QC after cleanup.
- Evaluation readiness: `data/test_instructions.jsonl` has N=200 (< Spec minimum 300) and 3 instructions overlap with training. Cannot satisfy Stage 1 gate (McNemar p<0.01 with adequate power). Expand/refresh holdout set and ensure zero leakage.

⚠️ HIGH
- Records omit `instruction_critique` despite schema in `specs/DATA_SCHEMAS_AND_PROVENANCE.md`; restore field for auditability.
- Dataset size 3,968 (≈26% of 15k target). With duplicates, effective examples are ~1.3k. Consider lowering critic threshold or adding shards to reach ≥6–8k unique before LoRA.
- Training config: LR=2e-4, 3 epochs, batch 2 × grad_accum 4 ⇒ 1,488 updates over tiny dataset. Risk of overfitting once data issues fixed; consider LR≤1e-4 or fewer epochs pending new data.

💡 SUGGESTIONS
- After dedupe/cleanup, recompute QC manifest with corrected heuristic so gate artifacts stay consistent.
- Track refusal/format diversity in QC to ensure dataset isn’t dominated by basic factual Q&A.
- When expanding eval set, follow spec (paired deterministic decode, BH correction) and document power analysis.

Recommendation
- Remediate critical blockers above, regenerate dataset/eval assets, and rerun gate review. Only then revisit SFT training configuration (possibly with milder LR/epochs tuned to final dataset size).
