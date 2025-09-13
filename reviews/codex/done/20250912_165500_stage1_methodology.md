# Review Request: Stage 1 Constitutional AI Methodology
Date: 2025-09-12 16:55
Requester: Claude Code  
Priority: High

## Approach Overview
Two-stage Constitutional AI training methodology for Stage 1 instruction following:

**Stage 1A (SFT)**: Train base model with supervised fine-tuning using consistent `Instruction:/Response:/END` format and proper loss masking (response tokens only)

**Stage 1B (DPO)**: Train SFT model using Direct Preference Optimization with diverse negative examples (5 types: unwarranted refusal, format violation, incorrect factual, off-topic, verbose/vague)

This methodology aims to establish basic instruction-following behavior before preference training, addressing the limitation that DPO cannot do token-level loss masking like SFT.

## Scientific/Methodological Questions
1. **Two-Stage Necessity**: Is SFT→DPO superior to direct DPO from base model for instruction following? Are we introducing unnecessary complexity?

2. **Loss Masking Impact**: How significant is token-level loss masking in SFT vs DPO's sequence-level preference optimization? Could we achieve similar results with better DPO prompting?

3. **Negative Example Validity**: Are our 5 categories of negatives (30% refusal, 25% format, 20% incorrect, 15% off-topic, 10% verbose) based on principled analysis or intuition? Should distribution be empirically determined?

4. **Evaluation Metrics**: Do our 9 evaluation criteria adequately capture instruction-following improvement? Are criteria weights appropriate?

5. **Sample Size Adequacy**: Is 200 SFT examples + 500 preference pairs sufficient for meaningful learning in 32B model? Statistical power analysis?

## Data Pipeline
```
Base Model Completions (200) 
    ↓ 
SFT Training Data (Instruction/Response/END format)
    ↓
SFT Model Training (loss masked to response tokens)
    ↓  
SFT Model Responses (generally good quality)
    ↓
Generate 5 Types of Negatives (diverse failure modes)
    ↓
Preference Pairs (chosen=SFT response, rejected=negative)
    ↓
DPO Training (from SFT checkpoint)
    ↓
Final Model Evaluation (vs base, SFT, held-out test set)
```

## Evaluation Metrics
**Format Compliance (3 criteria)**:
- `ends_with_end`: Response terminates properly 
- `proper_structure`: No format artifacts
- `no_rambling`: Appropriate length

**Instruction Following (3 criteria)**:
- `addresses_instruction`: Actually answers the request
- `appropriate_length`: Matches implicit length requirements  
- `no_unwarranted_refusal`: No inappropriate refusals

**Content Quality (3 criteria)**:
- `factually_correct`: Accurate information
- `coherent`: Well-formed responses
- `on_topic`: Stays focused on instruction

**Comparative Analysis**:
- Base vs SFT improvement 
- SFT vs DPO improvement
- Statistical significance testing

## Assumptions
1. **Base Model Behavior**: Qwen-2.5-32B exhibits continuation behavior rather than instruction following without training
2. **Format Importance**: Consistent format across training/inference is critical for learning
3. **Negative Diversity**: Multiple failure modes teach more robust preferences than single failure type
4. **Sequential Training**: SFT then DPO is superior to joint training or DPO-only approaches
5. **Evaluation Validity**: Human-designed criteria correlate with actual instruction-following quality
6. **Data Leakage Prevention**: Held-out test set properly measures generalization

## Alternative Approaches Considered
1. **Direct DPO**: Skip SFT, train DPO directly from base model (previous approach - lacked loss masking)
2. **Joint SFT+DPO**: Single-stage training with both supervised and preference objectives
3. **RLHF**: Use PPO instead of DPO (more complex, requires reward model)  
4. **Constitutional AI Critique**: Include critique generation step (adds complexity)
5. **Multiple Training Epochs**: Train for multiple epochs instead of single epoch (risk of overfitting)

## Methodological Concerns
1. **Selection Bias**: Are we cherry-picking examples that favor our approach?
2. **Evaluation Bias**: Are our criteria designed to make our method look better?
3. **Confounding Variables**: Could improvements come from better data rather than methodology?
4. **Hyperparameter Sensitivity**: How sensitive are results to LR, β, batch size choices?
5. **Reproducibility**: Are results reproducible across seeds, hardware, model versions?

## Statistical Rigor Questions  
1. **Sample Size**: Power analysis for detecting meaningful differences between models?
2. **Multiple Comparisons**: Need correction for testing 9 criteria across 3 models?
3. **Effect Size**: What constitutes practically significant improvement (not just statistical)?
4. **Confidence Intervals**: How confident are we in reported improvements?
5. **Baseline Establishment**: Is base model performance properly characterized?

## Checklist for Reviewer
Please validate:
- [x] Statistical rigor
- [x] Experimental design  
- [x] Data contamination prevention
- [x] Evaluation validity
- [x] Reproducibility
- [x] Scientific claims

## Research Context
This is part of a larger Constitutional AI bootstrapping experiment where Stage 1 (instruction following) enables subsequent stages (harmlessness, helpfulness, etc.). The methodology must be:

1. **Scalable**: Work for later stages with more complex objectives
2. **Automated**: Minimal human intervention required
3. **Interpretable**: Clear why improvements occur
4. **Robust**: Work across different base models and domains

## Key Validation Needs
1. **Methodology Soundness**: Is the SFT→DPO approach theoretically justified?
2. **Experimental Design**: Does evaluation properly test our hypotheses?
3. **Bias Identification**: What biases might affect results interpretation?
4. **Alternative Explanations**: What else could explain observed improvements?
5. **Generalization**: Will this approach work for other instruction-following tasks?