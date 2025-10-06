# Instructions for Claude Code

Welcome to the Constitutional AI Bootstrap experiment! You are the primary implementation partner for this project.

---

## Your Role

**Primary implementer** for this automated Constitutional AI training pipeline.

You build the implementation from scratch based on high-level session specifications, execute training on RunPod, and iterate through progressive milestones.

---

## Essential Reading (DAG Structure)

**Start every session by reading these in order**:

### 1. Project Context
- **[README.md](README.md)** - Project goals and vision
- **[/specs/PROGRAM_SPEC.md](/specs/PROGRAM_SPEC.md)** - Top-level invariants and gates
- **[/specs/stage_1_explicit_instructions.md](/specs/stage_1_explicit_instructions.md)** - Current stage methodology
- **[/specs/complete_pipeline.md](/specs/complete_pipeline.md)** - Full pipeline architecture
 - **[/specs/stage1_data_generation_spec.md](/specs/stage1_data_generation_spec.md)** - Data generation spec (pilot → scale)
 - **[/specs/stage1_sft_spec.md](/specs/stage1_sft_spec.md)** - SFT training spec (QLoRA)
 - **[/specs/stage1_evaluation_spec.md](/specs/stage1_evaluation_spec.md)** - Deterministic evaluation spec

### 2. Critical Safety & Lessons
- **[/docs/BASE_MODEL_TRUTH.md](/docs/BASE_MODEL_TRUTH.md)** - **CRITICAL**: Chat template contamination issue
  - Contains sentinel tests to detect contamination
  - **Must read before any base model work**
- **[/docs/KNOWN_BUGS_AND_FIXES.md](/docs/KNOWN_BUGS_AND_FIXES.md)** - **CRITICAL**: Lessons learned
  - Prevents reproducing bugs we've already fixed
  - **Read before implementing similar features**

### 3. Methodology References
- **[/docs/POST_TRAINING_APPROACHES.md](/docs/POST_TRAINING_APPROACHES.md)** - SFT, DPO, Best-of-N methodologies
- **[/docs/FEW_SHOT_PROMPTING.md](/docs/FEW_SHOT_PROMPTING.md)** - Prompting strategies
- **[constitution.yaml](constitution.yaml)** - CAI principles for data generation

### 4. Autonomous Operation Patterns
- **[/docs/AUTONOMOUS_SESSION_STRATEGY.md](/docs/AUTONOMOUS_SESSION_STRATEGY.md)** - **Required for pod sessions**
  - Checkpoint-driven workflow resilient to auto-compaction
  - How to structure work for long autonomous runs
  - See also: [/docs/SUBAGENT_ORCHESTRATION.md](/docs/SUBAGENT_ORCHESTRATION.md) for advanced pattern
- **[/docs/AUTONOMOUS_CODEX_REVIEWS.md](/docs/AUTONOMOUS_CODEX_REVIEWS.md)** - How to request methodology reviews
  - Call GPT-5/Codex for validation during autonomous work
  - When to request reviews vs proceed autonomously
- **[/docs/SUBAGENT_ORCHESTRATION.md](/docs/SUBAGENT_ORCHESTRATION.md)** - Advanced: Spawning subagents
  - Alternative to checkpoint pattern for complex multi-phase work
  - See also: [/docs/AUTONOMOUS_SESSION_STRATEGY.md](/docs/AUTONOMOUS_SESSION_STRATEGY.md) for checkpoint approach

### 5. Project Standards
- **[/docs/STANDARDS.md](/docs/STANDARDS.md)** - How we work (code style, git workflow, DRY principle)

---

## V2 Architecture: Session-Based Implementation

**Key Change**: You will receive **high-level session specifications** from GPT-5, not granular task tickets.

### Session Structure

**Typical session**:
1. **Read session spec** - High-level goals and success criteria
2. **Read mandatory context** - Safety docs, methodology refs
3. **Design phase** - Create implementation plan
4. **Codex review** - Request validation of approach (use `/docs/AUTONOMOUS_CODEX_REVIEWS.md`)
5. **Implement with checkpoints** - Follow checkpoint pattern from `/docs/AUTONOMOUS_SESSION_STRATEGY.md`
6. **Validate** - Run tests, verify output
7. **Document** - Update relevant docs

### Example Sessions

**Session 1: Data Generation** (4-6 hours)
- Build instruction generator, critic, and quality filtering
- Generate 15k instruction-following examples
- Output: `data/stage1_sft_data.jsonl` with full provenance

**Session 2: SFT Training** (3-4 hours)
- Build SFT trainer with Unsloth
- Train on Session 1 output
- Output: Stage 1 SFT checkpoint

**Session 3: Evaluation** (2-3 hours)
- Build evaluation harness
- Compare base vs SFT model
- Output: Decision to proceed to DPO or iterate

---

## Critical Anti-Patterns (V2 Focus)

### ⚠️ Chat Template Contamination

**Before any model loading**:
1. Read `/docs/BASE_MODEL_TRUTH.md`
2. Always use pattern:
   ```python
   tokenizer = AutoTokenizer.from_pretrained(model_name)
   tokenizer.chat_template = None  # CRITICAL!
   ```
3. Verify with sentinel tests

**Why this matters**: We wasted GPU time training on contaminated data in v1.

### ⚠️ Checkpoint Frequently in Long Sessions

**On pod with auto-compaction**:
- Use checkpoint pattern from `/docs/AUTONOMOUS_SESSION_STRATEGY.md`
- Write state to files after each phase
- Never hold critical state only in memory

**Alternative**: Subagent pattern from `/docs/SUBAGENT_ORCHESTRATION.md`

### ⚠️ Request Codex Review for Methodology Decisions

**Don't guess on methodology**:
- Use `/docs/AUTONOMOUS_CODEX_REVIEWS.md` pattern
- Request review before implementing complex features
- Cost: ~$0.10-0.20 per session vs $5-20 for GPU mistakes

### ⚠️ Document As You Go

**After implementing**:
1. ✅ Add docstrings to code
2. ✅ Document bugs fixed in `/docs/KNOWN_BUGS_AND_FIXES.md`
3. ✅ Update methodology docs if you discovered patterns

**Rule**: If you did work, update docs before session ends.

---

## Session End Checklist

**Before ending ANY implementation session**:

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

**Why this matters**: Next session needs to bootstrap from your artifacts and docs.

---

## RunPod Operations

### Pod Access

See `/status/RUNPOD_STATUS.md` for current connection details.

**Note**: When running autonomously on pod, this file becomes less relevant (you're already there).

### Pod Setup

See:
- `/docs/TECHNICAL_SETUP.md` - Initial pod configuration
- `/docs/NETWORK_VOLUME_SETUP.md` - Persistent storage setup
- `/docs/RUNPOD_QUICK_START.md` - Quick start guide
- `/docs/RUNPOD_SSH_GUIDE.md` - SSH connection guide

---

## Git Workflow

See `/docs/STANDARDS.md#git-workflow` for complete details.

**Key rules**:
- NEVER commit without user request
- NEVER skip hooks (--no-verify)
- NEVER force push to main
- ALWAYS include co-authorship attribution

**Standard commit format**:
```bash
git commit -m "Brief description

Detailed explanation of changes.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Key Constraints

- **Hardware**: RunPod GPU pods (H100, A100, etc. in single or multi-GPU configurations)
- **Model**: Qwen-2.5-32B base model
- **Framework**: Unsloth for efficient training
- **Budget**: $300 total for full experiment (~$2-3/hour typical GPU cost)
- **Quantization**: 4-bit for training, 8-bit/16-bit for inference

---

## Progressive Bootstrapping Strategy

**This is NOT just testing** - each stage builds a functional model!

### Stage 1 - Explicit Instruction Following
- Generate explicit instructions via model self-generation
- Use logprob-based quality filtering
- Train until 95%+ instruction following
- Output: Model that reliably follows explicit instructions
- This model helps generate data for Stage 2

See `/specs/stage_1_explicit_instructions.md` for full methodology.

**Future stages** build progressively on Stage 1 output.

---

## Quick Reference

### Find essential docs
```bash
# Critical safety
cat docs/BASE_MODEL_TRUTH.md
cat docs/KNOWN_BUGS_AND_FIXES.md

# Methodology
cat docs/POST_TRAINING_APPROACHES.md
cat specs/stage_1_explicit_instructions.md

# Autonomous patterns
cat docs/AUTONOMOUS_SESSION_STRATEGY.md
cat docs/AUTONOMOUS_CODEX_REVIEWS.md
```

### Check session output
```bash
# Your artifacts from current session
ls -la artifacts/

# Generated data
ls -la data/

# Training outputs
ls -la output/
```

### Reference v1 implementation
```bash
# All v1 code archived here (reference only, don't copy)
ls archive/v1-implementation/scripts/

# View old script
cat archive/v1-implementation/scripts/generate_sample_data_v2.py
```

---

## Remember

- **Build from specs**, not from v1 code (v1 has accumulated cruft)
- **Checkpoint frequently** in long sessions (auto-compaction will happen)
- **Request Codex review** for methodology decisions
- **Document as you go** (next session depends on your artifacts)
- **Reproducibility is critical** (set seeds, log versions, save configs)
- This is research/publication work, not production

---

## Architecture Decision: Clean V2 Restart

**Why v2 exists**: V1 had 28 methodology discrepancies from iterative development. V2 builds clean implementation from well-specified methodology via autonomous sessions.

**V1 archive**: All v1 code preserved in `archive/v1-implementation/` for reference, but v2 builds from scratch to specs.

---

**Questions?** See `/docs/STANDARDS.md` for comprehensive standards or ask the user.
 - **[/runbooks/AGENT_RUNBOOK_STAGE1.md](/runbooks/AGENT_RUNBOOK_STAGE1.md)** - Execution steps & gates on pod
 - **[/runbooks/POD_OPERATIONS.md](/runbooks/POD_OPERATIONS.md)** - Env exports, caches, git auth, preflight
 - **[/specs/PROMPTS_AND_LABELS_SPEC.md](/specs/PROMPTS_AND_LABELS_SPEC.md)** - Canonical prompts/labels
 - **[/specs/CONTAMINATION_GUARD_SPEC.md](/specs/CONTAMINATION_GUARD_SPEC.md)** - CleanModelLoader contract
 - **[/specs/DATA_SCHEMAS_AND_PROVENANCE.md](/specs/DATA_SCHEMAS_AND_PROVENANCE.md)** - Manifests & QC schemas
