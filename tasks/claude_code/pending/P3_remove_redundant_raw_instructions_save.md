# P3: Remove Redundant raw_instructions.jsonl Save

**Source:** Gemini Pre-Deployment Review (2025-09-10)
**Priority:** P3 (Low - minor cleanup)
**Estimated Time:** 5 minutes

## Issue Description

The script saves `raw_instructions.jsonl` and then immediately saves the exact same data to `train_instructions.jsonl`, creating a redundant file.

## Location

- File: `scripts/generate_stage1_data.py`
- Line: 441

## Suggested Fix

Remove the line that saves `raw_instructions.jsonl` since `train_instructions.jsonl` serves the same purpose.

## Impact

Negligible - just creates duplicate files.

## Success Criteria

- [ ] Remove redundant save operation
- [ ] Verify only `train_instructions.jsonl` is saved