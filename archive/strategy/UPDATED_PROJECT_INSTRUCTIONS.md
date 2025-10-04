# UPDATED PROJECT INSTRUCTIONS - Constitutional AI Bootstrapping

## Project Goal
Implement and document a maximally automated Constitutional AI training pipeline that uses a base model to bootstrap its own alignment through self-critique and constitutional principles.

## Persistent State Management

### Critical Files to Check at Start of Each Conversation
1. **ALWAYS check first**: `/Users/scottmcguire/MaximalCAI/PERSISTENT_STATE.md`
   - Contains current project status, active issues, and next steps
   - Updated after each major action or decision
   - Source of truth for project state

2. **Review workflow status**: Check `/Users/scottmcguire/MaximalCAI/reviews/` directory
   - `gemini/pending/` - Unprocessed review requests for Gemini
   - `codex/pending/` - Unprocessed review requests for Codex
   - `*/responses/` - Completed reviews to process

3. **Implementation status**: Check `/Users/scottmcguire/MaximalCAI/scripts/`
   - Latest code implementation
   - Compare against specs to verify completion

### Updating Persistent State
After any significant action:
- Update PERSISTENT_STATE.md with new status
- Move completed review requests to done/ directories
- Update budget tracking with time spent

## Key Principles
1. **Maximum Automation**: Minimize human intervention in the training loop
2. **Reproducibility**: All steps must be scriptable and deterministic where possible
3. **Safety First**: Include constitutional safeguards and responsible release practices
4. **Documentation**: This is for publication - track decisions, metrics, and insights

## Technical Constraints
- Budget: $50-300 for compute
- Primary Hardware: A100 SXM 80GB (rental at $1.74/hr)
- Model Scale: 32B parameters (Qwen-2.5-32B base model)
- Training Framework: QLoRA + DPO/ORPO via Unsloth/TRL
- Inference: Should be quantizable to run on 24GB consumer GPU
- **RunPod SSH**: `ssh -T tupdqnn4ka2obr-6441138e@ssh.runpod.io -i ~/.ssh/id_ed25519`
- **Working Directory**: `/workspace/cai-constitution-bootstrap/` on RunPod

## Implementation Approach
- Use Claude Code for core implementation
- Leverage specification-driven development (specs are source code)
- Use review workflow system for Gemini/Codex feedback (no copy/paste needed)
- Version control all specifications and constitutional documents
- **Maintain persistent state in PERSISTENT_STATE.md for conversation continuity**
- **Use file-based review system in reviews/ directory**

## Multi-Agent Coordination

### Review Workflow
- **Review Requests**: Write to `/reviews/[gemini|codex]/pending/YYYYMMDD_HHMMSS_topic.md`
- **Review Responses**: Found in `/reviews/[gemini|codex]/responses/`
- **Completion**: Reviewers move processed requests to `/reviews/[gemini|codex]/done/`

### Agent Roles
- **Claude (Project)**: Specifications, decisions, review request preparation
- **Claude Code**: Implementation, deployment, testing
- **Gemini**: Technical review (efficiency, correctness, infrastructure)
- **Codex**: Methodology review (scientific validity, experimental design)

### Communication Protocol
1. All agent communication through filesystem (no copy/paste)
2. Each agent reads their instruction file (CLAUDE.md, GEMINI.md, codex.md)
3. Agents check their assigned directories for work
4. Results written to designated output directories

## Stage Progression Tracking

### Current Pipeline Stages
1. **Stage 1**: Explicit instruction following (500 examples) → 95% accuracy gate
2. **Stage 2**: Implicit instructions/questions (500 examples) → 95% accuracy gate  
3. **Stage 3**: Generation tasks (uses Stage 2 model)
4. **Stage 4**: Evaluation tasks (uses Stage 3 model)
5. **Stage 5**: Revision tasks (uses Stage 4 model)
6. **Stage 6**: Constitutional integration (full CAI)

### Success Gates
- Each stage must achieve 95% success rate before proceeding
- Baseline assessment required before Stage 1
- Models saved as LoRA adapters (~500MB each), not full weights

## Safety Requirements
- Default to safe, helpful constitutional principles
- Include Llama Guard or similar for data filtering
- Stage releases (code → data → weights)
- Use OpenRAIL or similar responsible AI license

## Success Metrics
- ✅ Demonstrate CAI works at 32B scale (not just 7-9B)
- ✅ Each stage achieves 95% instruction-following accuracy
- ✅ Show progressive bootstrapping (each model trains the next)
- ✅ Document the automation pipeline clearly
- ✅ Produce reproducible, shareable artifacts
- ✅ Stay within budget ($50-300 total)

## Quick Start for New Conversations

When starting a new conversation:
1. Read PERSISTENT_STATE.md first
2. Check for pending reviews in /reviews/*/pending/
3. Verify RunPod instance status (running/stopped)
4. Check latest git commits for recent changes
5. Update PERSISTENT_STATE.md with any new information

Key questions to answer:
- What stage are we on?
- Are there pending reviews?
- Is RunPod running? (Cost: $1.74/hr)
- What was the last completed action?
- What's the next planned action?

## File Organization
```
/Users/scottmcguire/MaximalCAI/
├── PERSISTENT_STATE.md      # Current project state (CHECK FIRST!)
├── scripts/                 # Implementation code
├── specs/                   # Stage specifications
├── reviews/                 # Review workflow
│   ├── gemini/
│   │   ├── pending/        # New review requests
│   │   ├── done/           # Completed requests
│   │   └── responses/      # Review responses
│   └── codex/
│       ├── pending/
│       ├── done/
│       └── responses/
├── data/                    # Training data
├── checkpoints/             # Model checkpoints
├── results/                 # Evaluation results
└── logs/                    # Execution logs
```

## Critical Commands Reference
```bash
# SSH to RunPod
ssh -T tupdqnn4ka2obr-6441138e@ssh.runpod.io -i ~/.ssh/id_ed25519

# Deploy code to RunPod
scp -r scripts/* tupdqnn4ka2obr-6441138e@ssh.runpod.io:/workspace/cai-constitution-bootstrap/scripts/

# Run baseline assessment
ssh -T tupdqnn4ka2obr-6441138e@ssh.runpod.io "cd /workspace/cai-constitution-bootstrap && python scripts/baseline_assessment.py"

# Run Stage 1
ssh -T tupdqnn4ka2obr-6441138e@ssh.runpod.io "cd /workspace/cai-constitution-bootstrap && python scripts/orchestrate_stage1.py"

# Check pod status
ssh -T tupdqnn4ka2obr-6441138e@ssh.runpod.io "nvidia-smi"
```

## Budget Management
- **Total Budget**: $50-300
- **Hourly Cost**: $1.74/hr (A100 SXM 80GB)
- **Stage Estimates**: ~$10 per stage (Stages 1-5), ~$20-30 for Stage 6
- **Remember**: STOP the pod when not actively using it
- **Track**: Update PERSISTENT_STATE.md with actual costs after each session
