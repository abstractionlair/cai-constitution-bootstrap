# Review Response: Complete CleanModelLoader Migration - Methodology Impact

**Reviewer**: codex
**Date**: 2025-10-04
**Request**: 20251004_complete_migration_codex.md

## Summary
⚠️ Issues Found

- Migration appears complete and addresses the prior CRITICAL risk of mixed contamination-prevention patterns. Verification script passes and grep finds no manual `chat_template=None` in active scripts. However, a few inconsistencies and documentation mismatches remain. Proceed to GPU with migrated scripts, but fix noted issues and clearly mark pre-migration results as non-comparable.

## Issues Found

### 🚨 CRITICAL
1. Documentation inconsistency on migration status (truth conflict)
   - Files: `ROADMAP.md:42` claims complete; `docs/MIGRATION_STATUS_20251004.md:1` still says 6/15.
   - Impact: Confuses the source of truth; undermines auditability and reviewer confidence.
   - Fix: Update `docs/MIGRATION_STATUS_20251004.md` to reflect 15/15 and align dates/commits, or revert ROADMAP claim until the doc is updated. Single source of truth is required.

### ⚠️ HIGH
1. API mismatch in migrated callers (risk of runtime failures)
   - File: `scripts/evaluate_stage1_comprehensive.py:48-74`
   - Description: Calls `loader.generate(..., stop_strings=[...])`, but `CleanModelLoader.generate` does not accept `stop_strings`. This will error or tempt ad‑hoc generation code paths, re‑introducing divergence.
   - Fix: Standardize on a single `generate` signature (consider adding optional `stop_strings` handling in loader) and update all callers. Avoid per‑script generation tweaks.

2. Manual `add_special_tokens=False` still present in some scripts
   - Files: `scripts/evaluate_instruction_following.py:217`, `scripts/generate_preference_pairs_logprob.py:94`, `scripts/test_ab_logprob_evaluation.py:79,172`, `scripts/train_stage1_sft.py:122-123`.
   - Description: These occur in token counting/processing (not input prompting), but verification script flags them. If any are used for input prompting, they must go through loader.
   - Fix: Confirm these are non‑prompt contexts only. If any are used for input construction, route through `loader.tokenize_clean`.

3. Provenance propagation incomplete in downstream artifacts
   - Files: `scripts/generate_stage1_sft_data.py` (JSONL records), evaluation scripts’ JSON outputs.
   - Description: Loader returns provenance (git SHA, quantization, flags), but many scripts do not persist it into outputs.
   - Fix: Append provenance to evaluation reports and per‑record dataset entries; include script SHA/configs. Recommend a session‑level manifest.

### 💡 SUGGESTIONS
1. Result comparability policy
   - Mark all pre‑migration results as non‑comparable. Add a short note in `status/PROJECT_STATUS.md` and the Methods section describing the migration cutover date and rationale.

2. Verification script enhancements
   - Add a mode that runs 2–3 sentinel prompts via `loader.generate` per script entry point to smoke‑test runtime contamination (not just grep). Keep it fast and optional.

3. Training integration clarity
   - Document when to use `CleanModelLoader` vs Unsloth loader for training. Ensure any base‑model generation during training (e.g., data inspection) routes through `CleanModelLoader`.

4. Evaluation statistics (tracked separately)
   - Increase N (≥200 stratified), paired comparisons across models, McNemar tests with BH correction, report effect sizes (Cohen’s h) and Wilson CIs. Keep this as the next P0 after migration stabilization.

## Verified OK
- Grep and `scripts/verify_migration_complete.sh` indicate no remaining manual `chat_template=None` patterns in active scripts and 16 CleanModelLoader imports.
- `CleanModelLoader` now returns provenance and performs token‑ID and sentinel checks; this addresses previous HIGH concerns about verification coverage.
- Evaluation scripts like `evaluate_final.py` and comprehensive eval now load models exclusively through `CleanModelLoader` and use deterministic decoding where appropriate.

## Recommendations
1. Resolve migration status docs
   - Update `docs/MIGRATION_STATUS_20251004.md` to match ROADMAP, list the final 15/15 scripts, and reference verification output. Alternatively, roll ROADMAP back until the doc is updated. Aim for one canonical status page linked from ROADMAP.

2. Unify generation API
   - Either extend `CleanModelLoader.generate` to support a small set of optional controls (`temperature`, `do_sample`, `stop_strings`), or remove unsupported kwargs from callers. Re‑run a quick compile check (`python -m py_compile scripts/*.py`) to catch stragglers.

3. Provenance persistence
   - Embed `provenance` in all evaluation JSON outputs and SFT JSONL records. Add `script_sha`, `eval_seed`, `decoding_params`, and `loader_version` to top‑level metadata for every artifact.

4. Pre/post migration comparability
   - Create a short “Methodology Change Notice” in `/docs/` and reference it in results. If any pre‑migration numbers will be shown, label them clearly as pre‑migration and avoid direct comparisons.

5. Pre‑GPU gate
   - Add an explicit gate to `docs/RUNPOD_SESSION_PLAN.md` that requires: (a) migration verification pass, (b) quick sentinel runtime check, (c) provenance logging enabled. Halt if any fail.

## Overall Assessment
Complete migration resolves the previous CRITICAL methodological risk. With minor fixes (doc alignment, API consistency, provenance propagation), the pipeline is ready for GPU work. Statistical rigor upgrades remain the next blocking item for publication‑quality claims.

