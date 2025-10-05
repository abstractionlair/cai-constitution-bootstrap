# Known Bugs and Fixes

**Last Updated**: 2025-10-04
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

## 🚨 CRITICAL: RunPod Xet/MooseFS Write Quota Issues

### The Issue
**Discovered**: 2025-10-05 (RunPod session)
**Status**: ✅ WORKAROUND AVAILABLE
**Symptom**: File writes to `/workspace` fail with "CAS service error" or quota exceeded
**Root Cause**: `/workspace` uses MooseFS with Xet CAS integration that has write quotas

### What Gets Blocked
- HuggingFace cache writes (model downloads, lock files)
- Git index writes (`git add`, `git commit`)
- Any file writes to `/workspace` paths
- Output artifact saves

### The Workaround
**Work from `/tmp` instead of `/workspace`**:

```bash
# Clone to /tmp (uses local overlay filesystem, 30GB free)
cd /tmp
git clone https://github.com/abstractionlair/cai-constitution-bootstrap.git MaximalCAI_tmp
cd MaximalCAI_tmp

# Model cache at /workspace is READ-ONLY accessible (perfect!)
export MODEL_PATH=/workspace/huggingface_cache/hub/models--Qwen--Qwen2.5-32B/snapshots/<SHA>

# Run scripts - they write to /tmp, read model from /workspace
python3 scripts/generate_sample_data.py --count 100
```

### Why This Works
- `/tmp` uses local filesystem (no Xet quotas)
- Model cache at `/workspace/huggingface_cache/` is readable (no writes needed)
- Scripts use `MODEL_PATH` to load from `/workspace` (read-only)
- Output artifacts write to `/tmp` (no quotas)

### Code Support
- ✅ `CleanModelLoader` accepts local paths (commit a21ba73)
- ✅ Generation scripts check `MODEL_PATH` env var (commit a21ba73)
- ✅ No hardcoded paths - flexible via environment variable

### Status
- ✅ Workaround validated with 100-sample generation
- ✅ QC metrics passed (100% delimiter, 0% contamination)
- ✅ Ready for full-scale generation from `/tmp`

---

## 🚨 CRITICAL: RunPod Environment - Torch Import Hangs

### The Bug
**Discovered**: 2025-10-04 (RunPod H100 pod, first session)
**Status**: ⚠️ ENVIRONMENT ISSUE - was pod-specific, resolved by using new pod
**Symptom**: Scripts hung indefinitely when importing torch, SSH became unresponsive
**Root Cause**: That specific pod environment had broken/misconfigured torch installation that:
- Exhausted file descriptors ("Too many open files in system")
- Exhausted memory ("Cannot allocate memory")
- Hung indefinitely trying to initialize CUDA

### Where It Hit Us
1. **`scripts/setup_runpod_environment.sh` (lines 114-134)**:
   - Verification step imports torch to check versions
   - Hung during "Verifying installations..."

2. **`scripts/create_session_manifest.py` → `provenance_helper.py:251`**:
   - Session manifest script imports torch for GPU info
   - Hung on first execution by Pod Claude
   - User could not interrupt (Ctrl+C ineffective) or open new SSH session
   - Pod became completely unresponsive, had to be terminated

### This is NOT a Code Bug
This is a **pod environment problem**. Our scripts require torch to work - we can't work around a broken torch installation with try/except. We need torch to import successfully for ANY ML work.

### Diagnosis Steps for New Pod
Before running ANY of our scripts on a new pod:

```bash
# 1. Test basic torch import (should complete in <5 seconds)
timeout 10 python3 -c "import torch; print('Torch:', torch.__version__)"

# 2. Test CUDA availability
python3 -c "import torch; print('CUDA:', torch.cuda.is_available())"

# 3. Test GPU access
python3 -c "import torch; print('GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'No GPU')"
```

If ANY of these hang or fail:
- **Don't use this pod** - the environment is broken
- Try different RunPod template
- Or reinstall torch: `pip uninstall torch && pip install torch --index-url https://download.pytorch.org/whl/cu121`
- Check CUDA setup: `nvidia-smi` and `nvcc --version`
- Check system limits: `ulimit -a`

### Recovery Procedure
If pod hangs during torch import:
1. **Terminate pod from RunPod dashboard** (SSH is unresponsive)
2. **Start new pod**
3. **Test torch import FIRST** (before cloning repo or running scripts)
4. **Only proceed if torch works**

### Lessons Learned
- Pod being expensive ($2.69/hr) doesn't guarantee working environment
- Always smoke test torch before assuming environment is ready
- Setup script verification is important - don't skip it
- SSH lockout on hang is expensive - loses time and requires dashboard access

### Status
- ❌ First H100 pod (lost) had broken torch
- ⏳ Need new pod with verified working torch environment
- ⏳ Then can resume sample data generation workflow

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
