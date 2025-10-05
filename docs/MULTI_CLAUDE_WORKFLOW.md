# Multi-Claude Workflow: Local Planning + Remote Execution

**Date Created**: 2025-10-04
**Status**: ⏳ Experimental (Active Test)
**Purpose**: Document novel workflow using two Claude instances for ML research

---

## Overview

This experiment uses **two Claude Code instances** in a distributed architecture:

1. **Local Claude** (this instance) - Planning, design, code review, documentation
2. **Pod Claude** (GPU pod instance) - Execution, data generation, training

This separates the cognitive/planning work from the computational/execution work.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Local Machine                          │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │  Local Claude (Planning & Development)             │    │
│  │  - Design scripts and utilities                    │    │
│  │  - Write documentation                             │    │
│  │  - Review code and results                         │    │
│  │  - Create tasks and roadmaps                       │    │
│  │  - Commit to git                                   │    │
│  └────────────────────────────────────────────────────┘    │
│                          │                                   │
│                          │ git push/pull                     │
│                          ▼                                   │
└──────────────────────────────────────────────────────────────┘
                           │
                           │ SSH (22069)
                           │ Git sync
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    RunPod H100 Pod                          │
│                 (root@63.141.33.75)                         │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │  Pod Claude (Execution & Monitoring)               │    │
│  │  - Run data generation scripts                     │    │
│  │  - Monitor GPU utilization                         │    │
│  │  - Execute training runs                           │    │
│  │  - Run evaluations                                 │    │
│  │  - Report results and progress                     │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
│  Hardware: H100 SXM 80GB, 80GB VRAM                         │
│  Cost: $2.69/hr                                             │
│  Storage: /workspace (persistent volume)                    │
└─────────────────────────────────────────────────────────────┘
```

---

## Roles and Responsibilities

### Local Claude (Planning Agent)

**Environment**: MacBook (no GPU)
**Context**: Full project history, documentation, codebase
**Primary Functions**:
- Design and write scripts
- Create utilities (eval_statistics, provenance_helper, etc.)
- Write tests and documentation
- Review experiment results
- Update roadmaps and registries
- Commit code to git
- Create tasks and priorities

**Key Characteristics**:
- Has access to entire conversation history
- Can read and update all documentation
- Can review past decisions and context
- No GPU access (can't run models)
- Long-running sessions (hours/days)

### Pod Claude (Execution Agent)

**Environment**: RunPod H100 GPU pod
**Context**: Session-specific, experiment-focused
**Primary Functions**:
- Execute data generation scripts
- Run training jobs
- Monitor GPU utilization
- Execute evaluations
- Report progress and results
- Handle errors and retries

**Key Characteristics**:
- Fresh context per session (lightweight)
- GPU access (can run models)
- Focused on execution, not design
- Short-running sessions (minutes/hours per task)
- **Critical instruction**: "You are on the pod to run experiments, not code. Wait for explicit instructions before executing anything - don't start work proactively."

---

## Communication Protocol

### Pod Claude Initialization

**IMPORTANT**: Set up network volume FIRST (see `/docs/NETWORK_VOLUME_SETUP.md`)

**One-time setup on first pod**:
```bash
# Create 100GB network volume in RunPod dashboard
# Launch pod with volume attached (name: maximalcai-experiment)

cd /workspace/maximalcai-experiment
curl -O https://raw.githubusercontent.com/abstractionlair/cai-constitution-bootstrap/main/scripts/setup_network_volume.sh
chmod +x setup_network_volume.sh
./setup_network_volume.sh

# Follow prompts to configure credentials
source activate_pod.sh
```

**Every new pod** (after termination):
```bash
cd /workspace/maximalcai-experiment
source activate_pod.sh  # 30 seconds, everything persists!
```

**First message to Pod Claude** (critical to set expectations):

```
You are on the pod to run experiments, not code.

Your role:
- Execute scripts and commands I provide
- Monitor and report results
- Report errors and issues

Important: Wait for my explicit instructions before executing anything.
Don't start work proactively or suggest next steps without being asked.

Ready when you are.
```

This prevents Pod Claude from:
- Proactively running scripts without being asked
- Trying to write/modify code (that's Local Claude's job)
- Making assumptions about what to do next

### Handoff Pattern

**Local → Pod** (via git):
1. Local Claude designs script/task
2. Local Claude commits to git
3. User: `git pull` on pod
4. User instructs Pod Claude with explicit task

**Pod → Local** (via user):
1. Pod Claude executes and reports results
2. User copies results/logs to local machine
3. User shares with Local Claude for analysis
4. Local Claude reviews and plans next steps

### Information Flow

```
Local Claude designs → Git commit → Pod pulls → Pod Claude executes
                                                        │
                                                        ▼
Local Claude analyzes ← User shares ← Pod Claude reports
```

---

## First Test Case: Sample Data Generation

**Date**: 2025-10-04
**Task**: Generate 50 training examples with provenance metadata
**Cost**: ~$1-2 (~15-30 min on H100)

### Setup Phase

**Local Claude** (completed):
- ✅ Created `generate_sample_data.py` script
- ✅ Added provenance tracking integration
- ✅ Updated roadmap with checkpoint
- ✅ Committed to git
- ✅ Documented in IMPLEMENTATION_REGISTRY

**User** (completed):
- ✅ SSH'd to pod: `ssh root@63.141.33.75 -p 22069 -i ~/.ssh/id_ed25519`
- ✅ Pulled latest code: `cd /workspace/MaximalCAI && git pull`
- ✅ Launched Claude Code on pod
- ✅ Informed Pod Claude of its role: "You are on the pod to run experiments, not code. Wait for my explicit instructions before executing anything."

### Execution Phase

**User instruction to Pod Claude**:
```
Please run the following sequence:

1. Create session manifest to capture environment:
   python3 scripts/create_session_manifest.py

2. Generate sample training data (50 examples for inspection):
   python3 scripts/generate_sample_data.py --count 50

3. After generation completes, show me:
   - The output file path
   - First 3 examples (full JSON)
   - A summary of the metadata from one example
   - Any warnings or issues encountered
```

**Pod Claude** (blocked - pod environment broken):
- ❌ Session manifest creation hung (torch import failed)
- ❌ Pod environment had broken torch installation
- ❌ Pod terminated, need new pod with working environment

**Expected Output**:
- `artifacts/session_manifest_<timestamp>.json`
- `artifacts/sample_sft_data_<timestamp>.jsonl` (50 examples)
- Console logs with generation progress
- Sample examples for quality inspection

### Analysis Phase (pending)

**User** (planned):
- Download sample data: `scp -P 22069 -i ~/.ssh/id_ed25519 root@63.141.33.75:/workspace/MaximalCAI/artifacts/sample_*.jsonl ./`
- Share with Local Claude for review

**Local Claude** (planned):
- Review sample quality
- Check metadata completeness
- Verify no contamination
- Approve or request changes
- Plan next steps (full generation or iterate)

---

## Advantages of This Workflow

### Separation of Concerns
- **Planning** (complex, needs context) done locally with full history
- **Execution** (GPU-intensive, simple) done on pod with fresh context
- Each Claude optimized for its task

### Cost Efficiency
- Local Claude: Free (runs on local machine)
- Pod Claude: Only active during GPU work
- No idle GPU time while planning/designing

### Context Management
- Local Claude maintains long-term project context
- Pod Claude has lightweight, task-specific context
- Avoids context contamination between planning and execution

### Fault Tolerance
- If pod crashes, context loss is minimal (just current task)
- Local Claude maintains all design decisions and history
- Can resume with new pod instance easily

### Scalability
- Can run multiple Pod Claudes in parallel (if needed)
- Local Claude coordinates across all pods
- Clear handoff boundaries

---

## Challenges and Mitigations

### Challenge 1: Context Synchronization
**Issue**: Pod Claude doesn't have full project history
**Mitigation**:
- User provides explicit, self-contained instructions
- Scripts are well-documented with docstrings
- Session manifest captures environment context

### Challenge 2: Communication Latency
**Issue**: Results must be manually transferred between Claudes
**Mitigation**:
- Batch work to minimize round-trips
- Pod Claude provides comprehensive reports
- Use git for code, scp for artifacts

### Challenge 3: Role Confusion and Proactiveness
**Issue**: Pod Claude might try to design/code instead of execute, or start work without being asked
**Mitigation**:
- Explicit instruction: "You are on the pod to run experiments, not code. Wait for explicit instructions - don't start work proactively."
- Task-focused instructions (not open-ended)
- Local Claude handles all design/coding
- User provides clear "do X" instructions, not "what should I do?"

### Challenge 4: Pod Environment Reliability
**Issue**: First H100 pod had broken torch installation causing hangs
**Root Cause**: Pod environment had misconfigured/broken torch (file descriptor/memory exhaustion on import)
**Impact**: Pod became unresponsive, had to be terminated, ~$0.45 lost
**Mitigation**:
- Always smoke test torch import BEFORE running any scripts
- Test commands documented in `KNOWN_BUGS_AND_FIXES.md`
- Don't skip setup script verification (it catches this)
- Be prepared to try different pods/templates if torch doesn't work
**Lesson**: Expensive pod ≠ working environment, verify basics first
**See**: `KNOWN_BUGS_AND_FIXES.md` - "RunPod Environment - Torch Import Hangs"

---

## Comparison to Alternatives

### Single Claude on Pod
**Pros**: Simple, one context
**Cons**: Expensive (pay for GPU during planning), context gets huge, hard to review locally

### Single Claude Locally (SSH Execution)
**Pros**: One Claude, full context
**Cons**: PTY allocation issues (documented in previous sessions), less interactive feedback

### This Approach (Two Claudes)
**Pros**:
- Best of both worlds
- Cost-efficient
- Clear separation of concerns
- Fault-tolerant
**Cons**:
- Manual coordination
- Context must be passed explicitly
- Novel (untested at scale)

---

## Success Metrics

We'll consider this workflow successful if:

1. ✅ Pod Claude can execute tasks with clear instructions
2. ✅ Results can be reviewed by Local Claude
3. ✅ Cost is lower than alternatives (no idle GPU time)
4. ✅ Quality of output matches expectations
5. ✅ Workflow scales to full training pipeline

**Current Status**: Test 1 in progress (sample data generation)

---

## Future Experiments

If this workflow succeeds, we can:

1. **Parallelize**: Multiple Pod Claudes for different experiments
2. **Automate**: Create handoff scripts for common patterns
3. **Extend**: Add monitoring Claude, review Claude, etc.
4. **Document**: Write up as methodology for ML research workflows

---

## Related Documents

- `docs/RUNPOD_H100_SESSION.md` - Pod connection and setup
- `docs/claude_code_interoperability.md` - Previous SSH automation attempts
- `scripts/sync_claude.sh` - Sync infrastructure (from previous sessions)
- `ROADMAP.md` - Project plan and milestones

---

## Timeline

- **2025-10-04 15:00** - Local Claude created sample generation script
- **2025-10-04 19:30** - User set up pod, pulled latest code
- **2025-10-04 19:45** - Pod Claude launched and instructed
- **2025-10-04 19:50** - Pod Claude execution blocked: session manifest script hung
- **2025-10-04 20:00** - Local Claude diagnosed: pod has broken torch installation
- **2025-10-04 20:10** - Pod terminated (environment unfixable, ~$0.45 cost)
- **2025-10-04 20:15** - Documented environment issue and smoke test procedure
- **Next**: User starts new pod, smoke tests torch, resumes workflow

---

## Notes

This is an **experimental workflow**. We're documenting it in real-time as we discover what works and what doesn't.

**Key Insight**: The separation between "planning" and "execution" maps well onto the separation between "CPU/context work" and "GPU work" in ML research.

**Open Question**: Can this scale to more complex multi-step experiments? (e.g., train → evaluate → analyze → retrain)

**To Be Determined**: Optimal instruction format for Pod Claude to minimize ambiguity

---

**Status**: ⏳ Active experiment, documenting as we go
