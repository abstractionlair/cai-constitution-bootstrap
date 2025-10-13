# Stage 1 Findings & Project Pivot

**Date**: 2025-10-13
**Status**: Stage 1 invalidated, pivoting to Stage 1B (conversation ability)

---

## Executive Summary

Stage 1 SFT training completed successfully, but evaluation revealed the experimental premise was flawed. The base model (Qwen/Qwen2.5-32B) already possesses instruction-following capability when given simple formatting cues, making the training target invalid.

**Key finding**: Modern base models (2024+) have emergent instruction-following from pretraining. Post-training teaches refinement, not fundamental capabilities.

**Decision**: Pivot to conversation ability (multi-turn context tracking) as the target for Stage 1B.

---

## What Happened in Stage 1

### Training Completed Successfully

**SFT Training Results**:
- Model: Qwen/Qwen2.5-32B with QLoRA (16.7M trainable params)
- Training data: 5,467 instruction-response pairs
- Duration: 1.2 hours on L40S GPU
- Final loss: 0.587 (down from 1.67)
- Token accuracy: 82.5% (up from 65.3%)
- Cost: ~$2.40-3.60

**Technical success**: Training ran smoothly, no issues with:
- Model loading (all contamination guards passed)
- QLoRA configuration
- Training convergence
- Checkpoint saving

### Evaluation Revealed Fatal Flaw

**Initial results** (invalid):
- Base model: 81% success
- SFT model: 99.3% success
- McNemar p = 2×10⁻¹²
- Appeared to pass gate

**Problems discovered**:
1. **Broken scoring heuristic**: Marked responses >500 chars as "failure"
2. **More critically**: Base model was actually following instructions correctly

### Manual Review Findings

**Unambiguous instruction-following from base model**:
- "Translate 'thank you' to Spanish" → "Gracias." ✅
- "Translate 'hello' to German" → "Hallo" ✅
- "List five planets" → "Mercury, Venus, Earth, Mars, Jupiter" ✅
- "Describe side using only five words" → "Left, right, top, bottom, center" ✅

**All 57 "improvements" were just response length**:
- Base responses: Correct but verbose (>500 chars)
- SFT responses: Correct and concise (<500 chars)
- No difference in instruction-following capability

**Recounted with correct scoring**:
- Base model: 300/300 = 100% ✅
- SFT model: 298/300 = 99.3%
- **Real improvement: -0.7%** (SFT slightly worse)

---

## Root Cause Analysis

### Why Did Base Model Follow Instructions?

**The format matters**: Evaluation used `"Instruction: {instruction}\nResponse:"` format

**Hypothesis**: This simple format activates instruction-following behavior that Qwen 2.5 learned during pretraining:
- Modern base models (2024+) trained on diverse web data
- Pretraining corpora include instruction-response pairs naturally
- Format cue is sufficient to trigger this learned behavior

**Evidence from sentinel tests**:
- **Raw prompts** (no format): Base model rambles, doesn't follow instructions ✅
- **Formatted prompts**: Base model follows instructions perfectly ✅
- **Conclusion**: Format cue makes the difference, not SFT training

### What Did SFT Training Actually Teach?

Looking at paired responses where both succeeded (241 cases):
- **Primary difference**: Response length (base verbose, SFT concise)
- **Secondary differences**: Minor formatting/style preferences
- **NOT learned**: Basic instruction-following (already present)

**Conclusion**: SFT taught response style, not capability.

---

## Implications for Project

### Original Hypothesis

> Base models "know" enough to generate samples for post-training via CAI-like mechanisms.

**Status**: Partially validated
- ✅ Base models can generate instruction-response pairs
- ✅ Base models can critique quality (logprob critics work)
- ❌ Base models DON'T need training for simple instruction-following
- ❓ Need to test on capabilities base models actually lack

### What This Means

**Modern base models already have**:
- Instruction-following (with format cues)
- Factual knowledge
- Basic reasoning
- Language understanding

**What post-training likely adds** (based on Qwen Instruct claims):
- Multi-turn conversation ability
- System prompt adherence
- Role-playing capabilities
- Structured output (JSON, tables)
- Long-form coherent generation (8K+ tokens)
- Safety/refusal training
- Response calibration (brevity vs detail)

**For our experiment**: We need to target a capability that's genuinely missing from base models.

---

## Pivot to Stage 1B: Conversation Ability

### Why Conversation?

**Multi-turn conversation requires**:
- Context tracking across turns
- Reference resolution ("it", "that")
- Information persistence ("Remember I said X")
- Implicit context handling

**Expected gap**:
- Base models: Pretrained on documents, not dialogues
- Instruct models: Post-trained on conversation data
- Should show clear base-fail / instruct-succeed pattern

### Codex Validation

**First review** (project pivot): MODIFY - conversation viable but needs formal spec
**Second review** (evaluation spec): MODIFY - fix scoring and baseline config

**Codex feedback incorporated**:
- ✅ Written formal evaluation spec
- ✅ LLM-as-judge as primary scoring
- ✅ Heuristics demoted to triage/diagnostic
- ✅ Specified exact generation loop algorithm
- ✅ Three-way evaluation (base, instruct, alt-base)
- ✅ 200 conversations with power analysis documented
- ✅ Human calibration required (κ ≥ 0.7)

---

## New Experimental Plan

### Phase 1: Evaluation First (CRITICAL)

**Before any training**:

1. Design 200 conversation benchmark
   - 4 categories: memory, preferences, topic continuity, constraint updates
   - Each conversation: 3-5 turns with context dependencies
   - Store expected entities/constraints with each conversation

2. Evaluate three models:
   - Qwen/Qwen2.5-32B (base)
   - Qwen/Qwen2.5-32B-Instruct
   - meta-llama/Llama-3.1-8B (alt-base sanity check)

3. Score with LLM-as-judge (Claude 3.5 Sonnet)
   - Human calibrate on 30 conversations (κ ≥ 0.7)
   - Spot-check 10% with GPT-4

4. Statistical validation:
   - Base: ≤ 30% success (must fail)
   - Instruct: ≥ 80% success (must succeed)
   - McNemar p < 0.01
   - Cohen's h ≥ 0.5

5. **User confirmation**: Review sample conversations to verify gap is real

### Phase 2: Only If Gap Confirmed

**If Phase 1 passes all gates**:

1. Design conversation data generation pipeline
2. Generate multi-turn training data using base model
3. Train SFT model on conversation data
4. Re-evaluate to measure improvement
5. Compare to Instruct model

**If Phase 1 fails** (base model can already converse):
- Pivot to different capability (JSON, system prompts, long-form, etc.)
- Repeat evaluation-first approach

---

## Lessons Learned

### Never Train Without Proving Gap Exists

**Stage 1 mistake**: Assumed base model couldn't follow instructions
**Stage 1 reality**: Base model already had this capability
**Result**: Wasted $4-6 and 2 hours training on wrong target

**New rule**: Always evaluate base vs instruct FIRST
- Must prove base fails (< 30%)
- Must prove instruct succeeds (> 80%)
- Must validate with multiple scoring methods
- Must get user confirmation before training

### Scoring Heuristics Are Dangerous

**Stage 1 mistake**: Used simple length-based heuristic
**Result**: Completely invalid evaluation, false conclusions

**New approach**:
- LLM-as-judge as primary scoring
- Human calibration required (κ ≥ 0.7)
- Heuristics only for triage/diagnostics
- Multiple validation methods

### Sentinel Tests Need Updating

**Current sentinel tests**: Check raw prompts without formatting
**Finding**: Format matters a lot for modern base models

**Action needed**: Update `docs/BASE_MODEL_TRUTH.md` to document:
- Raw prompts: Base model doesn't follow instructions ✅
- `"Instruction: X\nResponse:"` format: Base model DOES follow instructions
- Conversation format: Unknown (Phase 1 will test this)

---

## Budget Status

### Stage 1 Costs (Completed)

- Data generation: ~$0 (cached models, CPU work)
- SFT training: ~$2.40-3.60 (1.2 hours L40S)
- Evaluation: ~$1.50-2.75 (0.9 hours L40S)
- **Total spent**: ~$4-6.50

### Remaining Budget

- **Total allocated**: $300
- **Spent**: ~$6
- **Remaining**: ~$294

**Plenty of budget** for Stage 1B evaluation and training.

---

## Current Status

### Completed Artifacts

**Valid work**:
- ✅ Data generation pipeline (reusable)
- ✅ CleanModelLoader utility (validated)
- ✅ Logprob critic utilities (working)
- ✅ SFT training script (works, just used on wrong target)
- ✅ Quality control procedures (sound)

**Invalid work**:
- ❌ Stage 1 SFT model (trained on capability base already has)
- ❌ Stage 1 evaluation results (broken scoring)
- ❌ Stage 1 gate decision (invalid)

### Next Steps

**Immediate** (tonight/tomorrow):
1. ✅ Conversation evaluation spec drafted
2. ✅ Codex review received (MODIFY with specific fixes)
3. ✅ Spec revised per Codex feedback
4. → Commit and push changes
5. → Stop pod for the night

**Next session**:
1. Implement conversation benchmark generator
2. Generate 30-40 pilot conversations
3. Implement LLM-as-judge scorer
4. Run pilot evaluation (base, instruct, llama)
5. Human calibration (30 conversations)
6. Get user confirmation gap is real
7. Proceed to full benchmark if pilot passes

---

## Key Insights

### What We Learned About Modern Base Models

**Qwen/Qwen2.5-32B capabilities**:
- ✅ Follows simple instructions (with format cue)
- ✅ Handles factual questions
- ✅ Performs translations, lists, counting
- ❓ Multi-turn conversation (unknown - will test)
- ❓ System prompt adherence (unknown)
- ❓ Structured output (unknown)

**Implications**:
- Base models from 2024+ are more capable than expected
- Pretraining on high-quality web data includes instruction examples
- Post-training may be more about refinement than teaching new capabilities
- Need to carefully select targets that base models genuinely lack

### What Instruct Models Likely Add

Based on Qwen marketing and our observations:
- Multi-turn conversation and context tracking
- System prompt adherence and role-playing
- Structured output (JSON, tables)
- Long-form coherent generation
- Safety and appropriate refusals
- Calibrated response length
- **NOT**: Basic instruction-following

---

## Files Updated

### New Specifications
- `specs/stage1b_conversation_eval_spec.md` - Conversation evaluation spec (DRAFT v2)

### Documentation
- `docs/STAGE1_FINDINGS_AND_PIVOT.md` - This file
- `docs/STAGE1_SFT_TRAINING_COMPLETE.md` - Training documentation (valid)
- `docs/STAGE1_EVALUATION_COMPLETE.md` - Evaluation documentation (INVALID - broken scoring)

### Codex Reviews
- `reviews/responses/20251012_stage1_evaluation_validity_codex.md` - Evaluation invalid
- `reviews/responses/20251013_stage1_conversation_pivot_codex.md` - Pivot approved with caveats
- `reviews/responses/20251013_stage1b_conversation_eval_codex.md` - Spec needs fixes (MODIFY)

### Code (Still Valid)
- `scripts/generate_stage1_pilot_data.py` - Data generation (reusable)
- `scripts/generate_diversity_guided.py` - Diversity generation (reusable)
- `scripts/train_stage1_sft.py` - Training script (reusable)
- `scripts/utils/clean_model_loader.py` - Contamination guards (validated)

---

## Action Items Before Next Session

**User confirmation needed**:
- Review conversation evaluation spec
- Confirm approach sounds reasonable
- Approve pivot to conversation ability

**Next session work**:
- Implement conversation benchmark
- Run pilot evaluation
- Validate gap exists
- Only proceed to training if gap confirmed

---

**Status**: Ready to commit changes and stop pod
**Next milestone**: Stage 1B evaluation pilot (conversation ability)
**Budget remaining**: ~$294 of $300
