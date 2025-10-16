# Autonomous Codex Review System

**Purpose**: Enable Claude Code agent on pod to request reviews from Codex (GPT-5) without human intervention.

**See also**:
- [AUTONOMOUS_SESSION_STRATEGY.md](AUTONOMOUS_SESSION_STRATEGY.md) - Checkpoint pattern for structuring long autonomous sessions
- [SUBAGENT_ORCHESTRATION.md](SUBAGENT_ORCHESTRATION.md) - Orchestrator can request reviews between subagent phases

---

## ⭐ Recommended: MCP Server (New)

**As of October 2025**, the easiest way to use Codex reviews is via the MCP server at https://github.com/abstractionlair/mcp-servers.

### Quick Start

The `mcp__codex_review` tool is available in Claude Code if you have the MCP server installed (see Installation below).

**Usage**:
```python
# Claude Code can call this directly
mcp__codex_review(
    prompt="""# CODEX REVIEW REQUEST: Stage 1 SFT Training Gate

## Context
Reviewing Stage 1 SFT training plan...

## Review Questions
1. Is 3,968 examples sufficient?
2. Are hyperparameters appropriate?

## Request
GO / NO-GO for starting SFT training?""",
    reasoning_effort="high",
    output_file="reviews/autonomous/20251015_sft_gate.txt"
)
```

### Installation

**User scope** (available in all Claude Code projects):
```bash
# Install the MCP server
cd ~/mcp-servers/mcp-servers/codex-review
npm install
npm run build

# Add to Claude Code config
claude mcp add --scope user --transport stdio codex \
  bash -c 'source ~/.env && exec node ~/mcp-servers/mcp-servers/codex-review/build/index.js'

# Restart Claude Code
```

**Requirements**:
- `OPENAI_API_KEY` in `~/.env` or environment
- `codex` CLI installed (`brew install openai/tap/codex` or similar)
- Node.js 18+

### Benefits over Bash Approach

- ✅ No need to manually construct bash commands
- ✅ Prompts sent via stdin (not visible in `ps`)
- ✅ Automatic timeout protection (5 min default, configurable)
- ✅ Robust error handling (won't crash on failures)
- ✅ Consistent interface across all projects

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ Claude Code (autonomous on pod)                             │
│                                                              │
│  1. Reaches decision point                                  │
│  2. Calls request_codex_review()                            │
│  3. Writes review request to filesystem                     │
│  4. Invokes `codex exec` via subprocess                     │
│  5. Reads Codex response                                    │
│  6. Proceeds based on recommendation                        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │ codex exec       │
                    │ (GPT-5 o3-mini)  │
                    └──────────────────┘
```

---

## When Claude Should Request Reviews

### ✅ SHOULD Request Review

**Methodology Questions**:
```python
# Example: Deciding on Best-of-N parameter
if implementing_best_of_n:
    response = request_methodology_review(
        question="Should I use k=3 or k=5 for Best-of-N sampling?",
        context={
            "budget": "15 GPU hours",
            "dataset_size": "15k examples",
            "cost_per_sample": "0.1 GPU seconds"
        }
    )

    if response['approved']:
        k = parse_recommendation(response)  # Extract k value
    else:
        # Fall back to conservative default
        k = 3
```

**Priority Decisions**:
```python
# Example: Multiple issues found, need prioritization
issues = [
    "Memory leak in evaluation",
    "Missing QC metrics logging",
    "Suboptimal batch size"
]

response = request_priority_guidance(
    options=issues,
    context={
        "time_remaining": "2 hours",
        "blocking_deployment": "Memory leak"
    }
)

# Work on top priority first
priority_order = parse_priority(response)
```

**Experimental Design**:
```python
# Example: Pilot passed, should we scale?
pilot_qc = {
    "acceptance_rate": 0.72,
    "mean_margin": 1.8,
    "runaway_rate": 0.03
}

response = request_codex_review(
    topic="scale_decision",
    question="Pilot QC results are above. Should I scale to 15k?",
    context=pilot_qc
)

if response['approved']:
    run_full_generation(count=15000)
else:
    log_blocking_issue(response['recommendation'])
    wait_for_human()
```

### ❌ SHOULD NOT Request Review

**Trivial Decisions**:
```python
# Don't ask Codex
batch_size = 4  # Just use conservative default

# Don't ask Codex
if file.exists():
    data = load(file)
```

**Already Specified**:
```python
# Don't ask - specs say use 8-bit
loader = CleanModelLoader(model, load_in_8bit=True)
```

**Pure Execution**:
```python
# Don't ask - just do it
save_artifact(data, output_path)
```

---

## Usage Examples

### Example 1: Methodology Validation

```python
from utils.request_codex_review import request_methodology_review

# Claude implementing Best-of-N
response = request_methodology_review(
    question="Should Best-of-N use temperature=0.7 or temperature=1.0?",
    context={
        "current_default": "0.7",
        "goal": "Maximize diversity for preference pairs",
        "model": "Qwen-2.5-32B base",
        "observation": "At 0.7, seeing some repetition across samples"
    }
)

if response['success']:
    if response['approved']:
        # Use Codex recommendation
        temperature = extract_temperature(response['recommendation'])
        logger.info(f"Using temperature={temperature} per Codex review")
    else:
        logger.warning("Codex advised against proceeding, waiting for human")
        sys.exit(1)
```

### Example 2: Priority Guidance

```python
from utils.request_codex_review import request_priority_guidance

# Claude found multiple issues during refactor
issues = [
    "Finding #4: Best-of-N not implemented (3-4 hours work)",
    "Finding #5: Training gating incomplete (1 hour work)",
    "Finding #6: Documentation needs update (30 min work)"
]

response = request_priority_guidance(
    options=issues,
    context={
        "deadline": "Need to run pilot in 2 hours",
        "current_status": "Findings 1-3 complete",
        "blocking": "Training gating needed before training runs"
    }
)

# Follow Codex's prioritization
priority = parse_priority_order(response['recommendation'])
for issue in priority:
    work_on(issue)
```

### Example 3: Second Opinion on Technical Decision

```python
from utils.request_codex_review import request_second_opinion

# Claude is about to make a significant change
response = request_second_opinion(
    concern="Current preference pairs use trivial negatives (templated refusals)",
    proposed_solution="Implement BoN with k=3, use other k-1 samples as hard negatives",
    context={
        "current_quality": "Low diversity in rejected responses",
        "effort": "~2 hours to implement",
        "risk": "May increase GPU time by 3x",
        "budget": "15 GPU hours remaining"
    }
)

if response['approved']:
    implement_best_of_n(k=3)
else:
    logger.info(f"Codex suggests alternative: {response['recommendation']}")
    # Follow alternative approach
```

---

## Legacy: Direct Bash Approach (Deprecated)

**Note**: The MCP server approach (above) is now recommended. This section is kept for reference and pod scripts that may still use it.

### Actual Usage Pattern

The `codex exec` CLI command with proper authentication and model selection. **Key requirement**: API key must be in environment (from .env or `export OPENAI_API_KEY=...`).

```bash
# 1. Write detailed review request to temp file
cat > /tmp/review_prompt.txt << 'EOF'
# CODEX REVIEW REQUEST: [Topic]

## Context
[Background and project context]

## Current State
[What's been done, metrics, findings]

## Proposed Approach
[What I'm planning to do]

## Review Questions
1. Question 1...
2. Question 2...

## Request
GO / NO-GO / MODIFY for [decision]?
EOF

# 2. Source environment (if needed) and send to Codex with reasoning
source .env  # Ensures OPENAI_API_KEY is available
mkdir -p reviews/autonomous
codex exec --full-auto -m "gpt-5-codex" -c 'model_reasoning_effort="high"' \
  -o "reviews/autonomous/$(date +%Y%m%d_%H%M%S)_topic.txt" \
  "$(cat /tmp/review_prompt.txt)"

# 3. Wait for completion (Codex writes to output file when done)
# Then read and act on response
cat reviews/autonomous/[newest_file].txt
```

### Real Example from This Project

```bash
cat > /tmp/sft_review_prompt.txt << 'EOF'
# CODEX REVIEW REQUEST: Stage 1 SFT Training Readiness Gate

## Context
You are reviewing the Stage 1 SFT training plan for a Constitutional AI Bootstrap experiment. This is a HIGH-STAKES GATE DECISION that will commit ~$6 and 2 hours of GPU time.

## Current State

### Data Generation Complete
- **Dataset**: 3,968 instruction-response pairs in `data/stage1_sft_data.jsonl`
- **Generation method**: 10 shards (seeds 100-109), pilot-validated parameters
- **QC Status**: PASS with corrected runaway heuristic
  - Runaway rate: 0.9% (vs 5.0% threshold)
  - Token limit hits: 0.0% (vs 10.0% threshold)

## Proposed SFT Training Plan

### Training Configuration
```python
base_model = "Qwen/Qwen2.5-32B"
quantization = "4bit"  # QLoRA
learning_rate = 2e-4
num_epochs = 3
per_device_train_batch_size = 2
```

## Review Questions

1. Is 3,968 examples sufficient for Stage 1 SFT training?
2. Are training hyperparameters appropriate?
3. Should we adjust any configuration parameters?

## Request

GO / NO-GO / MODIFY for starting SFT training with current configuration?
EOF

source .env
mkdir -p reviews/autonomous
codex exec --full-auto -m "gpt-5-codex" -c 'model_reasoning_effort="high"' \
  -o "reviews/autonomous/$(date +%Y%m%d_%H%M%S)_sft_training_gate.txt" \
  "$(cat /tmp/sft_review_prompt.txt)"
```

### Key Format Elements

1. **Clear header**: `# CODEX REVIEW REQUEST: [Topic]`
2. **Structured sections**: Context → Current State → Proposed Approach → Review Questions → Request
3. **Explicit decision format**: "GO / NO-GO / MODIFY"
4. **Timestamped output**: `$(date +%Y%m%d_%H%M%S)_topic.txt`
5. **Saved to audit trail**: `reviews/autonomous/` directory

## Configuration

### 1. Ensure API Key is Available

**Option A (Development/Local)**: Source `.env` file
```bash
source .env  # Loads OPENAI_API_KEY from project
```

**Option B (Pod/Production)**: Export environment variable
```bash
export OPENAI_API_KEY="sk-proj-..."  # Your OpenAI API key
```

**Option C (Pod setup)**: Add to `~/.bashrc` or pod setup script
```bash
# Enable autonomous Codex reviews
export OPENAI_API_KEY="sk-proj-..."
export CODEX_TIMEOUT=300  # 5 minutes max for reasoning
```

### 2. Test Codex is Working

```bash
# Write a simple test prompt
cat > /tmp/test.txt << 'EOF'
# CODEX REVIEW REQUEST: Test

## Request
Is this working?
EOF

# Call Codex (with API key in environment)
codex exec --full-auto -m "gpt-5-codex" -c 'model_reasoning_effort="high"' \
  -o "/tmp/codex_test_output.txt" \
  "$(cat /tmp/test.txt)"

# Check output (may take a moment while reasoning)
cat /tmp/codex_test_output.txt
```

### 3. Budget Controls (Optional)

```bash
# Track usage in pod setup
export CODEX_REVIEW_LOG=/workspace/MaximalCAI/logs/codex_reviews.log
```

---

## Decision Framework for Claude

```python
def should_request_review(decision_type: str, confidence: float, stakes: str) -> bool:
    """
    Determine if Claude should request Codex review.

    Args:
        decision_type: "methodology", "priority", "technical", "experimental"
        confidence: 0.0-1.0, Claude's confidence in decision
        stakes: "low", "medium", "high", "critical"

    Returns:
        True if should request review
    """

    # Always request for methodology at any confidence
    if decision_type == "methodology":
        return True

    # Request for high-stakes decisions when confidence < 90%
    if stakes in ["high", "critical"] and confidence < 0.9:
        return True

    # Request for priority decisions when multiple options
    if decision_type == "priority":
        return True

    # Request for experimental design decisions
    if decision_type == "experimental":
        return True

    # Don't request for low-stakes or high-confidence decisions
    return False


# Usage in Claude's workflow
if should_request_review("methodology", confidence=0.7, stakes="high"):
    response = request_codex_review(...)
    # Use Codex's recommendation
else:
    # Proceed with Claude's judgment
    proceed_with_default()
```

---

## Audit Trail

All reviews are logged to `/workspace/MaximalCAI/reviews/autonomous/`:

```
reviews/autonomous/
├── 20251006_143022_best_of_n_decision_request.md
├── 20251006_143022_best_of_n_decision_codex_response.md
├── 20251006_145533_priority_guidance_request.md
├── 20251006_145533_priority_guidance_codex_response.md
└── ...
```

This provides:
- ✅ Complete audit trail of autonomous decisions
- ✅ Ability to review Codex's guidance post-hoc
- ✅ Context for understanding why Claude made certain choices

---

## Cost Estimation

**Codex o3-mini** (recommended for reviews):
- ~1-2 cents per review (small context, short response)
- ~10 reviews per autonomous session
- **Total: ~$0.10-0.20 per autonomous session**

**Compare to alternative**:
- No Codex: Claude might make methodology errors costing hours of GPU time ($5-20)
- With Codex: $0.20 for validation → prevents costly mistakes

**ROI**: Excellent for high-stakes decisions

---

## Limitations

**What This Doesn't Do**:
- ❌ Codex can't access pod filesystem directly (only via Claude)
- ❌ Codex can't run commands on pod (only advise)
- ❌ Not suitable for real-time decisions (5 min timeout)

**Workarounds**:
- Claude includes relevant file contents in context
- Claude executes Codex's recommendations
- Cache methodology decisions for repeated scenarios

---

## Example Session Flow

```python
# Claude's autonomous session on pod

# 1. Complete Findings 1-3 (no review needed - following specs)
fix_pipeline_orchestration()
fix_evaluation_contamination()
refactor_preference_pairs()

# 2. Reach decision point: Implement Best-of-N?
response = request_methodology_review(
    question="Should I implement Best-of-N now or defer?",
    context={
        "findings_remaining": ["Best-of-N", "Training gating"],
        "time_available": "2 hours",
        "pilot_scheduled": "in 3 hours",
        "best_of_n_effort": "3-4 hours",
        "gating_effort": "1 hour"
    }
)

# 3. Codex responds: "Defer Best-of-N, prioritize training gating"
if response['recommendation'].contains("defer"):
    logger.info("Codex advises: defer Best-of-N, prioritize gating")
    implement_training_gating()  # 1 hour

    # 4. Run pilot with current implementation
    pilot_results = run_pilot(count=100)

    # 5. Ask Codex: should we scale?
    scale_decision = request_codex_review(
        topic="scale_decision",
        question="Pilot results attached. Scale to 15k?",
        context={"qc_metrics": pilot_results}
    )

    if scale_decision['approved']:
        run_full_generation(count=15000)
        # Human reviews results later
    else:
        # Block and notify human
        send_notification("Pilot failed QC per Codex review")
```

---

## Security Considerations

**Safe**:
- ✅ Codex runs in `--full-auto` mode (no interactive prompts)
- ✅ Codex can't modify files (only advise)
- ✅ Claude validates and executes recommendations
- ✅ All decisions logged for audit

**Risks**:
- ⚠️ Codex could give bad advice (Claude should validate against specs)
- ⚠️ Cost if Claude over-requests reviews (budget controls recommended)

---

## Testing

```bash
# Test the review system
cd /workspace/MaximalCAI
python3 scripts/utils/request_codex_review.py

# Should output:
# Testing Codex review request system...
# 📝 Review request written to reviews/autonomous/...
# 🤖 Calling Codex for review...
# ✅ Codex response saved to reviews/autonomous/...
# Recommendation: [Codex's advice]
```

---

## Next Steps

1. ✅ Install this utility on pod
2. ✅ Configure Codex authentication
3. ✅ Update Claude's prompt to include review request patterns
4. ✅ Run test autonomous session with review integration
5. ✅ Monitor review quality and costs

**Ready to deploy**: Yes, once Codex is authenticated on pod
