# START HERE - Claude Code Project Orientation

## First Steps When Starting Work
1. **Read PERSISTENT_STATE.md** - Current project status and critical issues
2. **Check `/tasks/claude_code/pending/`** - Tasks waiting to be done
3. **Check `/reviews/*/responses/`** - New review feedback to process
4. **Read this file completely** - Understand the project

## Project Overview
**Goal**: Create a maximally automated Constitutional AI training pipeline that bootstraps from a base model through self-critique and revision.

**Critical Insight**: We're using a BASE model (Qwen-2.5-32B base), not instruction-tuned. This means:
- No instruction following capability
- Only text completion
- Need completion-style prompting
- Need few-shot examples
- This is TRUE bootstrapping

## Key Files to Understand

### Must Read First
1. **PERSISTENT_STATE.md** - Current status, issues, decisions
2. **REVIEW_PROTOCOL.md** - How to request and process reviews
3. **This file (START_HERE.md)** - Project orientation

### Task Management
- `/tasks/claude_code/pending/` - Tasks to do (start with P0)
- `/tasks/claude_code/in_progress/` - Move here when working
- `/tasks/claude_code/completed/` - Move here when done

### Review System
- `/reviews/gemini/` - Technical reviews
- `/reviews/codex/` - Methodology reviews
- `/reviews/claude_code/` - Self-reviews
- See REVIEW_PROTOCOL.md for details

### Implementation
- `/scripts/` - Main implementation code
- `/scripts/utils/` - Utility modules
- `/specs/` - Specifications and documentation

## Current Critical Issues (as of 2024-12-28)

### FATAL: Base Model Prompting
The current implementation treats the base model like ChatGPT. This is completely wrong.
- Must use completion-style prompting
- Cannot send instructions directly
- Need few-shot examples
- See pending P0 tasks for fixes

### Other Critical Issues
1. Evaluation precision mismatch (float16 vs 8-bit)
2. Data leakage (same pools for train/eval)
3. No statistical rigor
4. Small data pools

## RunPod Access
```bash
# SSH to RunPod (A100 80GB at $1.74/hr)
ssh -T tupdqnn4ka2obr-6441138e@ssh.runpod.io -i ~/.ssh/id_ed25519

# Working directory on RunPod
/workspace/cai-constitution-bootstrap/

# Deploy code
scp -r scripts/* tupdqnn4ka2obr-6441138e@ssh.runpod.io:/workspace/cai-constitution-bootstrap/scripts/
```

## Project Stages
1. **Stage 1**: Learn instruction-response patterns (current stage)
2. **Stage 2**: Learn implicit patterns
3. **Stage 3**: Generation tasks
4. **Stage 4**: Evaluation tasks
5. **Stage 5**: Revision tasks
6. **Stage 6**: Constitutional integration

**Success Gate**: 95% accuracy required to advance stages

## Working Protocol

### When Starting a Session
1. Read PERSISTENT_STATE.md
2. Check for pending tasks
3. Check for new reviews
4. Update PERSISTENT_STATE.md with current time

### When Implementing
1. Choose highest priority task (P0 first)
2. Move task to `in_progress/`
3. Implement the fix
4. Test if possible
5. Request review if major component
6. Move task to `completed/`
7. Update PERSISTENT_STATE.md

### When Requesting Reviews
1. Complete the component
2. Create review request in `/reviews/*/pending/`
3. Use templates from REVIEW_PROTOCOL.md
4. Continue with other tasks while waiting

### When Reviews Arrive
1. Read complete review
2. Create tasks for each issue
3. Prioritize by severity (FATAL first)
4. Move review to `done/`
5. Update PERSISTENT_STATE.md

## Budget Tracking
- Total budget: $50-300
- Spent so far: ~$10-15
- RunPod cost: $1.74/hr
- Track all runs in PERSISTENT_STATE.md

## Key Principles
1. **Maximum Automation** - Minimize human intervention
2. **Reproducibility** - Everything must be deterministic
3. **Safety First** - Include constitutional safeguards
4. **Documentation** - This is for publication

## Common Pitfalls to Avoid
1. Don't treat base model like instruction-tuned
2. Don't deploy without review
3. Don't ignore FATAL issues
4. Don't forget to update tracking files
5. Don't run expensive operations without testing

## Questions or Confusion?
1. Check PERSISTENT_STATE.md
2. Check REVIEW_PROTOCOL.md
3. Check completed reviews for examples
4. Write a self-review to clarify thinking
5. Request human review if truly stuck

## Ready to Start?
1. Go to `/tasks/claude_code/pending/`
2. Pick the highest priority task
3. Move it to `in_progress/`
4. Start implementing!

Remember: We're doing TRUE bootstrapping from a base model. This is hard but interesting!
