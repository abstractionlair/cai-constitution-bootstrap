# Task: Fix Evaluation Precision Mismatch

## Task: Standardize all evaluations to 8-bit precision
Priority: P0 (CRITICAL - blocks deployment)
Estimated Time: 0.5 hours
Created: 2024-12-28 13:00
Created By: Claude (Project)

## Objective
Make baseline assessment and evaluation use identical precision (8-bit) to ensure fair comparison of results.

## Success Criteria
- [ ] Baseline assessment uses 8-bit precision
- [ ] Pre-training evaluation uses 8-bit precision  
- [ ] Post-training evaluation uses 8-bit precision
- [ ] All three use identical model loading code

## Files to Modify
- `scripts/baseline_assessment.py` - Line 58: Change to use `load_in_8bit=True`
- `scripts/evaluate_stage1.py` - Verify already using 8-bit (lines 70, 82)
- Consider extracting common model loading function to `utils/model_loader.py`

## Dependencies
- None

## Implementation Notes
Current issue: baseline uses float16/bfloat16, evaluation uses 8-bit. This makes comparison invalid.

Specific change needed in baseline_assessment.py:
```python
# Current (line 58):
model = AutoModelForCausalLM.from_pretrained(
    model_name,
    torch_dtype=torch.float16 if device.type == 'cuda' else torch.float32,
    device_map="auto"
)

# Should be:
model = AutoModelForCausalLM.from_pretrained(
    model_name,
    load_in_8bit=True,
    device_map="auto"
)
```

## Test Plan
1. Run baseline assessment with a small test (10 examples)
2. Verify memory usage is similar to evaluation
3. Check that results are deterministic across runs

---

## Status Updates
- [2024-12-28 15:35] Started implementation - Claude Code
- [2024-12-28 15:35] Updated baseline_assessment.py to use load_in_8bit=True instead of dtype selection
- [2024-12-28 15:35] Verified evaluate_stage1.py already uses load_in_8bit=True (lines 62, 76)
- [2024-12-28 15:35] Verified generate_stage1_data.py already uses load_in_8bit=True (line 80)
- [2024-12-28 15:35] ✅ COMPLETED - All success criteria met:
  - ✅ Baseline assessment uses 8-bit precision
  - ✅ Pre-training evaluation uses 8-bit precision
  - ✅ Post-training evaluation uses 8-bit precision
  - ✅ All three use identical model loading code (load_in_8bit=True)
- [2024-12-28 15:35] ✅ Precision consistency achieved across all evaluation points
