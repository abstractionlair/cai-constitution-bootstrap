# Known Bugs and Fixes

**Last Updated**: 2025-10-03
**Purpose**: Document bugs discovered and their fixes to prevent regression

---

## 🚨 CRITICAL: Chat Template Contamination

### The Bug
**Discovered**: Multiple times, repeatedly forgotten
**Symptom**: Qwen/Qwen2.5-32B base model appears to follow instructions perfectly
**Root Cause**: Tokenizer automatically applies chat templates even for base model

### Why It Happens
```python
# This code looks innocent but applies chat templates:
tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-32B")
inputs = tokenizer("Describe the seasons", return_tensors="pt")

# Silently becomes:
# <|im_start|>system
# You are a helpful assistant<|im_end|>
# <|im_start|>user
# Describe the seasons<|im_end|>
# <|im_start|>assistant
```

### Detection Signs
- Base model produces clean, assistant-style answers
- Base model follows instructions on first try
- High instruction-following accuracy (>70%) without training
- Numbered lists, structured responses, proper stopping

### Sentinel Tests (Base Model Should Fail These)
1. "Translate to Pig Latin: hello world" - Should NOT translate cleanly
2. "List three prime numbers" - Should NOT produce numbered list
3. "Write a JSON with keys a,b and integers" - Should NOT produce valid JSON
4. "Describe the seasons" - Should ramble/continue, not give structured answer

### The Fix
```python
tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-32B")
tokenizer.chat_template = None  # CRITICAL: Disable chat template
inputs = tokenizer(
    prompt,
    add_special_tokens=False,  # Prevent template injection
    return_tensors="pt"
)
```

### Applied In
- ✅ `generate_stage1_sft_data.py:130` - `tokenizer.chat_template = None`
- ✅ `generate_stage1_sft_data.py:273` - `add_special_tokens=False`
- ✅ `test_base_model_ultra_clean.py` - Definitive clean test

### Reference
- **Full details**: `BASE_MODEL_TRUTH.md`
- **Architecture notes**: `DATA_GENERATION_ARCHITECTURE.md`

### Prevention Checklist
Before ANY base model evaluation:
- [ ] Confirm model is `Qwen/Qwen2.5-32B` (NOT "Instruct")
- [ ] Set `tokenizer.chat_template = None`
- [ ] Use `add_special_tokens=False`
- [ ] Check first 100 chars of encoded input for `<|im_start|>`
- [ ] Test sentinel instructions
- [ ] Log exact tokenization path

---

## 🐛 CRITICAL: Evaluation Memory Management

### The Bug
**Status**: 🚨 NOT YET FIXED (P0)
**File**: `evaluate_capability_differentiation.py`
**Symptom**: OOM errors or incorrect results due to concurrent model loading

### Root Cause
Script loads multiple models simultaneously:
- Base model
- SFT model
- DPO model
All loaded into GPU memory at once

### Impact
- Out of memory crashes on smaller GPUs
- Incorrect evaluation results (models interfering)
- Inefficient GPU utilization

### The Fix (Pending)
Load models sequentially, unload between evaluations:
```python
# Load base model
results_base = evaluate(base_model)
del base_model
torch.cuda.empty_cache()

# Load SFT model
results_sft = evaluate(sft_model)
del sft_model
torch.cuda.empty_cache()

# Load DPO model
results_dpo = evaluate(dpo_model)
```

### Status
- ❌ Bug exists in `evaluate_capability_differentiation.py`
- ⏳ Fix pending (see `tasks/claude_code/pending/20250912_170000_P0_fix_evaluation_memory_management.md`)
- ✅ May already exist in `evaluate_capability_differentiation_sequential.py` (needs verification)

---

## 🐛 Prompt Format Inconsistency (Line 402 Bug)

### The Bug
**Status**: Known, cosmetic, not critical
**File**: `generate_stage1_sft_data.py:402`
**Symptom**: Dataset stores different prompt format than what was used for generation

### Root Cause
```python
# Line 268: Generation uses completion-style prompts
completion_prompt = self.create_completion_prompt(instruction, inst_type)

# Line 402: Dataset stores instruction-style prompts
'prompt': f"Instruction: {inst_data['instruction']}\nResponse:",  # WRONG FORMAT
```

### Impact
- Generated data is still high quality
- But stored prompt format doesn't match generation format
- Cosmetic inconsistency, doesn't affect training

### The Fix
```python
# Change line 402 from:
'prompt': f"Instruction: {inst_data['instruction']}\nResponse:",

# To:
'prompt': self.create_completion_prompt(instruction, inst_type),
```

### Why It Hasn't Broken Things
Chat template is properly disabled, so even with instruction-style prompts, the data is clean.

### Status
- 🐛 Known bug
- ⚠️ Low priority (P2-P3)
- 📝 Documented in `DATA_GENERATION_ARCHITECTURE.md`

---

## 🐛 Data Leakage Risks

### The Bug Pattern
**Status**: Addressed through task tracking
**Risk**: Test instructions appearing in training data

### Prevention Measures
- ✅ Separate test instruction generation (`generate_test_instructions.py`)
- ✅ Held-out test set (130 examples)
- ⏳ Need persistent evaluation set (see pending tasks)

### Detection
- Check for overlap between training JSONL and test JSONL
- Verify test set is never used for training data generation

### Status
- ✅ Architecture supports separation
- ⚠️ Need automated validation (see P0 tasks in pending)

---

## 🐛 Loss Masking Robustness

### The Issue
**Status**: Implemented, needs hardening
**Risk**: Loss masking might not work correctly with all formats

### Current Implementation
SFT trainer masks instruction tokens, trains only on response tokens.

Format: `Instruction: X\nResponse: Y\nEND`

Mask everything before `Response:`

### Potential Issues
- Edge cases with unusual instruction formats
- Tokenization boundary issues
- END token handling

### Hardening Needed (P2)
- Add validation that masking is applied correctly
- Test with edge cases
- Verify loss computation on masked regions

### Reference
- `train_stage1_sft.py` - Current implementation
- Pending task: `20250912_170300_P2_strengthen_loss_masking_robustness.md`

---

## 🐛 RunPod SSH Stable Proxy Failure

### The Bug
**Status**: Documented, workaround applied
**Symptom**: RunPod's documented stable proxy SSH doesn't work

### Root Cause
```bash
# Documentation says to use:
ssh tupdqnn4ka2obr-6441138e@ssh.runpod.io -i ~/.ssh/id_ed25519

# But this FAILS (connection timeout/refused)
```

### The Fix
Use direct SSH with dynamic port:
```bash
# Check RunPod dashboard for current port (changes on restart)
export RUNPOD_PORT=48550  # UPDATE THIS after pod restart!
ssh -p $RUNPOD_PORT -i ~/.ssh/id_ed25519 root@195.26.233.96
```

### File Transfer
Don't use `scp` (doesn't work with proxy). Use SSH pipes:
```bash
cat local_file | ssh -p $RUNPOD_PORT -i ~/.ssh/id_ed25519 root@195.26.233.96 'cat > /remote/path/file'
```

### Reference
- **Full details**: `RUNPOD_SSH_SOLUTION.md`
- **Helper script**: `scripts/copy_to_pod.sh`

---

## 🐛 Statistical Rigor Issues

### The Issue
**Status**: Identified in reviews, needs addressing
**Tasks**: See `tasks/claude_code/pending/20241228_130002_P0_statistical_rigor.md`

### Problems
- Evaluation may lack proper statistical testing
- Need paired t-tests or similar for model comparisons
- Sample sizes may be too small for significance

### The Fix (Pending)
- Implement paired statistical tests
- Increase evaluation sample sizes
- Add confidence intervals
- Document statistical methodology

### Status
- ⚠️ P0 priority from reviews
- 📝 Task created but not started

---

## Historical Bugs (Fixed, Watching for Regression)

### Template Placeholder Issues
**Fixed In**: Multiple scripts
**Was**: Using template placeholders incorrectly
**Now**: Proper template handling
**Watch For**: Placeholders appearing in generated text

### Evaluation Prompting Consistency
**Fixed In**: Evaluation scripts
**Was**: Different prompting styles for evaluation vs training
**Now**: Consistent prompting across pipeline
**Watch For**: Evaluation scripts using different format than training

### Few-Shot Diversity
**Addressed In**: `utils/data_formatter.CompletionStylePrompts`
**Was**: Same examples every time
**Now**: Random selection from pool of examples (3-4 per prompt)
**Watch For**: Loss of diversity in few-shot examples

---

## Regression Prevention Protocol

### When Modifying Code

1. **Check this document first** - Has this bug been fixed before?
2. **Check IMPLEMENTATION_REGISTRY.md** - Is there already a utility for this?
3. **Run relevant tests** - Don't break existing fixes
4. **Update documentation** - Add new bugs or fixes here

### When Adding Tests

1. **Add sentinel tests for critical bugs** (especially chat template contamination)
2. **Test edge cases** that caused previous bugs
3. **Verify fixes are still working** before marking tasks complete

### When Reviewing PRs / Changes

1. **Check for re-implementation** of existing fixes
2. **Verify critical patterns are followed** (chat template, few-shot, etc.)
3. **Ensure bug fixes are documented** in this file

---

## Quick Reference: "This looks wrong..."

**Base model following instructions too well**:
→ Chat template contamination - See top of this document

**OOM during evaluation**:
→ Memory management bug - Load models sequentially

**Dataset prompts don't match generation**:
→ Line 402 bug - Known, cosmetic, low priority

**Test data might be in training set**:
→ Data leakage - Verify separation, check pending tasks

**RunPod SSH not working**:
→ Stable proxy broken - Use direct SSH with port from dashboard

**Statistical significance unclear**:
→ Statistical rigor - See P0 task for improvements needed

---

**When you encounter a new bug**: Document it here immediately!
