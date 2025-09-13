# P1: Add DPO-Only Baseline for Methodology Validation
Source: Codex Review 20250912_165500
Priority: HIGH (P1)
Estimated Time: 60 minutes

## Issue Description
The methodology review identified that we need to validate the SFT→DPO approach against a DPO-only baseline to demonstrate that the two-stage approach is actually superior to direct DPO from the base model.

## Location
New file needed: `scripts/train_stage1_dpo_only.py`
Comparison needed in: `scripts/evaluate_stage1_comprehensive.py`

## Suggested Implementation
Create a DPO-only training script that:
1. Starts from base model (not SFT model)
2. Uses the same preference pairs as the SFT→DPO approach
3. Provides fair comparison for methodology validation

## Implementation Plan
```python
# New script: scripts/train_stage1_dpo_only.py
def run_dpo_only_training():
    """Run DPO directly from base model for comparison"""
    
    # Load base model (not SFT checkpoint)
    model, tokenizer = setup_base_model_for_dpo()
    
    # Use same preference pairs as SFT→DPO approach
    pairs = load_preference_pairs_improved()
    
    # Train DPO directly on base model
    trainer = DPOTrainer(
        model=model,
        # Same hyperparameters as SFT→DPO for fair comparison
        args=dpo_args
    )
    
    # Save as separate checkpoint
    trainer.save_model("stage1_dpo_only")
```

Also update evaluation script to include DPO-only model in comparisons.

## Experimental Design
This enables crucial comparisons:
- **Base vs SFT**: Shows format learning benefit
- **Base vs DPO-only**: Shows preference learning from base
- **Base vs SFT→DPO**: Shows combined approach
- **SFT vs SFT→DPO**: Shows DPO benefit on SFT foundation
- **DPO-only vs SFT→DPO**: Shows whether SFT foundation helps DPO

## Success Criteria
- [ ] DPO-only training script created
- [ ] Same hyperparameters and data as SFT→DPO for fair comparison
- [ ] Evaluation script includes DPO-only model
- [ ] Clear comparison metrics showing relative benefits
- [ ] Methodology validation through ablation study

## Impact
**HIGH** - Required for scientific validity of the two-stage approach. Without this baseline, we can't claim SFT→DPO is superior to simpler alternatives.