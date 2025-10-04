# Implementation Registry

**Last Updated**: 2025-10-04
**Purpose**: Track what's been implemented to prevent re-implementation

---

## ⚠️ ADD NEW SCRIPTS IMMEDIATELY

**RULE: When you create a script, add it to this registry in the SAME session**

**Why**: This registry exists to prevent reimplementation. If scripts aren't documented here immediately, the registry can't serve its purpose.

**What happened before**: Registry was 60% incomplete (17/43 scripts), which meant we couldn't reliably check "does X exist?" and ended up reimplementing features.

**Template for new entries**:
```markdown
### `your_script.py` ⭐ BRIEF DESCRIPTION
**Purpose**: What this script does
**Key Features**:
- Feature 1
- Feature 2
**Status**: ✅ Complete / ⏳ In Progress / ⚠️ Has Issues
**Location**: `scripts/your_script.py`
**Dependencies**: What it uses
**Use When**: When to use this vs alternatives
```

**Status markers**:
- ✅ Complete and working
- ⏳ In progress / experimental
- ⚠️ Has known issues (specify)
- ❌ Deprecated (point to replacement)
- 🚨 Critical bug (don't use)

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

### `model_loader.py` ⚠️ DEPRECATED FOR BASE MODEL EVALUATION
**Purpose**: Model loading with proper quantization (Unsloth-based)
**Key Functions**:
- `load_base_model()` - Loads models via Unsloth
- `clear_gpu_cache()` - GPU memory management
- `print_gpu_utilization()` - Monitoring utilities

**Status**: ⚠️ Does NOT disable chat_template - use for TRAINING only
**Critical**: For base model evaluation/generation, use `clean_model_loader.py` instead

### `clean_model_loader.py` ⭐ SAFE BASE MODEL LOADER
**Purpose**: GUARANTEED contamination-free base model loading
**Key Class**: `CleanModelLoader`
**Key Features**:
- ✅ Explicitly disables `chat_template` and `default_chat_template`
- ✅ Uses `add_special_tokens=False` for tokenization
- ✅ Checks ALL tokens for contamination (not just first 10)
- ✅ Uses token IDs (QWEN_CHAT_TOKEN_IDS: 151644, 151645)
- ✅ Runs sentinel prompt tests at load time
- ✅ Returns provenance tracking (git SHA, quantization, etc.)
- ✅ Provides clean `generate()` method
- ✅ Works with raw transformers (not Unsloth)

**Status**: ✅ Complete - ✅ **MIGRATION COMPLETE (15/15 scripts migrated)**
**Critical**: Use this for ALL base model evaluation and data generation

**Migration Status**:
- **✅ Complete**: All 15 base model scripts now use CleanModelLoader
- **Verification**: `scripts/verify_migration_complete.sh` passes (0 manual patterns found)
- **Scripts**: evaluate_*, create_preference_pairs, train_stage1_* all migrated
- **See**: `/docs/MIGRATION_STATUS_20251004.md` for details

**Use When**:
- Evaluating base model capabilities
- Generating training data from base model
- Training (replaces manual contamination prevention)
- Any scenario where chat template contamination would invalidate results

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

### `evaluate_instruction_following.py` ⭐ PRIMARY EVALUATION SCRIPT
**Purpose**: Self-contained instruction-following evaluation
**Lines**: ~600 lines
**Key Features**:
- ✅ Chat template disabled (line 141: `tokenizer.chat_template = None`)
- ✅ add_special_tokens=False (line 220)
- ✅ Comprehensive test suite (12 instruction types)
- ✅ Clear success criteria per example
- ✅ Reproducible (EVAL_SEED = 42)
- Expected performance: Base ~10-30%, SFT ~70-80%, SFT+DPO ~90-95%

**Test Coverage**:
- Explicit commands (lists, sentences, translation)
- Q&A format (math, factual)
- Completion tasks
- Format constraints (word count, numbered lists, yes/no)
- Multi-step instructions
- Harmful request refusal

**Status**: ✅ Ready to use
**Created**: 2025-10-03
**Location**: `scripts/evaluate_instruction_following.py`

### `test_base_model_ultra_clean.py` ⭐ VERIFICATION SCRIPT
**Purpose**: Verify no chat template contamination in base model
**Key Features**:
- ✅ Chat template disabled (line 49: `tokenizer.chat_template = None`)
- ✅ add_special_tokens=False (line 128)
- ✅ Sentinel tests from BASE_MODEL_TRUTH.md
- Tests: translation, lists, JSON, descriptions
- Base model SHOULD FAIL most tests (proves no contamination)

**Status**: ✅ Ready to use (NOT YET RUN - needs GPU)
**Created**: 2025-09-12
**Location**: `scripts/test_base_model_ultra_clean.py`

### `train_stage1_dpo_improved.py` ⭐ PRIMARY DPO TRAINER
**Purpose**: DPO training for Stage 1
**Status**: ✅ Current
**Location**: `scripts/train_stage1_dpo_improved.py`
**Note**: Full documentation needed (check script for details)

### `create_preference_pairs_improved.py` ⭐ PRIMARY PREFERENCE PAIR GENERATOR
**Purpose**: Generate preference pairs for DPO training
**Status**: ✅ Current
**Location**: `scripts/create_preference_pairs_improved.py`
**Note**: Full documentation needed (check script for details)

---

## Deprecated Scripts

### `stage1_generate.py` ❌ DEPRECATED
**Purpose**: Generate responses using base model
**Deprecated**: 2025-10-03
**Reason**: ❌ Chat template contamination - does NOT disable `tokenizer.chat_template`
**Location**: `scripts/archived/2025_10_03_chat_template_contaminated/`
**Use Instead**: `generate_stage1_sft_data.py`

**Note**: While it uses CompletionStylePrompts (line 196), it fails to disable chat_template (line 165), causing contamination.

### `stage1_generate_robust.py` ❌ DEPRECATED
**Purpose**: Robust generation with retry logic
**Deprecated**: 2025-10-03
**Reason**: ❌ Chat template contamination + superseded by more complete script
**Location**: `scripts/archived/2025_10_03_chat_template_contaminated/`
**Use Instead**: `generate_stage1_sft_data.py`

### `generate_stage1_data.py` ❌ DEPRECATED
**Purpose**: Complete Stage 1 data pipeline
**Deprecated**: 2025-10-03
**Reason**: ❌ Uses `model_loader.load_base_model` which doesn't disable chat_template
**Location**: `scripts/archived/2025_10_03_chat_template_contaminated/`
**Use Instead**: `generate_stage1_sft_data.py`

**Note**: Likely generated the Sep 10, 2025 data in `data/stage1/train_instructions.jsonl`.

---

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

### `train_stage1_dpo_improved.py` ⭐ IMPROVED DPO TRAINER
**Purpose**: Enhanced DPO training with better hyperparameters
**Status**: ✅ Current (may supersede train_stage1_dpo.py)
**Location**: `scripts/train_stage1_dpo_improved.py`
**Note**: Check which is actually primary - may need to verify with user

### Other Training Scripts (Experimental/Alternative)
- `train_stage1_dpo_only.py` - DPO without SFT first (experimental)
- `train_dpo_stage1.py` - Earlier DPO version
- `train_dpo_simple.py` - Simple DPO test

**Status**: ⚠️ Multiple versions exist, may be superseded

---

## Evaluation

### ⚠️ CRITICAL MEMORY ISSUE
**Problem**: `evaluate_capability_differentiation.py` loads all models concurrently → OOM
**Fixed in**: `evaluate_capability_differentiation_sequential.py`
**Status**: 🚨 P0 bug tracked in tasks/claude_code/pending/

### `evaluate_stage1_comprehensive.py`
**Purpose**: Comprehensive Stage 1 evaluation
**Status**: ✅ Complete
**Use For**: Full evaluation including multiple metrics

### `evaluate_capability_differentiation.py` ❌ HAS MEMORY BUG
**Purpose**: Evaluate capability differences between models
**Problem**: Loads all models concurrently causing OOM
**Status**: 🚨 Do NOT use - use sequential version instead

### `evaluate_capability_differentiation_sequential.py` ✅ FIXED VERSION
**Purpose**: Sequential model loading to avoid OOM
**Status**: ✅ Use this instead of concurrent version

### `evaluate_sft_model.py`
**Purpose**: SFT model-specific evaluation
**Status**: ✅ Complete

### `evaluate_stage1_corrected.py`
**Purpose**: Corrected evaluation (likely fixes from review feedback)
**Status**: ✅ Complete
**Note**: May supersede evaluate_stage1.py

### `evaluate_stage1_readiness.py`
**Purpose**: Pre-deployment readiness check
**Status**: ✅ Complete
**Use For**: Quick check before RunPod deployment

### `evaluate_stage1_simple.py`
**Purpose**: Simple/quick evaluation for testing
**Status**: ✅ Complete

### `evaluate_stage1.py`
**Purpose**: Original Stage 1 evaluation
**Status**: ⚠️ May be superseded by _corrected or _comprehensive versions

### `evaluate_final.py`
**Purpose**: Final evaluation after all training
**Status**: ✅ Complete
**Use For**: End-to-end comparison of base/SFT/DPO

---

## Testing & Verification

### `test_base_model_definitive.py`
**Purpose**: Earlier version of definitive base model test
**Status**: ⚠️ Superseded by test_base_model_ultra_clean.py

### `test_clean_base_model.py`
**Purpose**: Clean base model testing
**Status**: ⚠️ May be superseded by ultra_clean version

### Evaluation Testing

### `test_ab_logprob_evaluation.py`
**Purpose**: Test A/B evaluation using log probabilities
**Status**: ✅ Experimental test

### `test_binary_evaluation.py`
**Purpose**: Test binary (good/bad) evaluation approach
**Status**: ✅ Experimental test

### `test_critique_prompts.py`
**Purpose**: Test critique prompt generation
**Status**: ✅ Test script

### `test_fixes.py`
**Purpose**: Test bug fixes
**Status**: ✅ Test script

### `test_good_bad_format.py`
**Purpose**: Test good/bad response formatting
**Status**: ✅ Test script

---

## Data Generation & Processing

### `create_preference_pairs_improved.py` (Already documented above as PRIMARY)

### `stage1_critique.py`
**Purpose**: Generate critiques for Stage 1
**Status**: ✅ Complete
**Use For**: Generating constitutional critiques

### `stage1_incremental.py`
**Purpose**: Incremental Stage 1 pipeline with checkpoints
**Status**: ✅ Complete
**Use For**: Long-running generation with inspection points

---

## Utility & Debug Scripts

### `show_prompts.py`
**Purpose**: Display prompts for debugging
**Status**: ✅ Utility
**Use For**: Inspecting prompt formatting

### `show_raw_prompts.py`
**Purpose**: Display raw (unformatted) prompts
**Status**: ✅ Utility
**Use For**: Debugging template application

---

## Utility Modules (scripts/utils/)

### `utils/__init__.py`
**Purpose**: Package initialization
**Status**: ✅ Standard Python package file

### `utils/data_formatter.py` (Already documented above)

### `utils/data_validation.py` (Already documented above)

### `utils/metrics.py` (Already documented above)

### `utils/model_loader.py` (Already documented above)

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
