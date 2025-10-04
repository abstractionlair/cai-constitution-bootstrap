# Review Request: DRY Policy & CleanModelLoader Migration

**Date**: 2025-10-04
**Requester**: claude_code
**Assigned Reviewers**: gemini
**Priority**: High
**Type**: Technical Review (Code Quality, Memory Management, Correctness)

---

## Context

**Problem**: We created `CleanModelLoader` utility to centralize contamination-free base model loading, but only migrated 2/15 scripts initially. This created the "partial refactoring anti-pattern" - having TWO patterns (centralized utility + manual implementations) instead of one.

**User feedback**: "The state we were in after writing the central code but not updating other code to call it is similar to the state we get into when we reimplement rather than reuse existing code."

**Solution**:
1. Establish explicit DRY policy in STANDARDS.md
2. Update agent configs with partial refactoring warnings
3. Complete migration of all scripts to CleanModelLoader
4. Create migration tracking and checklists

---

## Scope of Review

### Committed Work (Since Oct 3)

**Commits to review**:
- `63d8bb5` Migrate critical scripts to use CleanModelLoader
- `c20465e` Add centralized clean model loader
- `c5f311e` Add RunPod automated setup
- `e68bd1b` Complete local preparation for Stage 1
- `b1ce019` Complete local preparation
- `5c21371` Remove old files
- `39d05c1` Major documentation restructuring

**Key files**:
- `scripts/utils/clean_model_loader.py` (NEW - 323 lines)
- `scripts/evaluate_instruction_following.py` (MIGRATED)
- `scripts/generate_stage1_sft_data.py` (MIGRATED)
- `docs/CLEAN_MODEL_LOADER_MIGRATION.md` (NEW - 262 lines)
- `RUNPOD_QUICKSTART.md` (NEW - 195 lines)
- `scripts/runpod_setup.sh` (NEW - 116 lines)
- `docs/RUNPOD_SESSION_PLAN.md` (NEW - 504 lines)

### Current Session Work (Uncommitted)

**New policy documents**:
- `docs/STANDARDS.md` - Added ~180 lines DRY policy section
- `docs/REFACTORING_CHECKLIST.md` (NEW - ~200 lines)
- `docs/CLEAN_LOADER_MIGRATION_TODO.md` (NEW - tracking doc)

**Agent config updates**:
- `CLAUDE.md` - Added partial refactoring warning
- `codex.md` - Added partial refactoring warning
- `GEMINI.md` - Added partial refactoring warning

**Migration progress**:
- `scripts/test_base_model_ultra_clean.py` (MIGRATED - reduced ~40 lines → ~10)
- `scripts/test_clean_base_model.py` (MIGRATED - reduced ~50 lines → ~20)

**Status tracking**:
- `docs/IMPLEMENTATION_REGISTRY.md` - Added migration status
- `ROADMAP.md` - Added blocker warning (4/15 migrated, 11 remaining)

---

## Review Focus Areas

### 1. CleanModelLoader Implementation

**File**: `scripts/utils/clean_model_loader.py`

**Review for**:
- ✅ **Memory management**: Does quantization setup prevent OOM on A100 80GB?
- ✅ **Contamination prevention**: Are all safety checks comprehensive?
- ✅ **Error handling**: Adequate error messages and validation?
- ✅ **Token verification**: Does it catch all contamination markers?
- ✅ **Generation correctness**: Does `generate()` method work correctly?

**Specific checks**:
```python
# Lines 45-65: Quantization config
# Is 8-bit setup correct for 32B model on 80GB GPU?
bnb_config = BitsAndBytesConfig(
    load_in_8bit=True,
    bnb_8bit_use_double_quant=True,
    bnb_8bit_quant_type="nf8",
    bnb_8bit_compute_dtype=torch.bfloat16
)

# Lines 90-110: Template disabling verification
# Are we checking all necessary attributes?
if self.tokenizer.chat_template is not None:
    raise RuntimeError("❌ CRITICAL: Failed to disable chat_template!")

# Lines 150-180: Generation method
# Is input/output length calculation correct?
input_length = inputs['input_ids'].shape[1]
generated_tokens = outputs[0][input_length:]
```

### 2. Migrated Scripts Correctness

**Files**:
- `scripts/evaluate_instruction_following.py`
- `scripts/generate_stage1_sft_data.py`
- `scripts/test_base_model_ultra_clean.py`
- `scripts/test_clean_base_model.py`

**Review for**:
- ✅ **Import correctness**: Are all necessary imports present?
- ✅ **Model loading**: Does `loader.load()` replace all old logic?
- ✅ **Generation logic**: Is `loader.generate()` used correctly?
- ✅ **No manual patterns remain**: Verify no `chat_template = None` or `add_special_tokens=False`
- ✅ **Compilation**: Do all scripts have valid syntax?

**Test**: Run syntax checks
```bash
python3 -m py_compile scripts/test_base_model_ultra_clean.py
python3 -m py_compile scripts/test_clean_base_model.py
```

### 3. Memory Efficiency

**Concern**: Are we duplicating model loading?

**Check**: In scripts like `evaluate_instruction_following.py`:
```python
# Before: Manual loading (~40 lines)
tokenizer = AutoTokenizer.from_pretrained(...)
model = AutoModelForCausalLM.from_pretrained(...)

# After: CleanModelLoader (~3 lines)
loader = CleanModelLoader(...)
model, tokenizer = loader.load()
```

**Question**: Does this introduce any memory overhead? Any unnecessary object retention?

### 4. Edge Cases

**Check for**:
- What if tokenizer doesn't have `default_chat_template` attribute?
- What if model fails to load with quantization?
- What if generation produces empty output?
- What if contamination markers exist in legitimate text?

### 5. RunPod Setup Script

**File**: `scripts/runpod_setup.sh`

**Review for**:
- ✅ **Error handling**: Does it exit on any error (`set -e`)?
- ✅ **GPU verification**: Does it check for CUDA before proceeding?
- ✅ **Dependency completeness**: Are all needed packages installed?
- ✅ **Flash attention handling**: Does it gracefully handle optional dependencies?
- ✅ **Path setup**: Are environment variables set correctly?

### 6. Documentation Completeness

**Files**:
- `docs/CLEAN_MODEL_LOADER_MIGRATION.md`
- `docs/STANDARDS.md` (DRY section)
- `docs/REFACTORING_CHECKLIST.md`

**Review for**:
- Are migration instructions clear enough?
- Do examples match actual code patterns?
- Are verification steps comprehensive?
- Any ambiguities or missing information?

---

## Specific Questions

1. **Memory**: Will CleanModelLoader work reliably on A100 80GB for 32B model?
2. **Safety**: Are contamination checks comprehensive enough?
3. **Migration**: Are the 4 migrated scripts correctly using the loader?
4. **Remaining work**: Any concerns about migrating the other 11 scripts?
5. **Policy**: Is the DRY policy section clear and actionable?
6. **Setup**: Will `runpod_setup.sh` work on a fresh RunPod pod?
7. **Edge cases**: Any scenarios we haven't considered?

---

## Files to Review

### Priority 1 (Critical for GPU work)
- `scripts/utils/clean_model_loader.py`
- `scripts/evaluate_instruction_following.py`
- `scripts/generate_stage1_sft_data.py`
- `scripts/test_base_model_ultra_clean.py`
- `scripts/test_clean_base_model.py`

### Priority 2 (Infrastructure)
- `scripts/runpod_setup.sh`
- `RUNPOD_QUICKSTART.md`
- `docs/RUNPOD_SESSION_PLAN.md`

### Priority 3 (Policy & Process)
- `docs/STANDARDS.md` (DRY section, lines 174-350)
- `docs/REFACTORING_CHECKLIST.md`
- `docs/CLEAN_MODEL_LOADER_MIGRATION.md`
- `CLAUDE.md`, `codex.md`, `GEMINI.md` (warning sections)

---

## Success Criteria

**Review is complete when**:
1. Memory management verified safe for A100 80GB
2. Contamination prevention confirmed comprehensive
3. Migrated scripts confirmed correct
4. Edge cases identified and addressed
5. RunPod setup script verified functional
6. Any critical issues flagged

**Severity levels**:
- 🚨 **CRITICAL**: Blocks GPU work, must fix before deployment
- ⚠️ **HIGH**: Should fix before deployment, has workarounds
- 💡 **SUGGESTIONS**: Nice-to-have improvements

---

## Timeline

**Requested**: 2025-10-04
**Needed by**: Before RunPod deployment (targeting 2025-10-15)
**Blocking**: Stage 1 baseline evaluation and data generation

---

## Additional Context

**Why this matters**:
- We're about to deploy to RunPod and run GPU evaluations
- Contamination would invalidate entire experiment
- Memory issues could waste GPU hours ($1.74/hour)
- Having TWO patterns causes maintenance burden

**What's at stake**:
- Scientific validity of results
- GPU budget (~$20 for Stage 1)
- Timeline for publication
- Codebase maintainability

**User's emphasis**: "I want to improve the policy documents to make the need to implement functionality in exactly one place and share it more salient."

---

Thank you for the review!
