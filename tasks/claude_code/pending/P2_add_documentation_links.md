# P2: Add Documentation Links to Results

**Priority**: P2 (Low - Documentation improvement)
**Estimated Time**: 15 minutes
**Created**: 2024-12-28 16:40
**Source**: Codex Review 20241228_160000_corrected_p0_implementation.md

## Problem
Evaluation results should include links to methodology documentation to preempt "unfairness" critiques and explain the Stage 1 evaluation philosophy.

## Required Changes

### 1. Add Documentation References to Evaluation Results
In `scripts/evaluate_stage1.py`, update the results summary:

```python
# In save_results or generate final summary
summary = {
    'timestamp': datetime.now().isoformat(),
    'model': self.model_name,
    'stage': 1,
    'methodology_docs': {
        'evaluation_philosophy': 'specs/stage_1_evaluation_philosophy.md',
        'sequential_architecture': 'specs/sequential_bootstrapping_architecture.md', 
        'methodology_clarification': 'specs/METHODOLOGY_CLARIFICATION.md',
        'stage_specifications': 'specs/stage_1_explicit_instructions.md'
    },
    'evaluation_approach': 'Both models evaluated with identical raw instructions to measure instruction-following learning',
    'note': 'Stage 1 focuses on instruction-following capability, not full constitutional AI',
    # ... rest of results
}
```

### 2. Add Methodology Note to Baseline Assessment
In `scripts/baseline_assessment.py`, add documentation links:

```python
# In save_results method
self.results = {
    'model': self.model_name,
    'timestamp': datetime.now().isoformat(),
    'methodology': {
        'approach': 'Raw instructions used to measure baseline instruction-following capability',
        'documentation': 'specs/stage_1_evaluation_philosophy.md',
        'note': 'Expected low success rate for base model - this is not a failure but baseline measurement'
    },
    'categories': category_results,
    # ... rest of results
}
```

### 3. Add Console Output Notices
Add informational messages during evaluation:

```python
# In run_comprehensive_evaluation
logger.info("📋 Evaluation Methodology:")
logger.info("   Both models receive identical raw instructions")
logger.info("   This measures instruction-following learning (Stage 1 goal)")  
logger.info("   See specs/stage_1_evaluation_philosophy.md for details")
logger.info("   Expected: Base model ~50%, Trained model 95%+ success")
```

### 4. Add Methodology Section to Results JSON
Include methodology explanation in all saved results:

```python
methodology_section = {
    'stage_1_goal': 'Teach instruction-following to base model',
    'evaluation_approach': 'Identical raw instructions to both models',
    'expected_pattern': 'Base struggles (~50%), Trained succeeds (95%+)',
    'why_fair': 'Tests exactly what Stage 1 training teaches',
    'documentation': [
        'specs/stage_1_evaluation_philosophy.md',
        'specs/sequential_bootstrapping_architecture.md'
    ],
    'not_full_cai': 'Stage 1 is capability building, full CAI happens in Stage 6'
}
```

## Files to Modify
- `scripts/evaluate_stage1.py` - Add documentation links to results and logging
- `scripts/baseline_assessment.py` - Add methodology notes to baseline results

## Success Criteria
- [ ] All evaluation results include methodology documentation links
- [ ] Console output explains the evaluation approach during runs
- [ ] Results JSON files contain methodology explanation section
- [ ] Clear notes that Stage 1 ≠ full CAI
- [ ] Expected success rate patterns documented in results
- [ ] Links to specific clarification documents included

## Testing
1. Run baseline assessment - verify methodology notes in output and JSON
2. Run stage 1 evaluation - confirm documentation links in results
3. Check that console messages explain the evaluation approach
4. Verify results JSON contains methodology section with doc links
5. Confirm messaging preempts "unfairness" concerns

## Notes
- Helps prevent misunderstanding of evaluation approach
- Documents the rationale behind identical instruction methodology  
- References the comprehensive clarification documents
- Makes the sequential bootstrapping approach clear to reviewers