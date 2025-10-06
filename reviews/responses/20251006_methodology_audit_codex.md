# Methodology Audit Response (Consolidated)

**Reviewer**: codex
**Date**: 2025-10-06
**Request**: 20251006_methodology_audit.md

---

## Severity Summary
- **Critical**: 2
- **High**: 4
- **Medium**: 0
- **Low**: 0

---

## Priority Recommendations
1. **Fix pipeline orchestration** (Finding 1): Update the Stage‑1 pipeline to invoke the modern data/critique scripts before any further runs.
2. **Harden the preference-pair generator** (Finding 2): Enforce `CleanModelLoader`, reuse the shared log‑prob critic, and regenerate the DPO dataset.
3. **Modernise SFT data generation** (Finding 3): Replace the template/placeholder flow with the model-generated + logprob-filtered pipeline (`instruction_generator` + `instruction_critic`).
4. **Implement Best-of-N with hard negatives** (Finding 4): Extend the preference data pipeline to follow the documented BoN + hard-negative strategy before any DPO training.
5. **Add gating + contamination safeguards** (Findings 5 & 6): Block SFT/DPO trainers on new QC’d datasets and ensure every evaluation script uses `CleanModelLoader`.

---

### Finding 1: Pipeline still invokes deprecated Stage‑1 generator
**File:Line**: scripts/run_stage1_pipeline.py:203

**Issue**: The pipeline’s “Data Generation” step executes `generate_stage1_data.py`, which now exists only as `.DEPRECATED` (retired for chat-template contamination). Any end-to-end run fails or regresses to the pre-migration, broken flow.

**Expected**: Pipeline orchestration should call the maintained components—model-generated instruction pipeline, logprob-based filtering, and the cleaned preference builder (e.g. `generate_sample_data_v2.py`, the refactored SFT generator, the updated preference script).

**Actual**: The deprecated script name remains hard-coded, so a “pipeline” run either crashes or executes the contaminated path if someone restores the file.

**Impact**: [x] Critical – invalidates end-to-end runs and risks reintroducing the contamination bug.

**Recommendation**: Replace the Step‑2 call with the vetted components, remove references to the deprecated script, and add a smoke test that fails fast if the modern scripts are missing.

**Related Files**: scripts/generate_stage1_data.py.DEPRECATED, docs/IMPLEMENTATION_REGISTRY.md:303

---

### Finding 2: Preference-pair generator bypasses CleanModelLoader and duplicates critic logic
**File:Line**: scripts/generate_preference_pairs_logprob.py:65-190

**Issue**: The script reimplements model loading and single-token logprob scoring, ignoring `CleanModelLoader` (chat-template guard) and the shared `instruction_critic` helpers—reviving the contamination risk and diverging judgement logic.

**Expected**: All base-model loads must go through `CleanModelLoader`; A/B logprob evaluation should reuse `instruction_critic.get_token_logprobs` / `critique_instruction_response_pair` for consistency.

**Actual**: `AutoTokenizer.from_pretrained()` is called directly (`add_special_tokens=True`), no `chat_template=None`, and bespoke logprob code duplicates core functionality.

**Impact**: [x] Critical – corrupts the preference dataset and undermines DPO training.

**Recommendation**: Remove `load_model_with_retry`, depend on `CleanModelLoader`, import the critic utility, and add sentinel contamination checks before sampling pairs. Add a unit/CI guard that fails if any active script reintroduces manual chat-template toggling.

**Related Files**: scripts/utils/clean_model_loader.py, scripts/utils/instruction_critic.py, docs/BASE_MODEL_TRUTH.md

---

### Finding 3: Primary SFT generator still template-driven, missing logprob QC
**File:Line**: scripts/generate_stage1_sft_data.py:28-320

**Issue**: The “main” SFT generator fabricates instructions from a small template list and falls back to placeholder paragraphs when generation fails. It never calls the new model-generated instruction pipeline nor the logprob-based critic we committed to use.

**Expected**: Stage‑1 data generation should leverage `InstructionGenerator.generate_instructions_in_batches` and filter instructions/responses with `instruction_critic` before assembling training examples.

**Actual**: Templates and placeholders dominate; the unused `instruction_generator.py` / `instruction_critic.py` show divergence between spec and implementation.

**Impact**: [x] High – produces low-diversity, low-quality data inconsistent with the documented methodology.

**Recommendation**: Integrate `InstructionGenerator` for instruction creation, apply `critique_instruction_quality` / `critique_instruction_response_pair` (with QC metrics and reject/regenerate loops), and emit provenance/QC summaries so trainers can gate on data quality. Deprecate the placeholder branch once the new flow is stable.

**Related Files**: scripts/utils/instruction_generator.py, scripts/utils/instruction_critic.py, scripts/generate_sample_data_v2.py

---

### Finding 4: Preference data lacks Best-of-N sampling and hard negatives
**File:Line**: scripts/generate_preference_pairs_logprob.py (overall)

**Issue**: The DPO dataset builder samples a single response per instruction and pairs it against templated “bad” replies, contrary to the documented best practices (BoN sampling + hard negatives).

**Expected** (docs/POST_TRAINING_APPROACHES.md): Sample k candidates per instruction, use logprob margins to pick the best, create k‑1 pairs against the remaining candidates, and include diverse hard-negative types.

**Actual**: Only one candidate is sampled; negatives are boilerplate (“I cannot help with that request”), giving limited learning signal.

**Impact**: [x] High – undermines DPO effectiveness and wastes GPU cycles.

**Recommendation**: Extend the script to accept `k`, sample with non-zero temperature, select the best via the logprob judge, and form pairs against the remaining candidates plus curated hard negatives. Track margins/confidence, filter low-quality pairs, and regenerate the dataset once implemented.

**Related Files**: docs/POST_TRAINING_APPROACHES.md, scripts/generate_diverse_negatives.py

---

### Finding 5: Training scripts lack gating on clean datasets
**File:Line**: scripts/train_stage1_sft.py & scripts/train_stage1_dpo_improved.py (usage pattern)

**Issue**: The training scripts are sound, but nothing prevents them from being launched on legacy/template data or contaminated pairs. Given Findings 1‑4, running them now would waste compute and produce invalid models.

**Expected**: Trainers should run only after the refactored data pipeline emits high-quality artefacts with QC manifests.

**Actual**: The pipeline (and ad-hoc runs) can call these trainers even if only template-based or contaminated data exists.

**Impact**: [x] High – high risk of expending budget on bad data.

**Recommendation**: Add gating (in pipeline and/or scripts) that checks for the new QC manifests (e.g. instruction/pair acceptance rates, contamination checks) before proceeding. Document this requirement in the IMPLEMENTATION_REGISTRY and enforce via CI or a helper script.

**Related Files**: scripts/run_stage1_pipeline.py, docs/POST_TRAINING_APPROACHES.md, docs/IMPLEMENTATION_REGISTRY.md

---

### Finding 6: Simple evaluation script reloads models without contamination guard
**File:Line**: scripts/evaluate_stage1_simple.py:34-107

**Issue**: The “simple” evaluation script manually loads models/tokenizer without `CleanModelLoader`, reintroducing the chat-template contamination risk in quick evaluations.

**Expected**: All base-model evaluation scripts must use `CleanModelLoader` to guarantee `chat_template=None` and consistent tokenisation.

**Actual**: The script calls `AutoTokenizer.from_pretrained()` / `AutoModelForCausalLM.from_pretrained()` directly and never disables chat templates.

**Impact**: [x] High – quick evaluation runs may report inflated performance due to contamination, undermining trust in metrics.

**Recommendation**: Swap to `CleanModelLoader` (mirroring comprehensive evaluation scripts) and add a regression test/grep check ensuring no active script loads the base model manually.

**Related Files**: docs/BASE_MODEL_TRUTH.md, scripts/evaluate_stage1_comprehensive.py

---

## Methodology Gaps
- **Data generation vs. docs**: Specs and POST_TRAINING_APPROACHES call for completion-based instruction generation, logprob critiques, Best-of-N sampling, and hard negatives; current “mainline” scripts still rely on templates, placeholders, and single-sample judging.
- **Utility reuse**: Newly introduced utilities (`instruction_critic`, `instruction_generator`, `CleanModelLoader`) are not consistently adopted, leading to reimplementation drift and regression risks.
- **Pipeline orchestration**: The official pipeline doesn’t execute the documented stages; it references deprecated components and lacks gating on QC artefacts.

Addressing Findings 1‑6 brings the codebase in line with the intended Stage‑1 methodology and ensures we collect high-quality data before committing to the 15k-sample generation.
