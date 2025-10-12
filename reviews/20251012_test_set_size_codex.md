Summary: ⚠️ MODIFY – Expand the held-out evaluation set to at least 300 unique instructions before resuming Stage 1 SFT.

🚨 CRITICAL
- The Stage 1 SFT spec explicitly permits either the full 800–1200 item hold-out or, if constrained, a deterministic subset **≥ 300** items (`specs/stage1_sft_spec.md:35`). Holding at 136 violates that gate, so downstream training would be out of compliance with the approved methodology.
- The Stage 1 evaluation spec expects per-type paired analysis with Benjamini–Hochberg correction (`specs/stage1_evaluation_spec.md:11`, `specs/stage1_evaluation_spec.md:20`). With only 136 items, several instruction categories would drop below the minimum counts needed to compute those adjusted p-values or produce interpretable confidence intervals, undermining the publishable evaluation plan.

⚠️ HIGH
- Statistical power suffers at N=136 for the McNemar gate (p < 0.01). Even a 12–15 item lift can fail the continuity-corrected test unless the discordant counts are extremely imbalanced, so we risk a false “no-improvement” verdict after investing compute in SFT.
- Future comparisons (e.g., SFT vs. SFT + DPO) will reuse the same hold-out. Locking in 136 now forces every later gate to rerun with an underpowered set or redo the expansion later when costs are higher. Spending ~1 hour now to cross the ≥300 threshold avoids a cascading rework.

💡 SUGGESTIONS
- Regenerate another ~250 raw instructions with the existing generator, then rerun dedupe/leakage to land around 320 unique items; log the updated manifest alongside the leakage audit so the next gate has the full provenance.
- While generating, stratify by the evaluation types you report (format, safety, refusal, knowledge, etc.) so the per-type cells stay well above 30 and BH-adjusted p-values remain meaningful.

