# Task: Complete CleanModelLoader Migration

**Priority**: P0 (CRITICAL - Blocks GPU work)
**Created**: 2025-10-04
**Assigned To**: claude_code
**Status**: Pending
**From Review**: reviews/responses/20251004_dry_policy_and_migration_codex.md

---

## Problem

Only 4/15 scripts have migrated to CleanModelLoader. Mixed contamination-prevention patterns compromise methodological consistency and reproducibility.

**Codex finding** (CRITICAL #1):
> "Mixed usage breaks the 'single source of truth' and undermines claims of uniform contamination prevention. Results across scripts may not be comparable; contamination bugs could selectively affect subsets."

---

## Impact

- **Scientific validity**: Results not comparable across mixed-pattern scripts
- **Reproducibility**: Cannot claim uniform methodology in paper
- **Timeline**: Blocks all GPU evaluation and data generation work

---

## Remaining Scripts (11/15)

1. test_base_model_definitive.py
2. evaluate_capability_differentiation_sequential.py
3. evaluate_capability_differentiation.py
4. evaluate_stage1_comprehensive.py
5. evaluate_stage1_readiness.py
6. evaluate_final.py
7. evaluate_sft_model.py
8. evaluate_stage1_corrected.py
9. create_preference_pairs_improved.py
10. train_stage1_dpo_improved.py
11. train_stage1_sft.py

---

## Solution

Migrate all 11 remaining scripts to use CleanModelLoader.

**For each script**:
1. Import CleanModelLoader
2. Replace manual model loading (~30-40 lines) with loader.load() (~3 lines)
3. Replace manual generation with loader.generate()
4. Test compilation
5. Verify no manual patterns remain

**Migration pattern** (see docs/CLEAN_MODEL_LOADER_MIGRATION.md):

**Before**:
```python
tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-32B")
tokenizer.chat_template = None
if hasattr(tokenizer, 'default_chat_template'):
    tokenizer.default_chat_template = None
...
model = AutoModelForCausalLM.from_pretrained(...)
```

**After**:
```python
from utils.clean_model_loader import CleanModelLoader
loader = CleanModelLoader("Qwen/Qwen2.5-32B", load_in_8bit=True)
model, tokenizer = loader.load()
```

---

## Verification

After migration:

```bash
# Should return 0 (except clean_model_loader.py itself)
grep -rn "chat_template = None" scripts/*.py | grep -v clean_model_loader.py | grep -v archived/

# Should return 0 (except clean_model_loader.py itself)
grep -rn "add_special_tokens=False" scripts/*.py | grep -v clean_model_loader.py | grep -v archived/

# All scripts should compile
for f in scripts/*.py; do python3 -m py_compile "$f" || echo "FAILED: $f"; done
```

---

## Completion Criteria

- [ ] All 11 scripts migrated
- [ ] All 15 scripts compile successfully
- [ ] Grep confirms no manual patterns remain
- [ ] IMPLEMENTATION_REGISTRY updated (migration complete)
- [ ] ROADMAP blocker removed
- [ ] CLEAN_LOADER_MIGRATION_TODO.md marked complete

---

## References

- docs/CLEAN_MODEL_LOADER_MIGRATION.md - Migration guide
- docs/CLEAN_LOADER_MIGRATION_TODO.md - Progress tracker
- docs/REFACTORING_CHECKLIST.md - Process checklist
- reviews/responses/20251004_dry_policy_and_migration_codex.md - Codex review
