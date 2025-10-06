# P3: Add Evaluation Guardrails and Monitoring
**Assigned To**: claude_code

**Source:** Codex Pre-Deployment Review (2025-09-11)
**Priority:** P3 (Low - robustness enhancement)
**Estimated Time:** 30 minutes

## Issue Description

Add guardrails to catch OOM issues early during evaluation and improve monitoring.

## Location

- File: `scripts/evaluate_stage1.py`
- Various methods in `Stage1Evaluator` class

## Suggested Implementation

1. Assert eval batch size = 1 at start of evaluation
2. Log GPU memory at start/end of evaluation
3. Add `--dry-run` flag that loads models and builds eval set without generating
4. Monitor memory during model loading

## Impact

Prevents OOM surprises during expensive GPU runs.

## Success Criteria

- [ ] Batch size assertion added
- [ ] GPU memory logging implemented
- [ ] Dry-run mode available
- [ ] Early OOM detection in place