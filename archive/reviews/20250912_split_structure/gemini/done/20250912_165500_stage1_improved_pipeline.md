# Review Request: Stage 1 Improved SFT→DPO Pipeline
Date: 2025-09-12 16:55
Requester: Claude Code
Priority: High

## Component Overview
Completely redesigned Stage 1 Constitutional AI training pipeline implementing SFT→DPO methodology with proper loss masking, diverse negative examples, and comprehensive evaluation. This replaces the previous simple DPO approach with a more principled two-stage training process.

## Files to Review
- `scripts/generate_stage1_sft_data.py` - SFT data generation with consistent format
- `scripts/train_stage1_sft.py` - SFT training with proper loss masking
- `scripts/generate_diverse_negatives.py` - Creates 5 types of negative examples
- `scripts/create_preference_pairs_improved.py` - Combines SFT responses with diverse negatives
- `scripts/train_stage1_dpo_improved.py` - DPO training from SFT checkpoint
- `scripts/evaluate_stage1_comprehensive.py` - Multi-model evaluation framework

## Specific Questions
1. **Loss Masking Implementation**: Is the custom `SFTDataCollator` correctly masking instruction tokens (-100) while training on response tokens? Are there edge cases in tokenization boundaries?

2. **Memory Management**: With 32B model + LoRA on 80GB GPU, are the sequential model loading/unloading patterns in evaluation safe? Any risk of OOM?

3. **LoRA Adapter Handling**: In DPO script, we merge SFT LoRA weights then add new LoRA for DPO. Is this the correct pattern, or should we keep SFT LoRA separate?

4. **Training Stability**: Are the hyperparameters (LR=5e-6, β=0.1) appropriate for 32B model? Is gradient accumulation configured correctly for effective batch size?

5. **Data Pipeline**: Any potential bugs in the instruction→response→negatives→pairs→training flow? Race conditions or data corruption risks?

## Context
This implementation incorporates insights from GPT-5 Pro feedback about:
- Need for SFT before DPO for proper loss masking
- Importance of consistent `Instruction:/Response:/END` format  
- Value of diverse negative examples vs just refusals
- Two-stage training methodology (SFT establishes format, DPO refines preferences)

Previous approach was DPO-only from base model, which lacked proper token-level loss masking and had noisy preference pairs with critique artifacts.

## Known Issues
1. **Model Loading**: Scripts assume specific checkpoint paths that may not exist
2. **Error Handling**: Limited graceful degradation if SFT model missing
3. **Resource Cleanup**: Some scripts may not fully clean GPU memory between steps
4. **Tokenizer Edge Cases**: Chat template disabling may not work consistently across contexts
5. **Evaluation Criteria**: Some subjective criteria (e.g., "factually_correct") use simple pattern matching

## Testing Status
- [ ] Unit tests written (none exist yet)
- [ ] Integration tests passed (manual testing only)
- [ ] Performance benchmarked (estimated times only)
- [x] Edge cases handled (basic error handling)

## Checklist for Reviewer
Please check for:
- [x] Code correctness
- [x] Performance issues
- [x] Security concerns
- [x] Best practices
- [x] Error handling
- [x] Documentation completeness

## Additional Technical Concerns
1. **Quantization Consistency**: BitsAndBytesConfig used consistently across all scripts?
2. **PEFT Integration**: Are LoRA configs and target modules appropriate for Qwen architecture?
3. **Stop Token Handling**: END token stopping implemented correctly in generation and training?
4. **Data Format Validation**: Any validation that training data follows expected format?
5. **Checkpoint Compatibility**: Will checkpoints be compatible across script versions?

## Critical Success Factors
This pipeline must:
1. Generate clean, consistent training data
2. Successfully train SFT model with proper loss masking
3. Create diverse, high-quality preference pairs
4. Train stable DPO model from SFT checkpoint
5. Provide meaningful evaluation metrics

The entire approach depends on the SFT→DPO methodology being correctly implemented with proper loss masking and format consistency.