# P0: Fix Critical Memory Management in Evaluation Script
Source: Gemini Review 20250912_165500
Priority: CRITICAL (P0)
**Assigned To**: claude_code
Estimated Time: 30 minutes

## Issue Description
The evaluation script `scripts/evaluate_stage1_comprehensive.py` loads all models (base, SFT, DPO) concurrently in `self.models` dictionary. This causes:
1. **Incorrect behavior** - LoRA adapters loaded onto same base model instance
2. **High OOM risk** - Multiple 32B models on 80GB GPU
3. **Memory leaks** - No proper cleanup between evaluations

## Location
File: `scripts/evaluate_stage1_comprehensive.py`
Methods: `load_base_model()`, `load_sft_model()`, `load_dpo_model()`, `evaluate_all_models()`

## Suggested Fix
Refactor to sequential model loading pattern:
```python
def evaluate_all_models(self, limit: int = None):
    # Evaluate each model sequentially, not concurrently
    for model_name in ['base', 'sft', 'dpo']:
        # Load single model
        self.load_model(model_name)
        
        # Run all evaluations for this model
        model_evaluations = self.evaluate_single_model(model_name, test_instructions)
        
        # Store results
        results['model_results'][model_name] = model_evaluations
        
        # Cleanup before next model
        self.cleanup_current_model()
        torch.cuda.empty_cache()
```

## Success Criteria
- [ ] Models loaded/evaluated/cleaned up sequentially
- [ ] No concurrent model storage in memory
- [ ] Explicit GPU cache clearing between models
- [ ] Each model gets fresh base model instance (no adapter conflicts)

## Impact
**CRITICAL** - Current implementation will fail on RunPod with OOM or produce incorrect results due to adapter conflicts.