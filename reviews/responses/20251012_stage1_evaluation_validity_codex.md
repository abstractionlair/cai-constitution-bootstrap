Summary: ❌ Stage 1 evaluation is invalid; gate must remain closed until a corrected assessment passes.

🚨 CRITICAL
- Broken scoring heuristic mislabels compliant responses as failures by capping length at 500 characters, so observed “improvement” mainly reflects shorter generations rather than better instruction-following (scripts/evaluate_stage1_sft.py:226).
- The current success label ignores factual accuracy and format requirements, allowing incorrect or incomplete answers to count as wins, so success rates do not measure instruction-following quality (scripts/evaluate_stage1_sft.py:226).
- Baseline prompt wrapper (`"Instruction: …\nResponse:"`) changes base-model behaviour relative to sentinel checks; without isolating this confound we cannot attribute gains to SFT (docs/BASE_MODEL_TRUTH.md:6, specs/stage1_evaluation_spec.md:14).

⚠️ HIGH
- McNemar significance and confidence intervals are uninterpretable because they rely on the corrupted success labels; reported p = 2.06×10⁻¹² does not provide evidence of real improvement (specs/stage1_evaluation_spec.md:24).
- Pilot size (300) is acceptable for a constrained run, but needs re-use only after labels are trustworthy; otherwise variance estimates will stay misleading.

💡 SUGGESTIONS
- Integrate CleanModelLoader sentinel prompts into evaluation CI so prompt-format regressions are caught automatically (specs/CONTAMINATION_GUARD_SPEC.md:9).
- Archive a 20–30 item human-reviewed calibration set to sanity-check any automatic scoring changes before scaling.

Recommendations:
1. Halt progression to Stage 2; mark Stage 1 gate as “blocked pending re-evaluation.”
2. Replace the scoring heuristic with an instruction-following judge that verifies task compliance and factual adequacy. Two viable options: (a) reuse the single-token pair critic with a high-confidence margin threshold, or (b) use an external LLM-as-judge with deterministic prompts and majority voting. Document the choice and validation set.
3. Re-run the evaluation under three conditions: (i) base model with raw instruction prompt, (ii) base model with `"Instruction: …\nResponse:"`, and (iii) SFT model with the canonical prompt. This isolates the prompt-format effect and quantifies the real SFT gain.
4. After relabeling, recompute success metrics, Wilson CIs, McNemar test, and effect sizes per specs/stage1_evaluation_spec.md. Only pass the gate if the corrected labels show a significant lift (p<0.01) with no regressions on safety/format slices.
5. Update the evaluation manifest to include scoring implementation details, prompt formats, and sentinel results so future audits can reproduce the findings.

Statistical Concerns:
- Because success labels are corrupted, all downstream statistics (rates, CIs, McNemar χ², p-values, Cohen’s h) are invalid; do not cite them.
- Recompute statistics after relabeling and apply Benjamini–Hochberg corrections across per-type tests as required by the spec.

Overall Assessment:
- Stage 1 SFT gate remains **not passed**. Redo evaluation with corrected scoring and baseline comparisons before attempting Stage 2 work.
