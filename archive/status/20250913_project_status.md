# Stage 1 Project Status & Execution Plan

## Current Status (2025-09-13)

### What We've Actually Run

#### ✅ Completed Work
1. **Initial Instructions Generated**: 
   - 40 train instructions in `data/stage1/train_instructions.jsonl`
   - 10 test instructions in `artifacts/held_out_test_instructions_20250911_162708.jsonl`
   - Mixed types: completion, QA, generation, response

2. **Preference Pairs Created**: 
   - 112 pairs in `artifacts/preference_pairs.jsonl`
   - Used for potential DPO training

3. **Architecture Implementation**:
   - **CompletionStylePrompts class** (`scripts/utils/data_formatter.py`): Sophisticated few-shot prompting system
   - **Chat template contamination fix**: `tokenizer.chat_template = None` and `add_special_tokens=False`
   - **Dataset prompt format bug fix**: Line 402 in `generate_stage1_sft_data.py`

4. **Documentation Created**:
   - `DATA_GENERATION_ARCHITECTURE.md` - Explains our two-pronged approach
   - `FEW_SHOT_PROMPTING.md` - Details our few-shot architecture
   - `CRITICAL_FIXES.md` - Documents fixes and remaining issues
   - `CLAUDE.md` - Updated with critical implementation details

#### ⚠️ Partially Complete
- Multiple background jobs running on RunPod (status unknown - pod stopped)
- No trained models/checkpoints saved locally yet
- 200 SFT examples may have been generated (needs verification)

### What Still Needs to Be Run

1. **Baseline Assessment** - Never completed
2. **Full SFT Data Generation** - Need 1000+ examples
3. **SFT Training** - No confirmed training completed
4. **DPO Training** - Not started
5. **Comprehensive Evaluation** - Not started

## Staged Execution Plan

### Stage 1A: Baseline Assessment (2 hours)
**Goal**: Establish what Qwen-2.5-32B base can already do

**Tasks**:
1. Run `test_base_model_definitive.py` on 100 explicit instructions
2. Document baseline success rate (expect ~10-30%)
3. Save results to `artifacts/baseline_assessment.json`

**Verification Criteria**:
- [ ] Baseline metrics JSON file exists
- [ ] Success rate documented for each instruction type
- [ ] Clear understanding of model's starting capabilities

**Lockdown**: Once complete, never re-run baseline (it's our control)

---

### Stage 1B: Data Generation (3 hours)
**Goal**: Generate high-quality SFT training data

**Tasks**:
1. Generate 1000 instructions using `generate_stage1_sft_data.py`
2. Use base model to generate responses with CompletionStylePrompts
3. Filter for quality:
   - Response length > 50 characters
   - No refusals or "I cannot" responses
   - Properly formatted

**Verification Criteria**:
- [ ] 800+ quality instruction/response pairs generated
- [ ] Data saved to `data/stage1/sft_training_data.jsonl`
- [ ] Quality metrics logged (success rate, avg length)

**Lockdown**: Once verified, backup data and mark as immutable

---

### Stage 1C: SFT Training (4 hours)
**Goal**: Train model to follow explicit instructions

**Tasks**:
1. Train with `train_stage1_sft.py` on filtered data
2. Configuration:
   - QLoRA 4-bit quantization
   - Learning rate: 2e-4
   - Epochs: 3
   - Batch size: 4 (gradient accumulation as needed)
3. Save checkpoint every 100 steps

**Verification Criteria**:
- [ ] Training loss decreases consistently
- [ ] 95%+ success on explicit instructions
- [ ] Checkpoint saved to `checkpoints/stage1_sft/`

**Lockdown**: Save best checkpoint, document hyperparameters

---

### Stage 1D: DPO Refinement (3 hours)
**Goal**: Improve response quality with preference learning

**Tasks**:
1. Generate negative examples using SFT model
2. Create preference pairs (positive from data, negative from failures)
3. Train DPO with `train_stage1_dpo_improved.py`

**Verification Criteria**:
- [ ] 500+ preference pairs created
- [ ] DPO loss converges
- [ ] Response quality improves on test set

**Lockdown**: Save DPO checkpoint separately

---

### Stage 1E: Final Evaluation (1 hour)
**Goal**: Comprehensive evaluation and lockdown

**Tasks**:
1. Run `evaluate_stage1_comprehensive.py` on held-out test set
2. Compare to baseline metrics
3. Generate performance report

**Verification Criteria**:
- [ ] All test instructions evaluated
- [ ] Improvement over baseline documented
- [ ] Final report generated

**Lockdown**: Archive all artifacts, create Stage 1 completion certificate

---

## Next Immediate Actions

1. **Start RunPod** and verify connection
2. **Check what's actually on RunPod** from previous runs
3. **Begin Stage 1A** - Baseline Assessment
4. **Update this document** after each stage completion

## Important Notes

- Each stage must be **completed and verified** before moving to next
- All outputs must be **saved locally** before stopping RunPod
- Use this document as the **single source of truth**
- Mark stages as locked once verified to prevent re-running

## Cost Tracking
- Estimated total: 13 hours @ $1.74/hr = ~$23
- Actual used: [TO BE UPDATED]

## SSH Connection Info
```bash
# Pod is currently STOPPED
# When restarted, get new port from RunPod dashboard
export RUNPOD_PORT=[CHECK_DASHBOARD]
ssh -p $RUNPOD_PORT -i ~/.ssh/id_ed25519 root@195.26.233.96
```