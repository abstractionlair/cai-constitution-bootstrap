# RunPod Session Plan - Stage 1 Complete Pipeline

**Created**: 2025-10-03
**Target**: Complete Stage 1 verification, data generation, and training

---

## Session Goals

1. **Verify base model behavior** (proves no contamination)
2. **Generate clean training data** (5-10k SFT, 10-30k preference pairs)
3. **Establish baseline** (eval base model performance)
4. **Train SFT model** (5-10k examples)
5. **Train DPO model** (10-30k pairs)
6. **Evaluate results** (compare base → SFT → DPO)

---

## Pre-Session Checklist

### Local Prep (DONE ✅)

- [x] P1: Data provenance investigation (existing data is incomplete/contaminated)
- [x] Write instruction-following eval script
- [x] Audit IMPLEMENTATION_REGISTRY
- [x] Deprecate contaminated scripts
- [x] Create this session plan

### Files to Transfer to RunPod

**Scripts**:
- `scripts/test_base_model_ultra_clean.py` - Verification
- `scripts/generate_stage1_sft_data.py` - Data generation
- `scripts/create_preference_pairs_improved.py` - Preference pairs
- `scripts/train_stage1_sft.py` - SFT training
- `scripts/train_stage1_dpo_improved.py` - DPO training
- `scripts/evaluate_instruction_following.py` - Evaluation
- `scripts/utils/` - Utility modules

**Documentation** (for reference):
- `docs/BASE_MODEL_TRUTH.md` - Chat template issue
- `docs/POST_TRAINING_APPROACHES.md` - Training guidance
- `ROADMAP.md` - Goals and milestones

**Configuration**:
- `constitution.yaml` - Constitutional principles (if needed)

---

## Session Workflow

### Phase 1: Verification (30-45 min, ~$1-1.50)

**Goal**: Prove base model has no chat template contamination

**Script**: `test_base_model_ultra_clean.py`

**Commands**:
```bash
# Run verification
python scripts/test_base_model_ultra_clean.py

# Expected output: Base model FAILS most instruction tests
# This proves no contamination
```

**Success Criteria**:
- Sentinel tests show base model behavior:
  - Does NOT produce clean translations
  - Does NOT produce numbered lists on command
  - Does NOT produce valid JSON on command
  - Does NOT give structured descriptions
  - CAN complete patterns (natural completion ability)

**Expected**: ~10-30% success rate on instruction-following

**Save**: Verification report to `artifacts/verification/`

---

### Phase 2: Baseline Evaluation (15-30 min, ~$0.50-1.00)

**Goal**: Establish baseline instruction-following performance

**Script**: `evaluate_instruction_following.py`

**Commands**:
```bash
# Evaluate base model
python scripts/evaluate_instruction_following.py \
    --model Qwen/Qwen2.5-32B \
    --output-dir artifacts/evaluations/base_model
```

**Success Criteria**:
- Evaluation completes successfully
- Success rate ~10-30% (matches verification)
- Results saved with timestamp

**Save**: Baseline evaluation to `artifacts/evaluations/base_model/`

---

### Phase 3: SFT Data Generation (2-4 hours, ~$3-7)

**Goal**: Generate 5-10k clean SFT training examples

**Script**: `generate_stage1_sft_data.py`

**Commands**:
```bash
# Generate SFT data
python scripts/generate_stage1_sft_data.py \
    --count 5000 \
    --output-dir artifacts/sft_data

# If successful, generate another batch to reach 10k
python scripts/generate_stage1_sft_data.py \
    --count 5000 \
    --output-dir artifacts/sft_data
```

**Success Criteria**:
- 5-10k examples generated
- Each has: instruction, response, formatted_text, completion
- chat_template=None verified in logs
- add_special_tokens=False verified
- Responses are appropriate for instructions

**Save**: SFT data to `artifacts/sft_data/sft_training_data_YYYYMMDD_HHMMSS.jsonl`

**Quality Check**:
```bash
# Sample a few examples
head -5 artifacts/sft_data/sft_training_data_*.jsonl | jq '.instruction, .response'

# Count examples
wc -l artifacts/sft_data/sft_training_data_*.jsonl
```

---

### Phase 4: SFT Training (2-4 hours, ~$3-7)

**Goal**: Train instruction-following with SFT

**Script**: `train_stage1_sft.py`

**Commands**:
```bash
# Train SFT model
python scripts/train_stage1_sft.py \
    --train-file artifacts/sft_data/sft_training_data_*.jsonl \
    --output-dir artifacts/models/sft_model \
    --epochs 3 \
    --batch-size 4 \
    --learning-rate 2e-4
```

**Hyperparameters** (adjust based on data size):
- Epochs: 3-5 (monitor for overfitting)
- Batch size: 4 (conservative for 32B model)
- Learning rate: 2e-4 (standard for QLoRA)
- LoRA r: 32-64
- LoRA alpha: 16-32

**Success Criteria**:
- Training loss decreases steadily
- No catastrophic overfitting
- LoRA adapters saved
- Training log saved

**Save**:
- LoRA adapters to `artifacts/models/sft_model/`
- Training log to `artifacts/logs/sft_training_*.log`

---

### Phase 5: SFT Evaluation (15-30 min, ~$0.50-1.00)

**Goal**: Measure SFT model instruction-following

**Script**: `evaluate_instruction_following.py`

**Commands**:
```bash
# Evaluate SFT model
python scripts/evaluate_instruction_following.py \
    --model artifacts/models/sft_model \
    --output-dir artifacts/evaluations/sft_model
```

**Expected**: ~70-80% success rate (base was ~10-30%)

**Success Criteria**:
- Clear improvement over baseline
- Most explicit instructions followed
- May still struggle with format constraints

**Save**: SFT evaluation to `artifacts/evaluations/sft_model/`

---

### Phase 6: Preference Pair Generation (1-2 hours, ~$2-3.50)

**Goal**: Generate 10-30k preference pairs using SFT model

**Script**: `create_preference_pairs_improved.py`

**Commands**:
```bash
# Generate preference pairs with BoN sampling
python scripts/create_preference_pairs_improved.py \
    --model artifacts/models/sft_model \
    --count 10000 \
    --candidates-per-prompt 4 \
    --output-dir artifacts/preference_pairs

# If working well, generate more to reach 20-30k
python scripts/create_preference_pairs_improved.py \
    --model artifacts/models/sft_model \
    --count 10000 \
    --candidates-per-prompt 4 \
    --output-dir artifacts/preference_pairs
```

**Best-of-N (BoN) Sampling**:
- Generate k=2-4 candidates per prompt
- Judge picks best → (chosen, rejected) pairs
- Target: 10k minimum, 30k ideal

**Success Criteria**:
- 10-30k pairs generated
- Each has: prompt, chosen, rejected
- Clear quality difference between chosen/rejected
- Diversity in rejection types (refusals, hallucinations, format violations)

**Save**: Preference pairs to `artifacts/preference_pairs/preference_pairs_*.jsonl`

---

### Phase 7: DPO Training (2-4 hours, ~$3-7)

**Goal**: Train with preferences for better instruction-following

**Script**: `train_stage1_dpo_improved.py`

**Commands**:
```bash
# Train DPO model from SFT checkpoint
python scripts/train_stage1_dpo_improved.py \
    --sft-model artifacts/models/sft_model \
    --preference-file artifacts/preference_pairs/preference_pairs_*.jsonl \
    --output-dir artifacts/models/dpo_model \
    --beta 0.1 \
    --epochs 3 \
    --batch-size 2
```

**Hyperparameters** (from POST_TRAINING_APPROACHES.md):
- β (beta): 0.1-0.3 (lower = stay closer to reference)
- Epochs: 1-3 (DPO needs less than SFT)
- Batch size: 2-4 (smaller for DPO due to memory)
- Learning rate: 5e-5 - 1e-4 (slightly lower than SFT)

**Success Criteria**:
- DPO loss decreases
- Win rate improves
- LoRA adapters saved

**Save**:
- LoRA adapters to `artifacts/models/dpo_model/`
- Training log to `artifacts/logs/dpo_training_*.log`

---

### Phase 8: Final Evaluation (15-30 min, ~$0.50-1.00)

**Goal**: Measure DPO model performance

**Script**: `evaluate_instruction_following.py`

**Commands**:
```bash
# Evaluate DPO model
python scripts/evaluate_instruction_following.py \
    --model artifacts/models/dpo_model \
    --output-dir artifacts/evaluations/dpo_model
```

**Expected**: ~90-95% success rate (SFT was ~70-80%)

**Success Criteria**:
- Further improvement over SFT
- Better format constraint following
- Better refusal behavior
- More consistent instruction-following

**Save**: DPO evaluation to `artifacts/evaluations/dpo_model/`

---

### Phase 9: Comparison & Analysis (15 min, local or GPU)

**Goal**: Compare all three models

**Commands**:
```bash
# Print comparison summary
python scripts/compare_evaluations.py \
    --base artifacts/evaluations/base_model/eval_*.json \
    --sft artifacts/evaluations/sft_model/eval_*.json \
    --dpo artifacts/evaluations/dpo_model/eval_*.json \
    --output artifacts/final_comparison.txt
```

**(If compare script doesn't exist, do manually)**:
```bash
# Extract success rates
jq '.success_rate' artifacts/evaluations/*/eval_*.json
```

**Expected**:
- Base: ~10-30%
- SFT: ~70-80%
- DPO: ~90-95%

**Save**: Comparison to `artifacts/final_comparison.txt`

---

## Time & Cost Estimates

| Phase | Time | Cost | Critical? |
|-------|------|------|-----------|
| 1. Verification | 30-45 min | $1-1.50 | ✅ Yes |
| 2. Baseline Eval | 15-30 min | $0.50-1.00 | ✅ Yes |
| 3. SFT Data Gen | 2-4 hours | $3-7 | ✅ Yes |
| 4. SFT Training | 2-4 hours | $3-7 | ✅ Yes |
| 5. SFT Eval | 15-30 min | $0.50-1.00 | ✅ Yes |
| 6. Preference Pairs | 1-2 hours | $2-3.50 | ✅ Yes |
| 7. DPO Training | 2-4 hours | $3-7 | ✅ Yes |
| 8. DPO Eval | 15-30 min | $0.50-1.00 | ✅ Yes |
| 9. Comparison | 15 min | $0.50 | ⚠️ Optional |
| **Total** | **9-16 hours** | **$15-29** | - |

**Budget**: Stage 1 allocated ~$25, estimated actual ~$15-29

**RunPod rate**: $1.74/hour for A100 SXM 80GB

**Recommendations**:
- Start early in day (this is a long session)
- Monitor progress; can pause between phases if needed
- Priority: Phases 1-5 (verification → baseline → SFT)
- If budget tight: Skip full 30k pairs, use 10k minimum

---

## Decision Points

### After Verification (Phase 1)

**If verification FAILS** (base model shows high instruction-following):
- ❌ STOP immediately
- Something is wrong (contamination detected)
- Debug before proceeding
- Don't waste GPU on training

**If verification PASSES** (base model shows ~10-30%):
- ✅ Continue to data generation
- Baseline confirmed

### After SFT Evaluation (Phase 5)

**If SFT shows NO improvement** (<40% success):
- ⚠️ Investigate data quality
- Check training logs
- May need to regenerate data or adjust training
- Can still try DPO, but results questionable

**If SFT shows GOOD improvement** (>60% success):
- ✅ Continue to DPO
- On track for good results

### After DPO Evaluation (Phase 8)

**If DPO shows NO improvement over SFT**:
- ⚠️ Check preference pair quality
- May indicate pairs weren't diverse/hard enough
- Still publishable (SFT alone is useful)

**If DPO shows GOOD improvement** (>85% success):
- ✅ Stage 1 complete!
- Proceed to result analysis and documentation

---

## Post-Session Tasks (Local)

After RunPod session, back on local machine:

1. **Transfer artifacts**:
   ```bash
   # From RunPod to local (use SSH pipes per RUNPOD_STATUS.md)
   scp -P $RUNPOD_PORT root@195.26.233.96:/workspace/artifacts/* artifacts/
   ```

2. **Update ROADMAP.md**:
   - Mark completed phases
   - Update success criteria with actual results

3. **Update VERIFICATION_STATUS.md**:
   - Document verification results
   - Confirm base model is clean
   - Record actual performance numbers

4. **Create results summary**:
   - Document in `status/PROJECT_STATUS.md`
   - Create decision doc in `archive/decisions/`

5. **Update IMPLEMENTATION_REGISTRY.md**:
   - Add any new scripts created
   - Update status of used scripts

6. **Archive old data**:
   - Move Sep 10-11 data to `archive/data/`
   - Document as superseded

---

## Troubleshooting

### OOM Errors

**Symptoms**: CUDA out of memory during training

**Solutions**:
1. Reduce batch size (try 2 or 1)
2. Reduce LoRA rank (try r=16)
3. Use gradient checkpointing
4. Reduce sequence length

### Slow Generation

**Symptoms**: Data generation taking >6 hours

**Solutions**:
1. Check if using flash attention
2. Reduce max_new_tokens
3. Use temperature=0 for faster (deterministic) generation
4. Consider generating in smaller batches

### Poor SFT Results

**Symptoms**: SFT model not improving over base

**Possible causes**:
1. Data quality issues
2. Learning rate too high/low
3. Not enough epochs
4. Formatting issues in training data

**Debug**:
1. Sample generated responses manually
2. Check training loss curve
3. Verify data format matches training script expectations

---

## Success Criteria Summary

**Minimum Success** (publishable):
- ✅ Verification passes (base model ~10-30%)
- ✅ Clean data generated (5k+ SFT examples)
- ✅ SFT training completes
- ✅ SFT model shows improvement (>60%)

**Full Success** (ideal):
- ✅ All minimum criteria
- ✅ Preference pairs generated (10k+)
- ✅ DPO training completes
- ✅ DPO model shows improvement (>85%)
- ✅ Clear progression: base → SFT → DPO

**Publication Ready**:
- ✅ All full success criteria
- ✅ Statistical significance demonstrated
- ✅ Error analysis completed
- ✅ Reproducibility documented

---

## Related Documents

- `/status/RUNPOD_STATUS.md` - Infrastructure details, SSH access
- `/docs/POST_TRAINING_APPROACHES.md` - DPO guidance, hyperparameters
- `/docs/BASE_MODEL_TRUTH.md` - Chat template contamination issue
- `/docs/TECHNICAL_SETUP.md` - Model and training setup
- `ROADMAP.md` - Project milestones and goals
- `/tasks/claude_code/completed/P1_determine_existing_data_provenance.md` - Why we're regenerating data

---

**Ready to deploy!** All prep work complete, scripts ready, plan documented.
