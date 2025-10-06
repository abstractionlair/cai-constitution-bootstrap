# Task: Change nf8 to nf4 in CleanModelLoader

**Priority**: P3 (LOW - Minor optimization)
**Created**: 2025-10-04
**Assigned To**: claude_code
**Status**: Pending
**From Review**: reviews/responses/20251004_dry_policy_and_migration_gemini.md

---

## Problem

CleanModelLoader uses `nf8` for 8-bit quantization. While valid, `nf4` is generally recommended even for 8-bit quantization as it can be more expressive.

**Gemini finding** (SUGGESTION):
> "The current 8-bit config uses `bnb_8bit_quant_type="nf8"`. While valid, the `nf4` data type is generally recommended even for 8-bit quantization as it can be more expressive. The difference is likely minor, but it's worth considering for consistency with the 4-bit config's `nf4`."

---

## Impact

- **Minor performance**: Potentially slightly better quantization quality
- **Consistency**: Matches 4-bit config (already uses nf4)
- **Best practices**: Aligns with BitsAndBytes recommendations

---

## Current Code

**File**: `scripts/utils/clean_model_loader.py`
**Line**: ~130

```python
quantization_config = BitsAndBytesConfig(
    load_in_8bit=True,
    bnb_8bit_use_double_quant=True,
    bnb_8bit_quant_type="nf8",  # ← Change this
    bnb_8bit_compute_dtype=torch.bfloat16
)
```

---

## Solution

Change one line:

```python
quantization_config = BitsAndBytesConfig(
    load_in_8bit=True,
    bnb_8bit_use_double_quant=True,
    bnb_8bit_quant_type="nf4",  # ← Changed from nf8
    bnb_8bit_compute_dtype=torch.bfloat16
)
```

---

## Testing

**Minimal impact**: Quantization config change shouldn't affect functionality, only quality

**Quick test**:
```bash
python3 scripts/test_clean_base_model.py
```

Should still work correctly.

---

## Completion Criteria

- [ ] Change nf8 → nf4 in CleanModelLoader (line ~130)
- [ ] Test script still works
- [ ] Update any comments mentioning nf8

---

## References

- reviews/responses/20251004_dry_policy_and_migration_gemini.md - Gemini review (SUGGESTION #1)
- scripts/utils/clean_model_loader.py - File to update
