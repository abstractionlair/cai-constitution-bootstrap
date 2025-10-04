# Implementation Registry

**Last Updated**: 2025-10-03
**Purpose**: Track what's been implemented to prevent re-implementation

---

## Core Utilities (`scripts/utils/`)

### `data_formatter.py`
**Purpose**: Data formatting and prompt construction
**Key Components**:
- `CompletionStylePrompts` class - Few-shot completion prompting for base model
  - `create_response_generation_prompt()` - Creates 3-4 example few-shot prompts
  - Examples: math, completion, facts, creative, explanatory
  - **Critical**: Use this for all base model response generation
- `load_jsonl()` - Load JSONL files
- Format conversion utilities

**Status**: ✅ Complete and tested
**Lines of Interest**:
- Class definition: ~line 50-150
- Few-shot examples: Random selection from predefined pool

### `data_validation.py`
**Purpose**: Validate training data formats
**Key Functions**:
- `load_and_validate_sft_data()` - Validates SFT data structure
- Format checking for Instruction/Response/END pattern

**Status**: ✅ Complete
**Use When**: Loading any SFT training data

### `model_loader.py`
**Purpose**: Model loading with proper quantization
**Key Functions**:
- `load_base_model()` - Loads Qwen-2.5-32B with 4-bit quantization
- `clear_gpu_cache()` - GPU memory management
- `print_gpu_utilization()` - Monitoring utilities

**Status**: ✅ Complete
**Critical**: Always use this, don't reimplement model loading

### `metrics.py`
**Purpose**: Evaluation metrics
**Key Functions**:
- Task-specific accuracy calculations
- Statistical analysis utilities

**Status**: ✅ Complete

---

## Data Generation

### `generate_stage1_sft_data.py` ⭐ PRIMARY SFT DATA GENERATOR
**Purpose**: Generate clean SFT training data for Stage 1
**Lines**: ~700 lines
**Key Features**:
- ✅ Chat template properly disabled (line 130: `tokenizer.chat_template = None`)
- ✅ Special tokens prevented (line 273: `add_special_tokens=False`)
- ✅ Uses completion-style prompting for generation (line 268)
- ❌ BUG at line 402: Stores wrong prompt format in dataset (cosmetic issue)
- Instruction types: QA, completion, generation, creative, analytical
- Minimum response length: 50 tokens
- Output format: `Instruction: X\nResponse: Y\nEND`

**Status**: ✅ Functional with minor bug
**Generated**: 200 high-quality examples (artifacts/sft_training_data_20250913_005116.jsonl)
**Dependencies**: `utils/data_formatter.CompletionStylePrompts`

### `stage1_generate.py`
**Purpose**: Generate responses using base model
**Key Features**:
- ✅ CORRECTLY uses `CompletionStylePrompts.create_response_generation_prompt()` (line 196)
- Few-shot completion approach
- Clean base model handling

**Status**: ✅ Complete and correct
**Use As**: Reference implementation for completion-style prompting

### `generate_test_instructions.py`
**Purpose**: Generate held-out test instructions
**Output**: Test instructions for evaluation (not training data)

**Status**: ✅ Complete
**Generated**: 130 test examples

### `generate_diverse_negatives.py`
**Purpose**: Create diverse negative examples for preference pairs
**Methods**:
- Truncation
- Incorrect responses
- Off-topic responses

**Status**: ✅ Complete

### `generate_preference_pairs_logprob.py`
**Purpose**: Create preference pairs using A/B log-probability evaluation
**Output**: DPO training data with chosen/rejected pairs

**Status**: ✅ Complete
**Generated**: 188 preference pairs

---

## Training

### `train_stage1_sft.py` ⭐ PRIMARY SFT TRAINER
**Purpose**: Supervised fine-tuning with proper loss masking
**Key Features**:
- ✅ Loss masking on response tokens only (masks "Instruction:" portion)
- QLoRA (4-bit base + LoRA adapters)
- LoRA config: r=16, alpha=32, dropout=0.1
- Target modules: q_proj, k_proj, v_proj, o_proj, gate_proj, up_proj, down_proj
- Training: 1 epoch, batch size 1, gradient accumulation 4
- Output: LoRA adapters only (~500MB)

**Status**: ✅ Complete
**Dependencies**: `utils/data_validation.load_and_validate_sft_data()`
**Output Dir**: `checkpoints/stage1_sft/`

### `train_stage1_dpo.py` ⭐ PRIMARY DPO TRAINER
**Purpose**: Direct Preference Optimization training
**Key Features**:
- Uses Unsloth's FastLanguageModel
- LoRA adapters (r=16)
- DPO with preference pairs (chosen/rejected)
- Can load from SFT checkpoint or start from base

**Status**: ✅ Complete
**Dependencies**: `utils/model_loader`, `utils/data_formatter`
**Output Dir**: `checkpoints/stage1_dpo/`

### Other Training Scripts (Superseded or Experimental)
- `train_stage1_dpo_improved.py` - Improved DPO pipeline
- `train_stage1_dpo_only.py` - DPO without SFT first
- `train_dpo_stage1.py` - Earlier DPO version
- `train_dpo_simple.py` - Simple DPO test

**Status**: ⚠️ Multiple versions exist, primary scripts identified above

---

## Evaluation

### ⚠️ CRITICAL MEMORY ISSUE
**Problem**: `evaluate_capability_differentiation.py` loads all models concurrently → OOM
**Status**: 🚨 P0 bug, not fixed yet
**Fixed Version**: `evaluate_capability_differentiation_sequential.py` (if exists)

### Evaluation Scripts Inventory (40 total scripts, many experimental)

**Primary Evaluation Scripts**:
- `evaluate_stage1_comprehensive.py` - Full Stage 1 evaluation
- `evaluate_sft_model.py` - SFT model-specific eval
- `evaluate_final.py` - Final evaluation script

**Base Model Testing** (Chat Template Contamination Prevention):
- `test_base_model_ultra_clean.py` ⭐ - Definitive contamination-free test
- `test_base_model_definitive.py` - Earlier definitive test
- `test_clean_base_model.py` - Clean base model test
- `evaluate_stage1_corrected.py` - Fixed chat template contamination

**Experimental/Test Scripts**:
- `evaluate_stage1.py`, `evaluate_stage1_simple.py`, `evaluate_stage1_readiness.py`
- `test_ab_logprob_evaluation.py` - Log-prob A/B testing
- `test_binary_evaluation.py` - Binary evaluation approach
- `test_fixes.py` - General fix testing

**Status**: ⚠️ Too many evaluation scripts, needs consolidation

---

## Pipeline Orchestration

### `run_stage1_pipeline.py`
**Purpose**: End-to-end Stage 1 pipeline
**Steps**:
1. Generate SFT data
2. Train SFT model
3. Generate preference pairs
4. Train DPO model
5. Evaluate final model

**Status**: ✅ Complete
**Use When**: Running full Stage 1 training

---

## Infrastructure

### `baseline_assessment.py`
**Purpose**: Assess base model capabilities before training
**Critical**: Run this FIRST to establish baseline

**Status**: ✅ Complete
**Reference**: See `BASE_MODEL_TRUTH.md` for expected behavior

### `runpod_manager.py`
**Purpose**: Programmatic RunPod instance management
**Features**:
- Start/stop pods via API
- Cost tracking
- Status monitoring

**Status**: ✅ Complete

### Shell Scripts
- `copy_to_pod.sh` - File transfer helper (uses SSH pipes, not scp)
- `deploy_via_git.sh` - Git-based deployment
- `scripts/sync_claude.sh` - Sync script (purpose TBD)

**Status**: ✅ Complete

---

## Analysis & Debugging

### `analyze_sft_data.py`
**Purpose**: Analyze SFT training data quality
**Checks**: Format, length, diversity

**Status**: ✅ Complete

### `preview_responses.py`
**Purpose**: Preview model responses interactively

**Status**: ✅ Complete

### `show_prompts.py`, `show_raw_prompts.py`
**Purpose**: Inspect exact prompts sent to model (for debugging contamination)

**Status**: ✅ Complete

### Test Scripts (Various)
- `test_critique_prompts.py` - Critique prompt testing
- `test_good_bad_format.py` - Format validation
- `test_fixes.py` - General fix verification

**Status**: ✅ Complete

---

## Archive Candidates

These scripts may be superseded or experimental:
- `stage1_critique.py` - Older critique implementation
- `stage1_generate_robust.py` - Alternative generation approach
- `stage1_incremental.py` - Incremental training approach
- `create_preference_pairs_improved.py` - Superseded by logprob version?

**Action Needed**: Review and move to `scripts/archived/` if confirmed obsolete

---

## Key Implementation Patterns

### Chat Template Contamination Prevention ⭐
**ALWAYS do this when loading Qwen base model:**
```python
tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-32B")
tokenizer.chat_template = None  # Disable chat template
inputs = tokenizer(prompt, add_special_tokens=False, return_tensors="pt")
```

**Reference**: `BASE_MODEL_TRUTH.md`, `generate_stage1_sft_data.py:130`

### Few-Shot Completion Prompting ⭐
**ALWAYS use CompletionStylePrompts for base model generation:**
```python
from utils.data_formatter import CompletionStylePrompts
prompt = CompletionStylePrompts.create_response_generation_prompt(instruction)
```

**Reference**: `stage1_generate.py:196`, `DATA_GENERATION_ARCHITECTURE.md`

### Loss Masking for SFT ⭐
**Mask instruction tokens, train only on response:**
```python
# Format: "Instruction: X\nResponse: Y\nEND"
# Mask everything before "Response:"
```

**Reference**: `train_stage1_sft.py`

---

## Quick Reference: "I need to..."

**Generate SFT training data**:
→ Use `generate_stage1_sft_data.py` (note line 402 bug)

**Train SFT model**:
→ Use `train_stage1_sft.py`

**Generate preference pairs**:
→ Use `generate_preference_pairs_logprob.py`

**Train DPO model**:
→ Use `train_stage1_dpo.py`

**Run full pipeline**:
→ Use `run_stage1_pipeline.py`

**Test base model (clean)**:
→ Use `test_base_model_ultra_clean.py`

**Evaluate trained model**:
→ Use `evaluate_stage1_comprehensive.py` (but check memory issue first!)

**Load a model**:
→ Use `utils/model_loader.py`

**Format prompts for base model**:
→ Use `utils/data_formatter.CompletionStylePrompts`

---

**Before implementing anything new**: Search this registry first!
