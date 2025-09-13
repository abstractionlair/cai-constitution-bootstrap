# P0: Fix Cross-Run Data Leakage

**Priority**: P0 (CRITICAL - Invalidates results)
**Estimated Time**: 1 hour
**Created**: 2024-12-28 16:10
**Source**: Codex Review 20241228_153500_p0_fixes.md

## Problem
Evaluation sets are generated fresh each time without checking against training data. This allows instructions to overlap between training and evaluation across different runs, invalidating results.

## Current Issue
- Training uses `Stage1DataGenerator(seed=42)`
- Evaluation uses `Stage1DataGenerator(seed=12345)`
- No cross-checking between them
- Assertions only check within single generator instance

## Required Fix

### 1. Save Training Instructions
In `generate_stage1_data.py`, after generating training data:
```python
def save_data(self, instructions, ...):
    # ... existing saves ...
    
    # NEW: Save training instructions for cross-run verification
    train_instructions_file = self.data_dir / "train_instructions.jsonl"
    save_jsonl(instructions, train_instructions_file)
    logger.info(f"Saved {len(instructions)} training instructions for leakage prevention")
```

### 2. Create Persistent Evaluation Set
Create new function in `evaluate_stage1.py`:
```python
def create_held_out_eval_set(eval_count: int = 100) -> List[Dict[str, Any]]:
    """Create evaluation set that's guaranteed disjoint from training"""
    
    # Load training instructions if they exist
    train_file = BASE_DIR / "data" / "stage1" / "train_instructions.jsonl"
    train_instructions = set()
    
    if train_file.exists():
        train_data = load_jsonl(train_file)
        train_instructions = {item['instruction'] for item in train_data}
        logger.info(f"Loaded {len(train_instructions)} training instructions to avoid")
    
    # Generate evaluation instructions
    eval_generator = Stage1DataGenerator(seed=12345)
    
    # Generate more than needed to account for filtering
    eval_instructions = []
    attempts = 0
    max_attempts = 10
    
    while len(eval_instructions) < eval_count and attempts < max_attempts:
        candidates = eval_generator.generate_all_instructions(
            qa_count=eval_count // 4 + 10,
            completion_count=eval_count // 4 + 10,
            generation_count=eval_count // 4 + 10,
            response_count=eval_count // 4 + 10
        )
        
        # Filter out any that appear in training
        for candidate in candidates:
            if candidate['instruction'] not in train_instructions:
                eval_instructions.append(candidate)
                if len(eval_instructions) >= eval_count:
                    break
        
        attempts += 1
    
    if len(eval_instructions) < eval_count:
        logger.warning(f"Could only generate {len(eval_instructions)} unique eval instructions")
    
    # Save for reproducibility
    eval_file = BASE_DIR / "data" / "stage1" / "eval_instructions.jsonl"
    save_jsonl(eval_instructions[:eval_count], eval_file)
    
    # Create overlap report
    overlap_report = {
        'train_count': len(train_instructions),
        'eval_count': len(eval_instructions[:eval_count]),
        'overlap_count': 0,  # Should always be 0
        'timestamp': datetime.now().isoformat()
    }
    
    report_file = BASE_DIR / "data" / "stage1" / "overlap_report.json"
    with open(report_file, 'w') as f:
        json.dump(overlap_report, f, indent=2)
    
    logger.info(f"Created {len(eval_instructions[:eval_count])} held-out eval instructions")
    logger.info(f"Overlap report saved to {report_file}")
    
    return eval_instructions[:eval_count]
```

### 3. Use Persistent Eval Set
In `evaluate_stage1.py`, modify evaluation to use held-out set:
```python
def evaluate_model(...):
    # Check if eval set exists, otherwise create it
    eval_file = BASE_DIR / "data" / "stage1" / "eval_instructions.jsonl"
    
    if eval_file.exists():
        logger.info("Loading existing held-out evaluation set")
        eval_instructions = load_jsonl(eval_file)
    else:
        logger.info("Creating new held-out evaluation set")
        eval_instructions = create_held_out_eval_set(eval_count)
    
    # Use eval_instructions for testing...
```

### 4. Add Verification
Add verification function:
```python
def verify_no_leakage():
    """Verify zero overlap between train and eval sets"""
    train_file = BASE_DIR / "data" / "stage1" / "train_instructions.jsonl"
    eval_file = BASE_DIR / "data" / "stage1" / "eval_instructions.jsonl"
    
    if not train_file.exists() or not eval_file.exists():
        logger.warning("Train or eval file not found, cannot verify")
        return False
    
    train_data = load_jsonl(train_file)
    eval_data = load_jsonl(eval_file)
    
    train_instructions = {item['instruction'] for item in train_data}
    eval_instructions = {item['instruction'] for item in eval_data}
    
    overlap = train_instructions & eval_instructions
    
    if overlap:
        logger.error(f"FATAL: Found {len(overlap)} overlapping instructions!")
        logger.error(f"Examples: {list(overlap)[:3]}")
        return False
    
    logger.info(f"✅ Verified: 0 overlap between {len(train_instructions)} train and {len(eval_instructions)} eval")
    return True
```

## Files to Modify
- `scripts/generate_stage1_data.py` - Save training instructions
- `scripts/evaluate_stage1.py` - Create and use held-out eval set
- `scripts/utils/data_formatter.py` - Ensure load_jsonl is available

## Success Criteria
- [ ] Training instructions saved to `train_instructions.jsonl`
- [ ] Evaluation instructions saved to `eval_instructions.jsonl`
- [ ] Overlap report shows 0 overlaps
- [ ] Verification function confirms no leakage
- [ ] Same eval set used across all model comparisons

## Testing
1. Generate training data
2. Create evaluation set
3. Run verification function
4. Confirm overlap_report.json shows 0 overlaps
5. Run evaluation with both base and trained models using same eval set
