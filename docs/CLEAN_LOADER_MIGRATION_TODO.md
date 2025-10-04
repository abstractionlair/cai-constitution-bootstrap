# CleanModelLoader Migration TODO

**Created**: 2025-10-04
**Status**: IN PROGRESS (3/15 scripts migrated)

---

## Progress

### ✅ Completed (3/15)

1. **evaluate_instruction_following.py** - Migrated in previous session
2. **generate_stage1_sft_data.py** - Migrated in previous session
3. **test_base_model_ultra_clean.py** - Migrated (lines 7-76, tested ✓)
4. **test_clean_base_model.py** - Migrated (lines 7-40, tested ✓)

### ⏳ Remaining (11/15)

5. **test_base_model_definitive.py**
6. **evaluate_capability_differentiation_sequential.py**
7. **evaluate_capability_differentiation.py**
8. **evaluate_stage1_comprehensive.py**
9. **evaluate_stage1_readiness.py**
10. **evaluate_final.py**
11. **evaluate_sft_model.py**
12. **evaluate_stage1_corrected.py**
13. **create_preference_pairs_improved.py**
14. **train_stage1_dpo_improved.py**
15. **train_stage1_sft.py**

---

## Migration Pattern

### Import Changes

**Remove**:
```python
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
```

**Add**:
```python
import sys
from pathlib import Path
from utils.clean_model_loader import CleanModelLoader
```

### Model Loading Changes

**Before** (~40 lines):
```python
tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-32B", ...)
tokenizer.chat_template = None
if hasattr(tokenizer, 'default_chat_template'):
    tokenizer.default_chat_template = None
...
bnb_config = BitsAndBytesConfig(...)
model = AutoModelForCausalLM.from_pretrained(..., quantization_config=bnb_config, ...)
```

**After** (~3 lines):
```python
loader = CleanModelLoader("Qwen/Qwen2.5-32B", load_in_8bit=True)
model, tokenizer = loader.load()
```

### Generation Changes

**Before**:
```python
inputs = tokenizer(prompt, add_special_tokens=False, return_tensors="pt", ...)
outputs = model.generate(**inputs, max_new_tokens=128, temperature=0.7, ...)
response = tokenizer.decode(outputs[0][input_len:], skip_special_tokens=True)
```

**After**:
```python
response = loader.generate(
    model, tokenizer, prompt,
    max_new_tokens=128, temperature=0.7
)
```

---

## Testing Checklist

After migrating each script:

- [ ] Syntax check: `python3 -m py_compile scripts/<script>.py`
- [ ] Verify imports correct
- [ ] Verify no `chat_template = None` remains
- [ ] Verify no `add_special_tokens=False` remains (except in utility itself)
- [ ] Review generation logic replaced correctly

---

## Final Verification

After all scripts migrated:

```bash
# Should return 0 results (except clean_model_loader.py itself)
grep -rn "chat_template = None" scripts/*.py | grep -v clean_model_loader.py

# Should return 0 results (except clean_model_loader.py and archived/)
grep -rn "add_special_tokens=False" scripts/*.py | grep -v clean_model_loader.py | grep -v archived/
```

---

## When Complete

1. Update IMPLEMENTATION_REGISTRY.md:
   - Remove "⚠️ MIGRATION INCOMPLETE"
   - Update to "✅ Complete - All scripts migrated"

2. Update ROADMAP.md:
   - Remove migration blocker warning

3. Commit with message:
   ```
   Complete CleanModelLoader migration (15/15 scripts)

   Migrated all remaining scripts to use centralized CleanModelLoader
   for guaranteed contamination-free base model loading.

   - Migrated: 11 additional scripts (total 15/15)
   - Verified: No manual chat_template disabling remains
   - Tested: All scripts compile successfully

   Eliminates: Duplicate contamination-prevention code across codebase
   Prevents: Future contamination from forgetting safety steps
   See: docs/CLEAN_MODEL_LOADER_MIGRATION.md
   ```

4. Update this file's status to "✅ COMPLETE"

---

## Notes

- Migration is blocking Stage 1 execution (we need clean evaluations)
- Each script ~30-50 lines → ~10 lines (simpler, safer)
- After completion, grep must confirm ZERO manual patterns remain
