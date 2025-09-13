# Comprehensive Fix Request for Stage 1 Pipeline

Based on independent reviews from Gemini and Codex, please fix all the following issues before deployment:

## 🔴 Critical Fixes (Deployment Blockers)

### 1. Enforce 95% Success Gate
**File**: `scripts/run_stage1_pipeline.py`
**Issue**: Pipeline doesn't check if model achieves 95% instruction following
**Fix**: 
- Read `results/stage1_evaluation_*.json` after evaluation
- Check if overall success rate >= 0.95
- Fail the pipeline if threshold not met
- Log clear message: "Stage 1 FAILED: Only achieved X% (need 95%)"

### 2. Fix RunPod Paths
**All files**
**Issue**: Code assumes local paths, but will run at `/workspace/cai-constitution-bootstrap/`
**Fix**:
```python
# Add to each script
import os
BASE_DIR = Path(os.getenv('CAI_BASE_DIR', '/workspace/cai-constitution-bootstrap'))
data_dir = BASE_DIR / "data" / "stage1"
```

### 3. Use Consistent Precision for Evaluation
**Files**: `scripts/baseline_assessment.py`, `scripts/evaluate_stage1.py`
**Issue**: Baseline uses 4-bit, trained uses higher precision (unfair comparison)
**Fix**: 
- Both should use same precision (recommend 8-bit for quality)
- Or at minimum, both should use 4-bit Unsloth loading

### 4. Increase Timeout
**File**: `scripts/run_stage1_pipeline.py`
**Issue**: 1-hour timeout too short for training
**Fix**:
```python
TIMEOUTS = {
    'baseline': 3600,    # 1 hour
    'generate': 7200,    # 2 hours  
    'train': 10800,      # 3 hours
    'evaluate': 3600     # 1 hour
}
```

### 5. Use Higher Precision for Data Generation
**File**: `scripts/generate_stage1_data.py`
**Issue**: Uses 4-bit for generation (spec says 8/16-bit for quality)
**Fix**:
```python
# For generation, use 8-bit
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name=self.model_name,
    max_seq_length=2048,
    dtype=None,
    load_in_8bit=True,  # Changed from load_in_4bit
)
```

## 🟡 Important Fixes (Quality Issues)

### 6. Actually Use Constitution
**File**: `scripts/generate_stage1_data.py`
**Issue**: Loads constitution.yaml but uses hardcoded principles
**Fix**:
```python
def _create_critique_prompt(self, instruction, response, principles=None):
    if principles is None:
        # Use constitution from YAML
        principles = [p['text'] for p in self.constitution.get('principles', [])]
        if not principles:  # Fallback
            principles = self.default_principles
```

### 7. Improve Instruction Diversity
**File**: `scripts/utils/data_formatter.py`
**Issue**: Limited diversity (small lists repeated)
**Fix**:
- Add more question templates (50+ instead of ~30)
- Add more topic variations
- Use random combinations of templates × topics × formats
- Consider using the model itself to generate diverse instructions

### 8. Make Checkpoint Selection Robust
**File**: `scripts/train_stage1_dpo.py`
**Issue**: Uses modification time (could pick incomplete checkpoints)
**Fix**:
```python
# Write success marker at end of training
success_marker = checkpoint_dir / "TRAINING_SUCCESS"
success_marker.write_text(json.dumps({
    'completed': datetime.now().isoformat(),
    'final_loss': final_loss,
    'epochs': epochs_completed
}))
```

### 9. Fix Instruction Count Bug
**File**: `scripts/generate_stage1_data.py`
**Issue**: Integer division drops remainder
**Fix**:
```python
# Ensure we get exactly the requested count
counts = [total_instructions // 4] * 4
counts[0] += total_instructions % 4  # Add remainder to first category
```

## 🟢 Nice-to-Have Fixes (Code Quality)

### 10. Add Path Arguments to Scripts
**All scripts**
**Issue**: Hardcoded paths make system brittle
**Fix**:
```python
parser.add_argument('--data-dir', default=BASE_DIR / 'data/stage1')
parser.add_argument('--checkpoint-dir', default=BASE_DIR / 'checkpoints/stage1')
parser.add_argument('--results-dir', default=BASE_DIR / 'results')
```

### 11. Fix Unused model_loader Function
**File**: `scripts/utils/model_loader.py`
**Issue**: `load_trained_model()` incorrectly loads LoRA
**Fix**: Either fix it or remove it to avoid confusion

### 12. Add Data Staleness Check
**File**: `scripts/run_stage1_pipeline.py`
**Issue**: Could silently train on wrong data
**Fix**:
```python
if existing_data and args.instructions != existing_summary['total_instructions']:
    logger.warning(f"⚠️ Existing data has {existing_summary['total_instructions']} instructions, but you requested {args.instructions}")
    if not args.force_data:
        raise ValueError("Data mismatch - use --force-data to regenerate")
```

### 13. Filter Low-Signal Preference Pairs
**File**: `scripts/generate_stage1_data.py`
**Issue**: Some pairs have minimal difference
**Fix**:
```python
# Skip pairs with very similar responses
similarity = len(set(original.split()) & set(improved.split())) / max(len(original.split()), len(improved.split()))
if similarity > 0.95:  # Too similar
    continue
```

### 14. Consistent Model Loading
**All scripts**
**Issue**: Some use transformers, some use Unsloth
**Fix**: Standardize on Unsloth for consistency (or document why different)

## Implementation Order

1. **First**: Fix paths (everything breaks without this on RunPod)
2. **Second**: Fix precision consistency and timeout
3. **Third**: Fix 95% gate enforcement
4. **Fourth**: Fix constitution usage and diversity
5. **Last**: Code quality improvements

## Testing After Fixes

```bash
# Test locally with tiny dataset
python scripts/run_stage1_pipeline.py --quick-test

# Verify paths work
CAI_BASE_DIR=/tmp/test python scripts/baseline_assessment.py

# Check evaluation gate
# Manually edit evaluation results to be <95% and verify pipeline fails
```

## Summary

Most of these are simple fixes:
- Path fixes: Add BASE_DIR variable (~10 lines total)
- Precision: Change one parameter in 3 places
- Timeout: Change one dict
- Constitution: Use the loaded YAML (~5 lines)
- 95% gate: Read JSON and check threshold (~10 lines)

Total time to fix all issues: ~1-2 hours
Impact: Transforms brittle prototype into robust system

The independent review model worked well - Gemini caught infrastructure issues while Codex caught methodology issues. Both caught the critical evaluation problem.
