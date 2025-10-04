# Review Response: DRY Policy & Methodology Rigor

**Reviewer**: codex
**Date**: 2025-10-04
**Request**: 20251004_dry_policy_and_migration_codex.md

## Summary
⚠️ Issues Found

- The DRY policy and migration stance are directionally correct and well documented, but incomplete migration currently jeopardizes methodological consistency and reproducibility claims. Proceed only with migrated scripts or run an A/B equivalence check before using mixed patterns. Strengthen contamination verification and evaluation statistics.

## Issues Found

### 🚨 CRITICAL
1. Mixed contamination‑prevention patterns risk inconsistent methodology (project‑wide)
   - Description: Only 3–4/15 scripts have migrated to `CleanModelLoader`; others still rely on manual `chat_template=None` and ad‑hoc tokenization. Mixed usage breaks the “single source of truth” and undermines claims of uniform contamination prevention.
   - Impact: Results across scripts may not be comparable; contamination bugs could selectively affect subsets, invalidating conclusions and complicating replication.
   - Fix: Block any GPU runs that involve base model evaluation or data generation unless the script is migrated to `CleanModelLoader`. Alternatively, run a formal A/B equivalence test (see Recommendations) and version‑stamp every artifact with the loader pattern used.

2. Evaluation sample size and statistics insufficient for claims (evaluation design)
   - Description: `scripts/evaluate_instruction_following.py` evaluates a very small bespoke suite (~12 examples) and reports a single success rate without uncertainty or significance testing.
   - Impact: Results are too brittle to support claims (e.g., “base 10–30%, SFT 70–80%, DPO 90–95%”). Noise and prompt idiosyncrasies can dominate.
   - Fix: Expand N and add paired significance tests and effect sizes (details in Recommendations).

### ⚠️ HIGH
1. Contamination verification may yield false positives and is incomplete
   - Files: `scripts/utils/clean_model_loader.py:221`, `scripts/utils/clean_model_loader.py:229`
   - Description: The check inspects only the first ~10 input tokens and flags generic strings like `system/user/assistant` which can legitimately occur in prompts. It does not verify outputs, and does not assert template‑token IDs explicitly.
   - Impact: False alarms or missed contamination if markers appear later; weaker assurance than needed for paper‑level claims.
   - Fix: Verify across all input tokens; check for known special token IDs (e.g., template tokens) rather than generic words; optionally run sentinel prompts and assert failure patterns as a smoke test.

2. Data provenance not fully captured in generated SFT data
   - File: `scripts/generate_stage1_sft_data.py:281`
   - Description: JSONL records lack explicit provenance fields (model id, loader pattern/version, script SHA, seeds, tokenizer settings). Placeholder responses may be mixed in silently if the model fails to load.
   - Impact: Hard to audit or reproduce datasets; training and evaluation comparability weakens.
   - Fix: Add provenance fields per record and forbid mixing placeholder/generated examples without an explicit flag and separate output files.

3. RunPod plan lacks explicit go/no‑go gates tied to migration status
   - File: `docs/RUNPOD_SESSION_PLAN.md:50`
   - Description: Phases reference migrated scripts, but there is no explicit precondition “all base‑model‑touching scripts migrated OR equivalence validated.”
   - Impact: Risk of accidentally running non‑migrated scripts on GPU.
   - Fix: Add a pre‑session gate and phase gates that assert migration completion for the scripts used.

### 💡 SUGGESTIONS
1. Determinism and settings logging for eval
   - File: `scripts/evaluate_instruction_following.py:209`
   - Suggestion: For baseline comparability, default to `temperature=0` (greedy) or fix a sampling seed and log `transformers`, `bitsandbytes`, CUDA, and GPU model. Save all settings in the JSON report.

2. Multiple testing control and effect sizes
   - Suggestion: When reporting by 10–12 instruction types, apply paired tests (McNemar for binary success) with Benjamini–Hochberg correction and report Cohen’s h and Wilson CIs.

3. Cleaner contamination checks
   - File: `scripts/utils/clean_model_loader.py:229`
   - Suggestion: Use tokenizer special token IDs where available; avoid generic word markers; confirm `add_special_tokens=False` consistently; consider a one‑time assert comparing encodings with and without `add_special_tokens` to detect template injection.

4. Automation metric definition
   - Suggestion: Quantify “automation” as the proportion of pipeline tokens/examples generated without human edits, fraction of stages executed unattended, and human minutes per 1k examples. Report with CIs where applicable.

## Verified OK
- DRY policy text is strong and unambiguous (`docs/STANDARDS.md:176`).
- Migration tracker and checklist are practical and aligned with policy (`docs/CLEAN_LOADER_MIGRATION_TODO.md:1`, `docs/REFACTORING_CHECKLIST.md:1`).
- Migrated scripts correctly route all base‑model I/O through `CleanModelLoader` (`scripts/evaluate_instruction_following.py:191`, `scripts/generate_stage1_sft_data.py:119`, `scripts/test_base_model_ultra_clean.py:24`).

## Recommendations
1. Migration policy and gating
   - Block any GPU execution for base model evaluation or data generation unless the exact script is migrated. Alternatively, run an A/B equivalence study on 200 prompts: manual vs `CleanModelLoader`, compute disagreement rate and impact on binary success; proceed only if 95% CI of disagreement is below 1–2% and no systematic bias is found.
   - Add a pre‑session gate in `docs/RUNPOD_SESSION_PLAN.md` requiring “All scripts used in this session touching base model are migrated OR A/B equivalence validated and version‑stamped.”

2. Strengthen contamination verification (`scripts/utils/clean_model_loader.py`)
   - Replace generic string markers with checks on special token IDs or known template fragments specific to Qwen chat templates.
   - Inspect all input tokens, not just the first 10, and optionally assert that `len(tokenizer(prompt, add_special_tokens=True)) == len(tokenizer(prompt, add_special_tokens=False))` for a set of sentinel prompts; any delta indicates template application.
   - Log and include a `loader_version` (git SHA) and `template_disabled=True` flag returned to callers for embedding into artifacts.

3. Evaluation design and statistics (`scripts/evaluate_instruction_following.py`)
   - Increase N: target ≥200 held‑out instructions (stratified by type) to achieve ~±5% Wilson CI on overall rates.
   - Use paired design across models on identical items; apply McNemar tests (base vs SFT, SFT vs DPO) and report p‑values with BH correction across instruction types.
   - Report effect sizes: Cohen’s h for overall and per‑type improvements; include 95% CIs via bootstrap.
   - Determinism: default `temperature=0` for baseline; if sampling, fix RNG and log all library versions; save seeds and decoding params in the JSON.

4. Data provenance and integrity (`scripts/generate_stage1_sft_data.py`)
   - Add per‑record fields: `model_name`, `loader_version`, `script_sha`, `seed`, `tokenizer_add_special_tokens=False`, `template_disabled=True`, `generated_with="clean_model_loader"`.
   - Split outputs by source: separate files for placeholder vs model‑generated; add a CLI flag `--allow-placeholders` default False to avoid mixing silently.
   - Save a dataset manifest with counts, hashes, and generation parameters; store alongside JSONL.

5. RunPod session plan (`docs/RUNPOD_SESSION_PLAN.md`)
   - Add explicit phase gates tied to migration status and an early‑stop condition: if sentinel contamination checks fail or A/B discrepancy >2%, stop and remediate.
   - Add a versions logger step (single script) to write `pip freeze`, `transformers`, `torch`, `bitsandbytes`, CUDA, GPU name, and git SHA into `artifacts/session_versions.json`.

6. Publication clarity (methods section)
   - Document the single implementation rule, the migration completion date, and the contamination verification procedure (including sentinel prompts). Declare evaluation N, success criteria, tests, CIs, effect sizes, and multiple‑testing correction explicitly.

## Overall Assessment
Good direction and strong policy foundation. Methodology is acceptable to proceed conditionally with migrated scripts only, but full migration or A/B validation is required before claiming uniform contamination prevention. Strengthen contamination checks and upgrade evaluation statistics to publication‑quality standards.

