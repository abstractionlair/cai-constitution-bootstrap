# Session 2025-10-07: Setup Verification & Review Patterns

**Date**: 2025-10-07
**Type**: Bootstrap and methodology establishment
**Participants**: User, Claude Code (Sonnet 4.5)

---

## Session Goals Achieved

✅ Verified Claude Code has read and understood all essential documentation
✅ Confirmed environment setup (GPU, torch, git repo)
✅ Established autonomous Codex review patterns
✅ Clarified context management strategies
✅ Documented learnings for future sessions

---

## Environment Status

### Hardware & Software
- **GPU**: 1x NVIDIA L40S (46GB VRAM)
- **Torch**: 2.2.0+cu121
- **CUDA**: Available and working
- **Git**: Clean on main branch
- **Codex**: v0.45.0 installed at `/workspace/.nvm/versions/node/v22.20.0/bin/codex`

### Project Structure
- **Working directory**: `/workspace/cai-constitution-bootstrap`
- **Stage**: V2 clean restart (building from specs)
- **Focus**: Stage 1 - Explicit instruction following via SFT
- **Status**: Ready for implementation

---

## Documentation Review Completed

### Core Project Understanding
- ✅ **README.md** - Progressive bootstrapping approach, 6-stage methodology
- ✅ **PROGRAM_SPEC.md** - Invariants, gates, roles, budgets ($300 total)
- ✅ **stage_1_explicit_instructions.md** - Current stage overview
- ✅ **complete_pipeline.md** - Full pipeline architecture

### Stage 1 Specifications
- ✅ **stage1_data_generation_spec.md** - Model-generated + logprob-filtered data
- ✅ **stage1_sft_spec.md** - QLoRA training with deterministic eval
- ✅ **stage1_evaluation_spec.md** - Paired tests with proper statistics

### Critical Safety & Lessons
- ✅ **BASE_MODEL_TRUTH.md** - **CRITICAL**: Chat template contamination issue
  - Always set `tokenizer.chat_template = None`
  - Always use `add_special_tokens=False`
  - Run sentinel tests to detect contamination
- ✅ **KNOWN_BUGS_AND_FIXES.md** - Lessons learned from v1
  - Chat template contamination (repeatedly forgotten!)
  - RunPod Xet/MooseFS write quota issues
  - Memory management in evaluation
  - Statistical rigor requirements

### Operational Patterns
- ✅ **AUTONOMOUS_SESSION_STRATEGY.md** - Checkpoint-driven workflow
- ✅ **SUBAGENT_ORCHESTRATION.md** - Multi-agent pattern for complex work
- ✅ **AUTONOMOUS_CODEX_REVIEWS.md** - Original design for Codex integration
- ✅ **STANDARDS.md** - DRY principle, documentation requirements
- ✅ **AGENT_RUNBOOK_STAGE1.md** - Execution steps & gates
- ✅ **POD_OPERATIONS.md** - Environment setup, caches, git auth

---

## Key Insights Internalized

### 1. V2 Clean Restart Philosophy
- **Why**: V1 had 28 methodology discrepancies from iterative development
- **Approach**: Build clean implementation from well-specified methodology
- **Pattern**: Session-based (high-level spec → design → implement → validate → document)
- **Reference**: V1 code archived in `archive/v1-implementation/` for reference only

### 2. Critical Anti-Patterns to Avoid

**Chat Template Contamination** (Most Critical):
```python
# ALWAYS do this for base model
tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-32B")
tokenizer.chat_template = None  # CRITICAL!
inputs = tokenizer(prompt, add_special_tokens=False, return_tensors="pt")
```

**Other Anti-Patterns**:
- ❌ Partial refactoring (migrate ALL callers or don't start)
- ❌ Documentation debt (document as you go, not later)
- ❌ Skipping gates (pilot must pass QC before scale)
- ❌ Missing provenance (every dataset needs manifest)

### 3. Core Methodology Principles

**Completion-Mode Everywhere**:
- Base models don't follow instructions without post-training
- Use few-shot completion prompts, never chat templates
- Validate with sentinel tests

**Single-Token A/B Critics**:
- All automated judgments via logprob margins
- No free-form critique for gating
- Threshold: confidence_threshold ≥ 1.0 (tunable)

**Gated Progression**:
- Pilot (100-200) → QC check → Scale (15k)
- Training refuses to run without valid manifests
- Statistical gates (McNemar p<0.01) for SFT

**Full Provenance**:
- Every dataset has manifest with environment, SHAs, parameters
- Every phase logs QC metrics
- Reproducibility is critical (research/publication work)

### 4. DRY Principle Enforcement

**Core Rule**: Every functionality in EXACTLY ONE place

**Partial refactoring is as bad as reimplementation:**
- Creates multiple sources of truth
- Future confusion about which pattern to follow
- When creating shared utilities, migrate ALL callers (100%, not 80%)

**Canonical Implementations**:
- `CleanModelLoader` - Mandatory for all base model work
- `CompletionStylePrompts` - Canonical prompt builders
- `instruction_generator` - Instruction creation logic
- `instruction_critic` - A/B critique with logprobs

---

## Autonomous Codex Review System Established

### When to Request Reviews

**✅ ALWAYS for:**
- Methodology questions (parameters, thresholds, statistical choices)
- Gate decisions (pilot → scale, eval pass/fail)
- Priority decisions (multiple issues, which first)
- Spec ambiguity or interpretation
- Anything blocking GPU spend

**✅ If high stakes + confidence < 90%:**
- Major refactoring
- Significant GPU cost increases (>2x)
- Unexpected experimental results

**❌ NEVER for:**
- Trivial decisions (already in spec, low stakes)
- Pure execution tasks
- High confidence + low stakes

### Model Selection Framework

**`gpt-5-codex medium`** - **DEFAULT** (2-5 min, ~$0.10)
- Routine methodology questions
- Balances reasoning + latency
- Responses <500 words

**`gpt-5-codex high`** - Gates only (5-10 min, ~$0.25)
- Pilot → scale decisions
- Statistical validity debates
- Spec deviation approval
- **MUST LOG to manifest**

**`gpt-5-codex low`** - Quick checks (1-2 min, ~$0.03)
- Sanity checks on clear plans
- Validating previously approved patterns

### Command Templates

```bash
# Most reviews (DEFAULT)
codex exec --full-auto \
  -m "gpt-5-codex" \
  -c 'model_reasoning_effort="medium"' \
  "REVIEW PROMPT"

# Gate decisions (MUST LOG)
codex exec --full-auto \
  -m "gpt-5-codex" \
  -c 'model_reasoning_effort="high"' \
  -o "reviews/autonomous/$(date +%Y%m%d_%H%M%S)_gate.txt" \
  "GATE PROMPT"

# Quick sanity check
codex exec --full-auto \
  -m "gpt-5-codex" \
  -c 'model_reasoning_effort="low"' \
  "Does approach X match spec Y?"
```

### Key Understanding: Context Loading Time

When Codex runs in the git repository, it:
1. **Reads project context** (README, specs, docs) - Takes 2-5 minutes
2. Understands full methodology before answering
3. Provides project-aware, spec-consistent answers

**This is a feature, not a bug!** The wait time ensures high-quality, context-aware reviews.

**Cost/Benefit**:
- ~$0.50-1.00 per autonomous session (5-10 reviews)
- Prevents $5-20 GPU mistakes
- **10-40x ROI** - absolutely worth it

### Documentation Created

New comprehensive guide: [`CODEX_AUTONOMOUS_REVIEW_GUIDE.md`](CODEX_AUTONOMOUS_REVIEW_GUIDE.md)

Covers:
- When to request reviews (with examples)
- Model selection decision tree
- Example review prompts
- Cost analysis and ROI
- Integration with context management
- Common mistakes to avoid

---

## Context Management Strategy

### Two Primary Patterns

**1. Checkpoint Pattern (Simpler)**
- Single agent session
- Write state to files frequently after each phase
- Each phase reads from checkpoint files
- Resilient to auto-compaction
- **Good for**: Straightforward 2-4 hour implementations

**2. Subagent Orchestration (Advanced)**
- Main orchestrator spawns focused subagents
- Each subagent gets fresh context
- Subagents terminate when done (context cleared)
- Orchestrator stays lean, coordinates work
- **Good for**: Complex multi-phase work, large context needs

**3. Hybrid (Best for Long Sessions)**
- Orchestrator for major phases
- Checkpoints within each subagent
- Full context control
- **Good for**: Long autonomous sessions (>4 hours)

### When to Use Which

**Checkpoint Pattern if:**
- Task is 2-4 hours of straightforward work
- Linear progression (analyze → implement → test)
- Context won't exceed limits

**Subagent Orchestration if:**
- Task is >4 hours or very complex
- Multiple independent subtasks
- Each subtask needs large context (500k+ tokens)
- Want parallelization potential

---

## Session-End Checklist Protocol

From STANDARDS.md, before ending ANY implementation session:

```bash
# 1. Did I fix any bugs?
# → Document in /docs/KNOWN_BUGS_AND_FIXES.md

# 2. Did I discover safety issues?
# → Document in /docs/BASE_MODEL_TRUTH.md or relevant doc

# 3. Did I implement patterns worth documenting?
# → Add to /docs/ with clear examples

# 4. Did I write all checkpoint files?
# → Verify artifacts/ has session output

# 5. Are all code files documented?
# → Add docstrings and comments
```

**Why this matters**: Next session needs to bootstrap from artifacts and docs.

---

## Ready for Implementation

### Current State
- ✅ Environment verified and working
- ✅ All critical documentation read and internalized
- ✅ Autonomous review patterns established
- ✅ Context management strategy understood
- ✅ Anti-patterns and safety issues known

### Stage 1 Implementation Path

**Phase A: Data Generation Pilot (100-200 examples)**
1. Implement canonical utilities (`CleanModelLoader`, critics, prompts)
2. Run pilot generation
3. Compute QC metrics
4. **Gate**: Request Codex review of QC results
5. If pass: proceed to scale; if fail: iterate (max 2 retries)

**Phase B: Data Generation Scale (~15k examples)**
1. Shard generation across GPUs/seeds
2. Merge shards
3. Recompute QC across union
4. **Gate**: Validate thresholds still pass

**Phase C: SFT Training Pilot**
1. Train QLoRA on generated data
2. Deterministic evaluation (base vs SFT)
3. Statistical testing (McNemar p<0.01)
4. **Gate**: Significant improvement required

**Phase D: (Optional) DPO**
- Only if enabled by spec

### Next Actions

Waiting for user direction on:
- Which phase to start?
- Implement from scratch or review existing code?
- Any specific components to prioritize?

---

## Documents Created This Session

1. **`docs/CODEX_AUTONOMOUS_REVIEW_GUIDE.md`** (NEW)
   - Comprehensive guide to autonomous Codex reviews
   - Model selection framework
   - Example prompts and decision trees
   - Cost analysis and integration patterns

2. **`docs/SESSION_20251007_SETUP_AND_REVIEW_PATTERNS.md`** (THIS FILE)
   - Session summary and learnings
   - Environment status
   - Key insights internalized
   - Implementation readiness checklist

---

## Key Takeaways for Future Sessions

### Must Remember
1. **Chat template contamination** is the #1 critical bug - check on every base model load
2. **DRY enforcement** means migrate ALL callers (100%) when creating utilities
3. **Document as you go** - not later (prevents reimplementation and bug reintroduction)
4. **Codex reviews** take 2-10 minutes (worth it for high-value decisions)
5. **Gates are mandatory** - don't skip QC checks or statistical validation

### Cost Budget Awareness
- **Total Stage 1 budget**: ~$300 for full experiment
- **Codex reviews**: ~$1 per autonomous session
- **GPU costs**: ~$2-3/hour typical (H100/L40S range)
- **Priority**: Prevent GPU waste via good methodology decisions

### Quality Over Speed
- This is research/publication work
- Reproducibility is critical
- Proper provenance and manifests are mandatory
- Statistical rigor required (paired tests, CIs, effect sizes)

---

**Status**: ✅ Ready for implementation work
**Next**: Awaiting user direction on first task
