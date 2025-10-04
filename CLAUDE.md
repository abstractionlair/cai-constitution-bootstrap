# Instructions for Claude Code

Welcome to the Constitutional AI Bootstrap experiment! You are the primary implementation partner for this project.

---

## Your Role

**Primary implementer** for this automated Constitutional AI training pipeline.

You write code, execute training on RunPod, transfer results, and iterate through milestones progressively.

---

## Essential Reading (In Order)

**Start every session by reading these**:

1. **[README.md](README.md)** - Project goals and vision
2. **[ROADMAP.md](ROADMAP.md)** - Current milestones and progress
3. **[/docs/STANDARDS.md](/docs/STANDARDS.md)** - How we work (files, code, reviews, git)
4. **[/status/PROJECT_STATUS.md](/status/PROJECT_STATUS.md)** - Current context and focus

---

## Your Work Queue

**Check BOTH queues at every session start**:

### Implementation Tasks (your primary role)

**Location**: `/tasks/claude_code/pending/`

**Find your tasks**:
```bash
grep -l "Assigned To: claude_code" tasks/claude_code/pending/*.md
```

**Expected**: Most implementation tasks will be assigned to you.

**Process**: Priority order (P0 → P1 → P2 → P3)

### Review Requests (occasional)

**Location**: `/reviews/requests/`

**Find your reviews**:
```bash
grep -l "Assigned Reviewers.*claude_code" reviews/requests/*.md
```

**Expected**: Rare (self-review requests, sanity checks)

### Why Check Both?

Assignments are flexible. While implementation is your primary role, you may occasionally be assigned review work for self-checks or quick validations.

---

## Critical Anti-Patterns (Must Read!)

### Before Implementing Anything

1. ✅ **Check IMPLEMENTATION_REGISTRY** first
   - Location: `/docs/IMPLEMENTATION_REGISTRY.md`
   - Prevents re-implementing existing features
   - 40+ scripts already exist - don't duplicate!

2. ✅ **Check KNOWN_BUGS_AND_FIXES** before debugging
   - Location: `/docs/KNOWN_BUGS_AND_FIXES.md`
   - Prevents reproducing old bugs
   - We've fixed many bugs - don't repeat them!

3. ✅ **Read BASE_MODEL_TRUTH** before base model work
   - Location: `/docs/BASE_MODEL_TRUTH.md`
   - Critical: Chat template contamination issue
   - Contains sentinel tests to detect contamination

### After Implementing

1. ✅ Update IMPLEMENTATION_REGISTRY with what you built
2. ✅ Document any bugs fixed in KNOWN_BUGS_AND_FIXES
3. ✅ Add docstrings and comments to code

---

## Claude Code-Specific Operations

### Task Management

**Lifecycle**: `pending/` → `in_progress/` → `completed/` or `obsolete/`

**When starting a task**:
```bash
mv tasks/claude_code/pending/TASK.md tasks/claude_code/in_progress/
```

**When completing**:
1. Add completion notes to task file
2. Move to completed:
```bash
mv tasks/claude_code/in_progress/TASK.md tasks/claude_code/completed/
```

### RunPod Deployment

See `/status/RUNPOD_STATUS.md` for:
- SSH access (direct SSH, not stable proxy!)
- File transfer (use SSH pipes, not scp)
- Pod management
- Cost tracking

**Quick reference**:
```bash
export RUNPOD_PORT=48550  # Update after pod restart!
ssh -p $RUNPOD_PORT -i ~/.ssh/id_ed25519 root@195.26.233.96
```

### Git Workflow

See `/docs/STANDARDS.md#git-workflow` for complete details.

**Key rules**:
- NEVER commit without user request
- NEVER skip hooks (--no-verify)
- NEVER force push to main
- ALWAYS include co-authorship attribution

---

## Quick Reference Commands

### Find your work
```bash
# Tasks assigned to you
grep -l "Assigned To: claude_code" tasks/claude_code/pending/*.md

# Reviews assigned to you (rare)
grep -l "Assigned Reviewers.*claude_code" reviews/requests/*.md
```

### Check what exists
```bash
# See what's implemented
cat docs/IMPLEMENTATION_REGISTRY.md

# See known bugs
cat docs/KNOWN_BUGS_AND_FIXES.md

# Check current focus
cat status/PROJECT_STATUS.md
```

### Create review request
```bash
# Add to reviews/requests/YYYYMMDD_topic.md
# Must include: Assigned Reviewers field
```

See `/reviews/README.md` for review request template.

---

## Key Constraints

- **Hardware**: RunPod A100 SXM 80GB GPU
- **Model**: Qwen-2.5-32B base model
- **Framework**: Unsloth for efficient training
- **Budget**: ~$1.74/hour - be efficient
- **Quantization**: 4-bit for training, 8-bit/16-bit for inference

---

## Progressive Bootstrapping Strategy

**This is NOT just testing** - each stage builds a functional model!

### Current: Stage 1 - Explicit Instruction Following
- Generate explicit instructions
- Train until 95%+ instruction following
- Output: Model that reliably follows explicit instructions
- This model helps generate data for Stage 2

See `ROADMAP.md` and `/specs/stage_1_explicit_instructions.md` for details.

**Future stages** build progressively on Stage 1 output.

---

## Remember

- Maximum automation with minimal human intervention
- Reproducibility is critical (set seeds, log versions, save configs)
- Document progress and decisions
- This is research/publication work, not production
- Flag issues that might affect experiment validity

---

**Questions?** See `/docs/STANDARDS.md` for comprehensive standards or ask the user.
