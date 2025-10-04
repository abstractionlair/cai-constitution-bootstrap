# Revised Stage 1 Fix Priorities (Automation-Focused)
Date: 2024-12-28
Goal: Maximum automation for bootstrapping, CAI-inspired but not strict CAI

## Reframed Project Goal
We're testing **automated bootstrapping** with critique-and-revise mechanisms inspired by CAI, not implementing true Constitutional AI. The key metric is automation success, not constitutional adherence.

## Critical Issues (MUST FIX for valid experiment)

### 1. **Baseline/Evaluation Precision Mismatch** [FATAL]
**Problem**: Baseline uses float16, evaluation uses 8-bit - makes comparison invalid
**Fix**: Standardize ALL evaluations to 8-bit precision
**Impact**: Without this, we can't measure improvement

### 2. **Data Leakage Between Train/Eval** [FATAL]
**Problem**: Same content pools used for both training and evaluation
**Fix**: Enforce disjoint splits
**Impact**: Current results may show memorization, not learning

### 3. **Statistical Rigor** [HIGH]
**Problem**: No confidence intervals, stochastic evaluation
**Fix**: 
- Switch to deterministic evaluation
- Add confidence intervals
- Use proper statistical tests

## Lower Priority (given our actual goals)

### 4. ~~Constitutional Principle Tagging~~ [NOT REQUIRED]
Since we're not claiming true CAI, we don't need explicit principle tagging. The critique-and-revise mechanism is sufficient for our automation experiment.

### 5. **Constitution Usage** [MINOR]
Current implementation uses constitution.yaml but not optimally. For Stage 1 (instruction following), the hardcoded principles might actually be better. This is fine for our automation goals.

### 6. **Data Pool Size** [MEDIUM]
Should still expand pools for better quality, but this is about training quality, not the core automation claim.

## Minimum Viable Fix Set for Our Actual Goals

1. **Fix precision mismatch** (30 min) - Essential for valid comparison
2. **Create disjoint data splits** (1 hour) - Essential for generalization claims  
3. **Switch to deterministic evaluation** (15 min) - Essential for reproducibility
4. **Add basic statistical tests** (30 min) - Essential for credibility
5. **Expand data pools moderately** (1 hour) - Improves quality

Total: ~3.5 hours (vs 5 hours if we were doing true CAI)

## What We're Actually Testing

Our experiment tests whether we can:
1. **Automate** the entire training pipeline
2. **Bootstrap** from a base model to instruction-following
3. Use **self-critique and revision** (CAI-inspired) to create training data
4. Achieve **progressive improvement** through stages
5. Do this with **minimal human intervention**

We're NOT claiming:
- This is true Constitutional AI
- The constitution is meaningfully integrated
- Principles guide the learning

## Updated Narrative for Publication

"We present an automated bootstrapping approach inspired by Constitutional AI's critique-and-revise mechanism. While not implementing full CAI (our critiques don't explicitly reference constitutional principles), we demonstrate that automated self-improvement is achievable through staged training with self-generated preference pairs."

## Recommendation

Fix the FATAL issues that affect experimental validity:
1. Precision mismatch
2. Data leakage  
3. Statistical rigor

Don't worry about constitutional principle tagging - it's not core to our automation experiment.

## Cost Impact
- Reduced fixes: ~3.5 hours @ $1.74/hr = ~$6
- Re-run pipeline: ~6 hours @ $1.74/hr = ~$10
- Total: ~$16 (vs $19 if doing full CAI fixes)
