# P0: Implement Persistent Held-Out Evaluation Set

**Priority**: P0 (CRITICAL - Blocking valid results)
**Estimated Time**: 45 minutes
**Created**: 2024-12-28 16:30
**Source**: Codex Review 20241228_160000_corrected_p0_implementation.md

## Problem
The persistent held-out eval set is not actually implemented in the code. The evaluation still regenerates eval sets each time, allowing cross-run data leakage and preventing paired statistical analysis.

## Current Issue
```python
# Current code in evaluate_stage1.py still does:
eval_set = self.generate_evaluation_set(eval_set_size)  # Regenerates each time!

# The functions create_held_out_eval_set() and verify_no_leakage() exist but aren't used
```

## Required Implementation

### 1. Fix generate_evaluation_set Method
In `scripts/evaluate_stage1.py`, update to actually use persistence:

```python
def generate_evaluation_set(self, size: int = 200) -> List[Dict[str, Any]]:
    """Get persistent held-out evaluation set (load if exists, create if not)"""
    
    eval_file = BASE_DIR / "data" / "stage1" / "eval_instructions.jsonl"
    
    if eval_file.exists():
        logger.info("📚 Loading existing persistent evaluation set")
        eval_instructions = load_jsonl(eval_file)
        
        # Verify no leakage (critical check)
        if not verify_no_leakage():
            raise ValueError("Data leakage detected in persistent eval set")
        
        # Use requested size or all available
        final_set = eval_instructions[:size] if len(eval_instructions) >= size else eval_instructions
        logger.info(f"✅ Using {len(final_set)} persistent evaluation examples")
        
    else:
        logger.info("🔒 Creating new persistent evaluation set")
        final_set = create_held_out_eval_set(size)
        logger.info(f"✅ Created and saved {len(final_set)} persistent evaluation examples")
    
    return final_set
```

### 2. Ensure Training Instructions Are Saved
Verify that `scripts/generate_stage1_data.py` actually saves training instructions:

```python
# In save_data method - this should already be implemented
train_instructions_file = self.data_dir / "train_instructions.jsonl" 
save_jsonl(instructions, train_instructions_file)
logger.info(f"🔒 Saved {len(instructions)} training instructions for leakage prevention")
```

### 3. Add Overlap Report Generation
In the `create_held_out_eval_set` function, enhance the overlap report:

```python
# Create detailed overlap report
overlap_report = {
    'timestamp': datetime.now().isoformat(),
    'train_count': len(train_instructions),
    'eval_count': len(final_eval_set),
    'overlap_count': 0,  # Should always be 0
    'eval_seed': 12345,
    'generation_attempts': attempts,
    'train_file_hash': hashlib.md5(str(sorted(train_instructions)).encode()).hexdigest(),
    'eval_file_hash': hashlib.md5(str(sorted([x['instruction'] for x in final_eval_set])).encode()).hexdigest()
}
```

### 4. Add Persistent Eval Set Documentation
Add logging to confirm persistence:

```python
# In run_comprehensive_evaluation
logger.info("🔒 Using persistent held-out evaluation set for paired analysis")
logger.info(f"📊 Eval set file: {eval_file}")
logger.info(f"🔍 Overlap report: {BASE_DIR / 'data' / 'stage1' / 'overlap_report.json'}")
```

## Files to Modify
- `scripts/evaluate_stage1.py` - Fix generate_evaluation_set to use persistence
- `scripts/generate_stage1_data.py` - Verify training instruction saving
- Enhance overlap reporting in create_held_out_eval_set

## Success Criteria
- [ ] Evaluation always uses the same persistent eval set file
- [ ] Training instructions saved to `train_instructions.jsonl`
- [ ] Eval instructions saved to `eval_instructions.jsonl` 
- [ ] Overlap report generated with 0 overlaps confirmed
- [ ] verify_no_leakage() called and passes on every evaluation
- [ ] Same eval set used for both base and trained model evaluation
- [ ] File hashes included in overlap report for verification

## Testing
1. Generate training data (should save train_instructions.jsonl)
2. Run evaluation (should create persistent eval_instructions.jsonl)
3. Run evaluation again (should load same eval set, not regenerate)
4. Verify overlap_report.json shows 0 overlaps
5. Confirm eval set file hashes are consistent

## Notes
This is the **critical blocker** identified by Codex. Without persistent eval sets:
- Cross-run data leakage can occur
- Paired statistical analysis is invalid  
- Results cannot be compared across model versions
- Scientific validity is compromised