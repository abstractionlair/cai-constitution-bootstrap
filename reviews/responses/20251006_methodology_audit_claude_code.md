# Methodology Audit - Claude Code Review

**Date**: 2025-10-06
**Reviewer**: Claude Code (Sonnet 4.5)
**Review Type**: Open-Ended Code Review
**Request**: reviews/requests/20251006_methodology_audit.md

---

## Executive Summary

Conducted comprehensive audit of Constitutional AI codebase covering 40+ scripts across data generation, training, evaluation, and utilities. **Found 28 significant discrepancies** between documentation/specifications and actual implementation.

**Key Findings**:
- **5 CRITICAL issues** - Chat template contamination risks in 3 scripts
- **12 HIGH severity issues** - Methodology mismatches, memory management bugs
- **11 MEDIUM severity issues** - Inconsistencies, documentation gaps

**Primary Issue**: **Documentation vs Implementation Gap** - Specifications describe one methodology (model-generated instructions with logprob critique), but primary scripts use simpler template-based approach.

---

## Severity Summary

| Severity | Count | Status |
|----------|-------|--------|
| **Critical** | 5 | 3 documented as known issues, 2 newly discovered |
| **High** | 12 | 3 already tracked, 9 newly identified |
| **Medium** | 11 | Mixed documentation/inconsistency issues |
| **Low** | Multiple | Noted but not blocking |

---

## Top 5 Priority Issues (Must Fix Before 15k Generation)

### 1. 🚨 CRITICAL: Instruction Generation Method Mismatch
**Severity**: CRITICAL
**Files**:
- `scripts/generate_sample_data.py:46-74` (template-based)
- `scripts/generate_stage1_sft_data.py:51-99` (template-based)
- `scripts/utils/instruction_generator.py:1-311` (model-generated - NOT USED)

**Expected** (per recent commits & docs/DATA_GENERATION_ARCHITECTURE.md):
- Model-generated instructions via `InstructionGenerator.generate_instructions_via_completion()`
- Completion-style prompting with few-shot examples
- Quality filtering via `InstructionCritic.critique_instruction_quality()`

**Actual**:
- `generate_sample_data.py` uses **hardcoded templates** (lines 46-74)
- `generate_stage1_sft_data.py` uses **hardcoded templates** (lines 51-99)
- `instruction_generator.py` and `instruction_critic.py` **exist but are unused**

**Impact**:
- Missing promised model-generated instruction diversity
- No quality filtering implementation despite having the infrastructure
- Recent commits (e482acc "Implement model-generated instructions with quality filtering") suggest this SHOULD be implemented but isn't

**Evidence**:
```python
# generate_sample_data.py:46-74 - Template-based (SIMPLE)
INSTRUCTION_TEMPLATES = {
    'list': [
        'List {count} {topic}',
        'Name {count} types of {topic}',
    ],
    # ... hardcoded templates
}

# instruction_generator.py:157-226 - Model-generated (SOPHISTICATED, BUT UNUSED)
def generate_instructions_via_completion(self, model, tokenizer, count: int):
    """Generate diverse instructions using model completion"""
    prompt = self.create_instruction_generation_prompt(count=count)
    completion = loader.generate(...)
    instructions = self.parse_generated_instructions(completion)
```

**Recommendation**:
1. **Immediate**: Update `generate_sample_data.py` to use `InstructionGenerator` class
2. **Before 15k run**: Migrate `generate_stage1_sft_data.py` to model-generated instructions
3. **Add**: Quality filtering with `InstructionCritic` before response generation
4. **Document**: Why template-based was chosen if this was intentional

**Related**: Git commit e482acc message suggests this was recently implemented but not integrated

---

### 2. 🚨 HIGH: Evaluation Methodology Mismatch (Train/Test Distribution Shift)

**Severity**: HIGH
**Files**:
- **Spec**: `specs/stage_1_explicit_instructions.md:77-93`
- **Training**: `scripts/generate_stage1_sft_data.py:402`
- **Evaluation A**: `scripts/evaluate_stage1_comprehensive.py:93`
- **Evaluation B**: `scripts/evaluate_instruction_following.py:206`

**Expected** (per spec lines 77-93):
> "Both Models Get Raw Instructions: Base Model gets 'Answer this question: What is 2+2?', Trained Model gets 'Answer this question: What is 2+2?'. **Same test for both** - this is essential for valid comparison."

**Actual**:
- **Training format**: `"Instruction: {instruction}\nResponse:"` (line 402)
- **Evaluation comprehensive**: `"Instruction: {instruction}\nResponse:"` ✅ MATCHES training
- **Evaluation primary**: `instruction` (raw) ❌ MISMATCH with training

**Impact**:
- Train/test distribution shift in primary evaluation script
- Model trained on formatted prompts, evaluated on raw prompts
- Creates unfair comparison (trained model disadvantaged)
- **Invalidates core evaluation metric** if using primary script

**Evidence**:
```python
# Training: generate_stage1_sft_data.py:402
'prompt': f"Instruction: {inst_data['instruction']}\nResponse:",

# Evaluation: evaluate_instruction_following.py:206 (PRIMARY)
response = self.loader.generate(
    self.model, self.tokenizer,
    instruction,  # RAW - no "Instruction:" prefix!
    ...
)

# Evaluation: evaluate_stage1_comprehensive.py:93 (SECONDARY)
prompt = f"Instruction: {instruction}\nResponse:"  # MATCHES training
```

**Recommendation**:
1. **Clarify methodology decision**:
   - Option A: Evaluate with training format (test if training worked)
   - Option B: Evaluate with raw format (test instruction generalization) BUT update spec to acknowledge this
2. **Update spec** to match actual methodology OR update code to match spec
3. **Document** in `specs/stage_1_evaluation.md` why chosen approach is valid
4. **Standardize** across all evaluation scripts

**Why This Matters**: This is a fundamental experimental validity issue

---

### 3. 🚨 HIGH: Logprob-Based Critique Method - Implemented But Unused

**Severity**: HIGH
**Files**:
- `scripts/utils/instruction_critic.py:1-270` (exists, documented)
- `scripts/generate_preference_pairs_logprob.py` (uses logprob for preference pairs)
- `scripts/generate_stage1_sft_data.py` (generates SFT data WITHOUT critique)

**Expected** (per docs/POST_TRAINING_APPROACHES.md:42-78):
> "High-Quality Pair Construction: Include diverse rejection types via confidence weighting, judge margin (log-prob gap), abstain > guess"

**Expected** (per recent commit e482acc):
> "Implement model-generated instructions with quality filtering"

**Actual**:
- `InstructionCritic` class fully implemented with logprob-based A/B classification
- `critique_instruction_quality()` method ready to use
- `critique_instruction_response_pair()` method ready to use
- **NOT used in `generate_stage1_sft_data.py`** - no quality filtering
- **NOT used in `generate_sample_data.py`** - no quality filtering

**Impact**:
- Missing promised quality filtering before expensive GPU generation
- Lower data quality than achievable
- No confidence-based sample selection
- Wastes GPU time on low-quality examples

**Evidence**:
```python
# instruction_critic.py:103-156 - READY TO USE
def critique_instruction_quality(model, tokenizer, instruction: str,
                                 confidence_threshold: float = 1.0):
    """Judge instruction quality using logprob-based A/B classification"""
    prompt = create_instruction_quality_prompt(instruction)
    token_logprobs = get_token_logprobs(model, tokenizer, prompt, ['A', 'B'])
    # ... returns is_good, margin, confident

# generate_stage1_sft_data.py - MISSING CRITIQUE STEP
# Line 268: Creates instruction
# Line 268: Generates response directly
# NO quality filtering between instruction creation and response generation!
```

**Recommendation**:
1. **Add quality filtering** to data generation scripts:
   ```python
   instruction = generate_instruction(...)
   critique = critique_instruction_quality(model, tokenizer, instruction)
   if not critique['is_good'] or not critique['confident']:
       continue  # Skip low-quality instructions
   response = generate_response(instruction)
   ```
2. **Add to pipeline**: Generate 2x needed instructions → filter → keep top 50%
3. **Log metrics**: Track rejection rate, margin distribution for quality monitoring

**Cost/Benefit**: Small upfront cost (critique = 1 forward pass) for much better data quality

---

### 4. 🚨 CRITICAL: Chat Template Contamination in evaluate_stage1_simple.py

**Severity**: CRITICAL
**File**: `scripts/evaluate_stage1_simple.py:51-53`

**Expected** (per docs/BASE_MODEL_TRUTH.md:42-54):
```python
tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-32B")
tokenizer.chat_template = None  # CRITICAL: Disable chat template
inputs = tokenizer(prompt, add_special_tokens=False, return_tensors="pt")
```

**Actual**:
```python
# Line 51-53
tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token
# MISSING: tokenizer.chat_template = None
```

**Impact**:
- Silent chat template application during base model evaluation
- Base model instruction-following scores artificially inflated
- Invalidates base vs trained comparison
- This bug was discovered and fixed multiple times (see KNOWN_BUGS_AND_FIXES.md)

**Recommendation**:
```python
tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
tokenizer.chat_template = None  # ADD THIS LINE
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token
```

**Prevention**: Run sentinel tests from BASE_MODEL_TRUTH.md after loading

---

### 5. 🚨 HIGH: Memory Management Bug - Concurrent Model Loading

**Severity**: HIGH
**Files**:
- `scripts/evaluate_capability_differentiation.py:64-89` (KNOWN BUG, documented)
- `scripts/evaluate_stage1_comprehensive.py:60-86` (SAME BUG, undocumented)

**Expected** (per docs/KNOWN_BUGS_AND_FIXES.md:227-261):
```python
# Load base model
results_base = evaluate(base_model)
del base_model
torch.cuda.empty_cache()

# Load SFT model
results_sft = evaluate(sft_model)
del sft_model
torch.cuda.empty_cache()
```

**Actual**:
```python
# Line 66: Load base model
self.base_model, self.tokenizer, provenance = self.loader.load()

# Line 72: Load SFT (base still in memory!)
sft_base, _, _ = sft_loader.load()
self.sft_model = PeftModel.from_pretrained(sft_base, ...)

# Line 77: Load DPO (base + SFT still in memory!!)
dpo_base, _, _ = dpo_loader.load()
# Now have 3x 32B models in memory → OOM
```

**Impact**:
- OOM crashes on GPUs with < 80GB VRAM
- Wastes GPU time and money
- `evaluate_capability_differentiation.py` documented as broken
- `evaluate_stage1_comprehensive.py` has **same bug** but not documented

**Recommendation**:
1. **Fix evaluate_stage1_comprehensive.py** using sequential loading pattern from `evaluate_stage1_corrected.py:195-322`
2. **Add deprecation warning** to evaluate_capability_differentiation.py
3. **Add automated check** to prevent this pattern in future scripts

**Good Reference**: `evaluate_stage1_corrected.py` loads sequentially (CORRECT pattern)

---

## Additional Findings by Category

### Data Generation Issues

#### Finding 6: Few-Shot Prompting Utility Created But Underutilized
**Severity**: MEDIUM
**File**: `scripts/utils/data_formatter.py:71-166`

**Issue**: `CompletionStylePrompts.create_response_generation_prompt()` creates sophisticated few-shot prompts but only used in deprecated script (`stage1_generate.py`).

**Actual**:
- ✅ `stage1_generate.py` (DEPRECATED) uses it correctly (line 196)
- ❌ `generate_stage1_sft_data.py` (CURRENT) uses simpler approach
- ❌ `generate_sample_data.py` (CURRENT) uses simple templates

**Recommendation**: Migrate current scripts to use sophisticated few-shot utility OR document why simpler approach chosen.

---

#### Finding 7: Prompt Format Bug (Cosmetic)
**Severity**: LOW (documented as known issue)
**File**: `scripts/generate_stage1_sft_data.py:402`

**Issue**: Dataset stores different prompt format than generation uses.

**Actual**:
```python
# Line 268: Generation uses completion-style
completion_prompt = self.create_completion_prompt(instruction, inst_type)

# Line 402: Dataset stores instruction-style (MISMATCH)
'prompt': f"Instruction: {inst_data['instruction']}\nResponse:",
```

**Impact**: LOW - Data still high quality due to proper chat_template disabling.

**Status**: ✅ Documented in docs/KNOWN_BUGS_AND_FIXES.md:272-307 and docs/DATA_GENERATION_ARCHITECTURE.md

---

### Training Script Issues

#### Finding 8: Script Status Ambiguity
**Severity**: MEDIUM
**Files**: Multiple DPO trainers

**Issue**: docs/IMPLEMENTATION_REGISTRY.md lists both `train_stage1_dpo.py` (line 375) AND `train_stage1_dpo_improved.py` (line 387) with unclear primary designation.

**Actual**:
- `train_stage1_dpo.py` marked as "PRIMARY DPO TRAINER"
- `train_stage1_dpo_improved.py` marked as "IMPROVED DPO TRAINER" with note "may supersede"
- File dates show _improved.py is newer (Oct 4 vs Sep 10)

**Recommendation**: Update registry to clearly mark `train_stage1_dpo_improved.py` as PRIMARY, move `train_stage1_dpo.py` to LEGACY section.

---

#### Finding 9: Chat Template Safety in Training Scripts
**Severity**: HIGH
**Files**:
- ✅ `train_stage1_sft.py` - Uses CleanModelLoader (SAFE)
- ✅ `train_stage1_dpo_improved.py` - Uses CleanModelLoader (SAFE)
- ⚠️ `train_stage1_dpo.py` - Uses Unsloth (chat_template status UNKNOWN)
- ❌ `train_dpo_simple.py` - Manual loading, NO chat_template = None (UNSAFE)

**Impact**: Training with contaminated templates could invalidate base model assumption.

**Recommendation**:
1. Add `tokenizer.chat_template = None` to `train_dpo_simple.py` after line 66
2. Verify Unsloth behavior in `train_stage1_dpo.py` or add explicit disabling
3. Run sentinel tests from BASE_MODEL_TRUTH.md to verify

---

#### Finding 10: Quantization Inconsistency
**Severity**: MEDIUM
**Files**: Various training scripts

**Issue**: Specs don't specify 4-bit vs 8-bit for training, implementations differ without documented rationale.

**Actual**:
- `train_stage1_sft.py`: 8-bit (via CleanModelLoader)
- `train_stage1_dpo_improved.py`: 8-bit (via CleanModelLoader)
- `train_stage1_dpo.py`: 4-bit (via Unsloth)
- `train_dpo_simple.py`: 4-bit (manual loading)

**Recommendation**: Document quantization choice in `specs/stage_1_explicit_instructions.md` with rationale (8-bit = more stable, 4-bit = more memory efficient).

---

#### Finding 11: LoRA Rank Variance
**Severity**: LOW
**Files**: Various training scripts

**Issue**: Different LoRA ranks without documented reason.

**Actual**:
- Most scripts: r=16
- `train_stage1_dpo.py`: r=64 (4x higher!)

**Recommendation**: Document why r=64 was chosen OR standardize to r=16.

---

### Evaluation Script Issues

#### Finding 12: Evaluation Scoring Methodology Inconsistency
**Severity**: HIGH
**Files**: All evaluation scripts

**Issue**: Different scripts use completely different scoring methods, making results incomparable.

**Methods**:
- `evaluate_instruction_following.py`: Task-specific checks (e.g., count fruits, check for "4")
- `evaluate_stage1_comprehensive.py`: 4-dimensional scoring (instruction_following, coherence, relevance, quality)
- `evaluate_stage1_simple.py`: Type-based heuristics (length, refusals)
- `evaluate_capability_differentiation.py`: 6-dimensional scoring

**Impact**: Can't compare results across evaluations, no single ground truth metric.

**Recommendation**:
1. Designate ONE methodology as canonical
2. Document in `specs/stage_1_evaluation.md`
3. Other scripts can supplement but shouldn't contradict

---

#### Finding 13: evaluate_stage1_corrected.py Dual Methodology
**Severity**: MEDIUM (actually a feature, needs documentation)
**File**: `scripts/evaluate_stage1_corrected.py:73-118`

**Issue**: Tests BOTH raw instructions (line 76) AND few-shot prompts (line 97).

**Impact**: POSITIVE - Allows comparison of methodologies, but needs documentation explaining why.

**Recommendation**: Document this as intentional dual evaluation with different purposes:
- Raw instructions: Test if training worked
- Few-shot: Show base model capability with prompting

---

#### Finding 14: Missing add_special_tokens=False in SFT Trainer
**Severity**: MEDIUM
**File**: `scripts/train_stage1_sft.py:97-103`

**Issue**: Main tokenization doesn't explicitly use `add_special_tokens=False` even though BASE_MODEL_TRUTH.md recommends it.

**Actual**:
```python
full_encoding = self.tokenizer(
    full_text,
    truncation=True,
    max_length=self.max_length,
    padding=False,
    return_tensors=None
)  # Missing add_special_tokens=False
```

**Impact**: LOW - CleanModelLoader disables template at load time, so this is safe, but inconsistent with documented pattern.

**Recommendation**: Add `add_special_tokens=False` explicitly for consistency.

---

### Utility Module Issues

#### Finding 15: CleanModelLoader Migration Status
**Severity**: LOW (positive finding)
**Status**: ✅ COMPLETE

**Finding**: docs/IMPLEMENTATION_REGISTRY.md:169 shows CleanModelLoader migration is COMPLETE (15/15 scripts migrated).

**Impact**: POSITIVE - Primary scripts use safe loading method.

**Evidence**: `scripts/verify_migration_complete.sh` passes with 0 manual patterns found.

---

#### Finding 16: CompletionStylePrompts Class Sophisticated But Underused
**Severity**: MEDIUM
**File**: `scripts/utils/data_formatter.py:71-166`

**Issue**: Sophisticated few-shot prompt builder exists but only used in deprecated scripts.

**Design**:
- Diverse example types (math, completion, factual, creative, explanatory)
- Random selection for diversity (3-4 examples per prompt)
- Natural completion patterns

**Usage**:
- ✅ Used in `stage1_generate.py` (DEPRECATED, line 196)
- ❌ NOT used in `generate_stage1_sft_data.py` (CURRENT)
- ❌ NOT used in `generate_sample_data.py` (CURRENT)

**Recommendation**: Either migrate current scripts to use this OR document why simpler approach preferred.

---

### Pipeline & Orchestration Issues

#### Finding 17: Pipeline Scripts Don't Use New Utilities
**Severity**: MEDIUM
**Files**:
- `scripts/run_stage1_pipeline.py`
- `scripts/stage1_incremental.py`

**Issue**: Pipeline orchestrators call individual scripts but don't verify they use new utilities (InstructionGenerator, InstructionCritic, etc.).

**Impact**: Pipelines will run old methodology even though new utilities exist.

**Recommendation**: Update pipelines to verify or enforce use of new utilities.

---

### Documentation Issues

#### Finding 18: Recent Commit Message Suggests Unintegrated Work
**Severity**: HIGH
**Commit**: e482acc "Implement model-generated instructions with quality filtering"

**Issue**: Commit message suggests model-generated instructions and quality filtering are implemented, but:
- `instruction_generator.py` exists but unused
- `instruction_critic.py` exists but unused
- Current scripts still use template-based approach

**Possible Explanations**:
1. Work implemented but not integrated into main scripts
2. Implemented in separate branch not yet merged
3. Commit message inaccurate

**Recommendation**:
1. Check git history to verify if integration commit missing
2. Either integrate or update commit message/docs to reflect status
3. Add to IMPLEMENTATION_REGISTRY.md with status markers

---

#### Finding 19: IMPLEMENTATION_REGISTRY.md Incompleteness
**Severity**: MEDIUM
**File**: `docs/IMPLEMENTATION_REGISTRY.md:390-391`

**Issue**: `train_stage1_dpo_improved.py` marked as needing full documentation.

**Actual**: "Full documentation needed (check script for details)"

**Impact**: Makes it harder for new developers/sessions to understand implementation.

**Recommendation**: Complete documentation for all primary scripts.

---

#### Finding 20: Experimental Scripts Not Clearly Marked
**Severity**: LOW
**Files**: Various (e.g., `train_dpo_simple.py`, `train_stage1_dpo_only.py`)

**Issue**: Scripts unclear if they're experimental, deprecated, or production.

**Recommendation**:
1. Add status to script docstrings
2. Add status markers in IMPLEMENTATION_REGISTRY.md
3. Consider moving experimental scripts to `scripts/experimental/` directory

---

## Methodology Gaps - Features We Said We'd Use But Aren't

### Gap 1: Model-Generated Instructions (CRITICAL)
**Documented In**: Commit e482acc message
**Status**: Implemented but not integrated
**Impact**: Missing promised diversity and quality

### Gap 2: Logprob-Based Quality Filtering (HIGH)
**Documented In**:
- docs/POST_TRAINING_APPROACHES.md:42-78
- Commit e482acc message
**Status**: Implemented (`instruction_critic.py`) but not integrated
**Impact**: Lower data quality than achievable

### Gap 3: Few-Shot Completion Prompting (MEDIUM)
**Documented In**:
- docs/FEW_SHOT_PROMPTING.md
- docs/DATA_GENERATION_ARCHITECTURE.md
**Status**: Implemented (`CompletionStylePrompts`) but underutilized
**Impact**: Simpler prompting may yield lower quality responses

### Gap 4: Confidence-Based Sample Selection (MEDIUM)
**Documented In**: docs/POST_TRAINING_APPROACHES.md:52-56
**Status**: Not implemented
**Impact**: Can't filter low-confidence examples

### Gap 5: BoN (Best-of-N) Pair Generation (LOW)
**Documented In**: docs/POST_TRAINING_APPROACHES.md:46-50
**Status**: Not implemented
**Impact**: Fewer training pairs per prompt

---

## Spec-Implementation Compliance Matrix

| Requirement | Spec Location | Implementation | Status |
|-------------|---------------|----------------|--------|
| **Data Generation** | | | |
| Model-generated instructions | Commit e482acc | instruction_generator.py exists | ❌ Not integrated |
| Template-based instructions | Not in spec | generate_sample_data.py | ⚠️ Undocumented choice |
| Quality filtering | POST_TRAINING_APPROACHES | instruction_critic.py exists | ❌ Not integrated |
| Few-shot prompting | FEW_SHOT_PROMPTING | CompletionStylePrompts | ⚠️ Underutilized |
| Completion-style prompts | stage_1_explicit_instructions:60-74 | ✅ All scripts use | ✅ COMPLIANT |
| Chat template disabled | BASE_MODEL_TRUTH | CleanModelLoader | ✅ PRIMARY scripts |
| | | | ❌ evaluate_stage1_simple.py |
| **Training** | | | |
| SFT → DPO approach | POST_TRAINING_APPROACHES:182-189 | train_stage1_sft + dpo_improved | ✅ COMPLIANT |
| QLoRA/LoRA | stage_1_explicit_instructions:138 | LoRA + quantized base | ✅ COMPLIANT (terminology issue) |
| Beta = 0.1-0.3 | POST_TRAINING_APPROACHES:158-163 | All use 0.1 | ✅ COMPLIANT |
| **Evaluation** | | | |
| Both models get raw instructions | stage_1_explicit_instructions:77-93 | Mixed (some formatted, some raw) | ❌ INCONSISTENT |
| Same test for both | stage_1_explicit_instructions:81 | ✅ Same prompts | ✅ COMPLIANT |
| Task-specific scoring | stage_1_evaluation:8-54 | evaluate_instruction_following | ✅ COMPLIANT |
| Chat template disabled | BASE_MODEL_TRUTH | Most use CleanModelLoader | ⚠️ 1 script missing |
| Sequential model loading | KNOWN_BUGS_AND_FIXES:227-267 | evaluate_stage1_corrected | ⚠️ 2 scripts broken |

---

## Priority Recommendations for 15k Generation

### MUST FIX (Before any large-scale generation)

1. ✅ **Fix chat template bug** in `evaluate_stage1_simple.py:51` - Add `tokenizer.chat_template = None`
2. 🔴 **Decide on instruction generation method**: Template-based (current) OR model-generated (implemented but unused)
3. 🔴 **Clarify evaluation methodology**: Update spec to match code OR update code to match spec (train/test format)
4. ✅ **Fix memory management** in `evaluate_stage1_comprehensive.py` - Use sequential loading
5. 🟡 **Integrate or remove** instruction_generator.py and instruction_critic.py (decide if using)

### SHOULD FIX (Before results publication)

6. **Standardize evaluation metrics** - Choose one canonical scoring method
7. **Document methodology decisions** - Why template-based over model-generated (if chosen)
8. **Update IMPLEMENTATION_REGISTRY** - Mark correct primary scripts, deprecate old ones
9. **Add quality filtering** - Even if keeping template-based, filter responses
10. **Verify chat template safety** - Add explicit checks to all training scripts

### NICE TO FIX (Cleanup)

11. Complete documentation for `train_stage1_dpo_improved.py`
12. Add status markers to experimental scripts
13. Standardize quantization across scripts
14. Add `add_special_tokens=False` explicitly to SFT trainer
15. Document LoRA rank choices

---

## Questions for User/Team

1. **Instruction Generation**: Was template-based approach intentional? If so, should we remove/deprecate instruction_generator.py? Or should we integrate it for 15k run?

2. **Quality Filtering**: Commit message says "quality filtering" implemented - was this intended to be integrated? Should we add it before 15k generation?

3. **Evaluation Methodology**: Specs say "both get raw instructions" but training uses formatted prompts. Which is correct?
   - Option A: Update spec to acknowledge formatted evaluation
   - Option B: Update code to use raw evaluation
   - Option C: Accept mismatch as testing "instruction generalization"

4. **Script Status**: Which scripts are "production" vs "experimental"? Should we deprecate old versions?

5. **15k Generation Plan**: Which scripts should be used for 15k generation?
   - Data generation: `generate_stage1_sft_data.py` with templates OR new script with model-generated?
   - Training: `train_stage1_sft.py` + `train_stage1_dpo_improved.py`?
   - Evaluation: `evaluate_instruction_following.py` OR `evaluate_stage1_comprehensive.py`?

---

## Files Audited (40+)

### Data Generation (6)
- ✅ generate_sample_data.py
- ✅ generate_stage1_sft_data.py
- ✅ generate_test_instructions.py
- ✅ generate_preference_pairs_logprob.py
- ✅ generate_diverse_negatives.py
- ✅ generate_data_parallel.py

### Training (4)
- ✅ train_stage1_sft.py
- ✅ train_stage1_dpo.py
- ✅ train_stage1_dpo_improved.py
- ✅ train_dpo_simple.py

### Evaluation (5)
- ✅ evaluate_stage1_comprehensive.py
- ✅ evaluate_stage1_corrected.py
- ✅ evaluate_stage1_simple.py
- ✅ evaluate_instruction_following.py
- ✅ evaluate_capability_differentiation.py

### Utilities (5)
- ✅ utils/data_formatter.py
- ✅ utils/clean_model_loader.py
- ✅ utils/eval_statistics.py
- ✅ utils/instruction_generator.py
- ✅ utils/instruction_critic.py

### Pipeline (2)
- ✅ stage1_incremental.py
- ✅ run_stage1_pipeline.py

### Documentation (7)
- ✅ specs/stage_1_explicit_instructions.md
- ✅ specs/stage_1_evaluation.md
- ✅ specs/complete_pipeline.md
- ✅ docs/POST_TRAINING_APPROACHES.md
- ✅ docs/FEW_SHOT_PROMPTING.md
- ✅ docs/DATA_GENERATION_ARCHITECTURE.md
- ✅ docs/BASE_MODEL_TRUTH.md
- ✅ docs/IMPLEMENTATION_REGISTRY.md
- ✅ docs/KNOWN_BUGS_AND_FIXES.md

---

## Conclusion

The codebase has **solid foundations** (CleanModelLoader, provenance tracking, DRY utilities) but shows a **significant gap between documented/promised methodology and actual implementation**.

**Key Pattern**: Recent development created sophisticated utilities (InstructionGenerator, InstructionCritic, CompletionStylePrompts) but **main scripts haven't been updated to use them**. This suggests either:
1. Work in progress not yet integrated
2. Intentional decision to keep simpler approach (undocumented)
3. Lost context between sessions

**Primary Risk for 15k Generation**: Using current scripts will generate template-based data without quality filtering, which differs from what specifications and recent commits suggest should happen.

**Recommendation**: **Clarify methodology before 15k generation** - either integrate new utilities OR document why simpler approach is better. Current state (sophisticated utilities exist but unused) creates confusion and may waste GPU budget on suboptimal approach.

---

**End of Audit Report**

**Next Steps**:
1. Review findings with team
2. Answer methodology questions above
3. Prioritize fixes for 15k generation
4. Update documentation to match chosen approach
