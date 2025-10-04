# CleanModelLoader Migration Status - 2025-10-04

**Current Progress**: 6/15 scripts migrated (40%)
**Blocking**: GPU deployment until complete
**Commits**: 2 commits made and ready to push

---

## ✅ Completed (6/15)

### Scripts Migrated:
1. ✅ **evaluate_instruction_following.py** - Updated to handle provenance 3-tuple
2. ✅ **generate_stage1_sft_data.py** - Updated to handle provenance 3-tuple
3. ✅ **test_base_model_ultra_clean.py** - Updated to handle provenance 3-tuple
4. ✅ **test_clean_base_model.py** - Updated to handle provenance 3-tuple
5. ✅ **test_base_model_definitive.py** - Fully migrated (load + generate methods)

### CleanModelLoader Improvements (Complete):
- ✅ Changed nf8 → nf4 (Gemini suggestion)
- ✅ Check ALL tokens, not just first 10 (Codex HIGH #1)
- ✅ Use token IDs instead of strings (QWEN_CHAT_TOKEN_IDS)
- ✅ Added sentinel prompt tests (_verify_no_template_injection)
- ✅ Added provenance tracking (git SHA, quantization, etc.)
- ✅ load() returns (model, tokenizer, provenance) 3-tuple

### Infrastructure Created:
- ✅ scripts/verify_migration_complete.sh - Grep-based verification
- ✅ scripts/log_session_versions.py - Environment logging for reproducibility

### Documentation:
- ✅ DRY policy added to STANDARDS.md (~180 lines)
- ✅ REFACTORING_CHECKLIST.md created (6-phase process)
- ✅ All 3 agent configs updated with warnings
- ✅ ROADMAP.md updated with blocker (6/15 status)
- ✅ IMPLEMENTATION_REGISTRY.md updated with migration status

### Tasks Created:
- ✅ 20251004_P0_complete_clean_loader_migration.md
- ✅ 20251004_P0_upgrade_evaluation_statistics.md (deferred)
- ✅ 20251004_P1_fix_contamination_verification.md (done)
- ✅ 20251004_P1_add_provenance_tracking.md (partial - loader done, data gen pending)
- ✅ 20251004_P1_add_migration_gates_to_runpod_plan.md (scripts created, plan update pending)
- ✅ 20251004_P3_change_nf8_to_nf4.md (done)

---

## ⏳ Remaining (9/15)

### Scripts to Migrate:
1. ❌ **evaluate_sft_model.py** - Has load_base_model() and load_sft_model()
2. ❌ **evaluate_final.py**
3. ❌ **evaluate_stage1_comprehensive.py**
4. ❌ **evaluate_stage1_readiness.py**
5. ❌ **evaluate_stage1_corrected.py**
6. ❌ **evaluate_capability_differentiation.py**
7. ❌ **evaluate_capability_differentiation_sequential.py**
8. ❌ **create_preference_pairs_improved.py**
9. ❌ **train_stage1_sft.py** - May use Unsloth, verify if needs migration
10. ❌ **train_stage1_dpo_improved.py** - May use Unsloth, verify if needs migration

**Note**: Training scripts (train_stage1_*) may intentionally use model_loader.py (Unsloth) instead of CleanModelLoader. Verify which loader is appropriate.

### Migration Pattern for Each Script:

**Step 1: Update imports**
```python
# Remove:
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig

# Add:
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from utils.clean_model_loader import CleanModelLoader
```

**Step 2: Replace model loading** (~40 lines → ~3 lines)
```python
# OLD:
tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-32B", ...)
tokenizer.chat_template = None
if hasattr(tokenizer, 'default_chat_template'):
    tokenizer.default_chat_template = None
bnb_config = BitsAndBytesConfig(...)
model = AutoModelForCausalLM.from_pretrained(..., quantization_config=bnb_config, ...)

# NEW:
loader = CleanModelLoader("Qwen/Qwen2.5-32B", load_in_8bit=True)
model, tokenizer, provenance = loader.load()
logger.info(f"📋 Loader version: {provenance['loader_version'][:8]}")
```

**Step 3: Replace generation** (~20 lines → ~5 lines)
```python
# OLD:
inputs = tokenizer(prompt, add_special_tokens=False, return_tensors="pt", ...)
outputs = model.generate(**inputs, max_new_tokens=128, temperature=0.7, ...)
response = tokenizer.decode(outputs[0][input_len:], skip_special_tokens=True)

# NEW:
response = loader.generate(model, tokenizer, prompt, max_new_tokens=128, temperature=0.7)
```

**Step 4: Test compilation**
```bash
python3 -m py_compile scripts/script_name.py
```

---

## Remaining Tasks

### High Priority (P1):
1. **Add per-record provenance to generate_stage1_sft_data.py**
   - Status: Loader provides provenance, but script doesn't add to JSONL records yet
   - Needs: Add provenance dict to each generated example
   - See: tasks/claude_code/pending/20251004_P1_add_provenance_tracking.md

2. **Add RunPod plan gates**
   - Status: Scripts created (verify_migration_complete.sh, log_session_versions.py)
   - Needs: Update docs/RUNPOD_SESSION_PLAN.md with pre-session gates and phase gates
   - See: tasks/claude_code/pending/20251004_P1_add_migration_gates_to_runpod_plan.md

### After All Migrations:
3. **Final verification**
   ```bash
   # Should return 0
   grep -rn "chat_template = None" scripts/*.py | grep -v clean_model_loader.py | grep -v archived/

   # Should return 0
   grep -rn "add_special_tokens=False" scripts/*.py | grep -v clean_model_loader.py | grep -v archived/

   # All should compile
   for f in scripts/*.py; do python3 -m py_compile "$f" || echo "FAILED: $f"; done
   ```

4. **Update documentation**
   - IMPLEMENTATION_REGISTRY.md: Change status to "✅ Complete - All 15 scripts migrated"
   - ROADMAP.md: Remove blocker warning
   - CLEAN_LOADER_MIGRATION_TODO.md: Mark complete

5. **Final commit**
   ```
   Complete CleanModelLoader migration (15/15 scripts)

   All base model scripts now use centralized CleanModelLoader.
   No manual contamination prevention patterns remain.
   ```

6. **Archive reviews**
   - Move reviews/requests/20251004*.md to archive/20251004_review_cycle/requests/
   - Move reviews/responses/20251004*.md to archive/20251004_review_cycle/responses/

### Deferred (P0 but large scope):
7. **Upgrade evaluation statistics** (Codex CRITICAL #2)
   - Separate dedicated session needed
   - Increase N from 12 → 200+ examples
   - Add statistical tests, effect sizes, CIs
   - See: tasks/claude_code/pending/20251004_P0_upgrade_evaluation_statistics.md

---

## Commits Made

**Commit 1** (0ed5c8a):
```
Fix CleanModelLoader contamination verification and add provenance tracking
- Core loader improvements
- 4 scripts updated to handle provenance
```

**Commit 2** (4f0f336):
```
Add DRY policy, create review tasks, and progress migration (6/15 scripts)
- DRY policy in STANDARDS.md
- 6 tasks created from reviews
- Infrastructure scripts created
- 1 additional script migrated
```

**Ready to push**: Yes, both commits ready

---

## Next Session Plan

1. Migrate remaining 9 scripts (systematic, ~30-60 min)
2. Add provenance to generate_stage1_sft_data.py (~15 min)
3. Update RUNPOD_SESSION_PLAN.md with gates (~15 min)
4. Run verification checks (~5 min)
5. Update docs (~10 min)
6. Final commit and push (~5 min)
7. Archive reviews (~5 min)

**Total estimated time**: 1.5-2 hours

---

## Key Files Modified (Not Yet Committed)

None - all work committed.

## Key Files To Create/Modify (Next Session)

**To Modify**:
- 9 remaining scripts (see list above)
- generate_stage1_sft_data.py (add per-record provenance)
- docs/RUNPOD_SESSION_PLAN.md (add gates)
- docs/IMPLEMENTATION_REGISTRY.md (mark complete)
- ROADMAP.md (remove blocker)
- docs/CLEAN_LOADER_MIGRATION_TODO.md (mark complete)

**To Create**:
- archive/20251004_review_cycle/ (directory structure)

---

## Migration Verification Checklist

Before considering migration complete:

- [ ] All 15 scripts migrated (currently 6/15)
- [ ] All 15 scripts compile successfully
- [ ] `grep -rn "chat_template = None" scripts/*.py` returns 0 (excluding loader and archived)
- [ ] `grep -rn "add_special_tokens=False" scripts/*.py` returns 0 (excluding loader and archived)
- [ ] `scripts/verify_migration_complete.sh` exits 0
- [ ] IMPLEMENTATION_REGISTRY updated
- [ ] ROADMAP blocker removed
- [ ] CLEAN_LOADER_MIGRATION_TODO.md marked complete
- [ ] Reviews archived

---

**Status**: Ready to continue migration in next session
**Blocker**: 9 scripts remaining before GPU deployment
