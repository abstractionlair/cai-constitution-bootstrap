# Codex Autonomous Review Guide

**Purpose**: Guide for Claude Code to autonomously request Codex (GPT-5) reviews during pod sessions.

**Last Updated**: 2025-10-07

**Related Docs**:
- [AUTONOMOUS_SESSION_STRATEGY.md](AUTONOMOUS_SESSION_STRATEGY.md) - Checkpoint pattern for context management
- [SUBAGENT_ORCHESTRATION.md](SUBAGENT_ORCHESTRATION.md) - Advanced multi-agent pattern
- [AUTONOMOUS_CODEX_REVIEWS.md](AUTONOMOUS_CODEX_REVIEWS.md) - Original design doc (v1)

---

## Quick Reference

### When to Request Codex Review

**✅ ALWAYS request for:**
- Methodology questions (parameters, thresholds, statistical choices)
- Gate decisions (pilot → scale, eval pass/fail)
- Priority decisions (multiple issues, which first)
- Spec ambiguity or interpretation questions
- Anything blocking GPU spend

**✅ Request if high stakes + confidence < 90%:**
- Major refactoring affecting multiple components
- Significant GPU cost increases (>2x)
- Unexpected experimental results requiring interpretation

**❌ NEVER request for:**
- Trivial decisions (batch size, log format)
- Already specified in specs (use what spec says)
- Pure execution (save files, run commands)
- Low stakes or high confidence decisions

### Command Template

```bash
# Most methodology reviews (2-5 min, DEFAULT)
codex exec --full-auto \
  -m "gpt-5-codex" \
  -c 'model_reasoning_effort="medium"' \
  "REVIEW PROMPT"

# Gatekeeper decisions (5-10 min, MUST LOG TO MANIFEST)
codex exec --full-auto \
  -m "gpt-5-codex" \
  -c 'model_reasoning_effort="high"' \
  -o "/workspace/cai-constitution-bootstrap/reviews/autonomous/$(date +%Y%m%d_%H%M%S)_gate.txt" \
  "GATE DECISION PROMPT"

# Quick sanity check (1-2 min)
codex exec --full-auto \
  -m "gpt-5-codex" \
  -c 'model_reasoning_effort="low"' \
  "Quick validation: Does approach X match spec Y?"
```

---

## Model Selection Framework

### gpt-5-codex Family (For Methodology Reviews)

**`gpt-5-codex medium`** - **DEFAULT**
- **Use for**: Most autonomous methodology reviews
- **Time**: 2-5 minutes (reads project context)
- **Best for**: Routine questions, parameter choices, threshold validation
- **Response length**: <500 words (fits review format)
- **Cost**: Low-moderate

**`gpt-5-codex low`** - Quick checks
- **Use for**: Sanity checks when you have a clear plan
- **Time**: 1-2 minutes
- **Best for**: "Does this look right?", validating previously approved patterns
- **Cost**: Low

**`gpt-5-codex high`** - Gatekeeper only
- **Use for**: Gates that block GPU spend (pilot→scale, eval pass/fail, spec deviations)
- **Time**: 5-10 minutes
- **Best for**: High-stakes decisions requiring deep reasoning
- **MUST**: Log request/response to manifest
- **Cost**: Moderate-high

### gpt-5 Family (For Non-Methodology Work)

**Not recommended for methodology reviews.** Use for:
- `minimal`: Code snippets, CLI scaffolding
- `low`: Log summaries, short explanations
- `medium`: Broader context synthesis, runbook drafting
- `high`: Long-form analysis (avoid - slower + pricier)

---

## Decision Tree

```python
def choose_codex_model(decision_type, stakes, have_clear_plan):
    """
    Decision tree for selecting Codex model and reasoning effort.

    Args:
        decision_type: "gate" | "methodology" | "sanity_check" | "priority"
        stakes: "blocks_gpu" | "high" | "medium" | "low"
        have_clear_plan: bool - Do I already have a clear approach?

    Returns:
        (model, reasoning_effort, must_log_to_manifest)
    """

    # Gates that block GPU spend
    if decision_type == "gate" or stakes == "blocks_gpu":
        return ("gpt-5-codex", "high", True)  # MUST LOG

    # Quick validation of existing plan
    elif have_clear_plan and decision_type == "sanity_check":
        return ("gpt-5-codex", "low", False)

    # Default: methodology reviews
    elif decision_type in ["methodology", "priority"]:
        return ("gpt-5-codex", "medium", False)

    # Shouldn't reach here for autonomous reviews
    else:
        raise ValueError(f"Unexpected decision_type: {decision_type}")


# Example usage:
model, reasoning, must_log = choose_codex_model(
    decision_type="gate",
    stakes="blocks_gpu",
    have_clear_plan=False
)
# Returns: ("gpt-5-codex", "high", True)
```

---

## What Happens When You Call Codex

### Behind the Scenes

```bash
codex exec --full-auto \
  -m "gpt-5-codex" \
  -c 'model_reasoning_effort="medium"' \
  "Should I proceed to scale after pilot passed QC?"
```

**Steps:**
1. Codex detects git repository
2. **Reads project context files** (2-5 minutes):
   - README.md, PROGRAM_SPEC.md
   - Stage 1 specs (data gen, SFT, eval)
   - BASE_MODEL_TRUTH.md, KNOWN_BUGS_AND_FIXES.md
   - Other relevant docs
3. Understands full project context
4. Answers your question with project-aware response
5. **Total time: 2-7 minutes** depending on reasoning level

### Why This Is Good

- ✅ **Project-aware answers**: Not generic, understands your methodology
- ✅ **Spec-consistent**: Can validate against actual specs
- ✅ **Worth the wait**: 5 minutes to prevent $20 GPU mistake = excellent ROI

### Why It's Slow

- Reading 10-20 docs takes time
- High reasoning effort adds compute time
- This is a **feature**, not a bug - you want thorough, context-aware reviews

---

## Example Review Prompts

### Example 1: Gate Decision (pilot → scale)

```bash
codex exec --full-auto \
  -m "gpt-5-codex" \
  -c 'model_reasoning_effort="high"' \
  -o "reviews/autonomous/$(date +%Y%m%d_%H%M%S)_scale_decision.txt" \
"You are reviewing a gate decision for Constitutional AI Bootstrap Stage 1.

CONTEXT:
I completed data generation pilot (100 examples) and computed QC metrics.

PILOT RESULTS:
- Instruction acceptance rate: 72%
- Pair acceptance rate: 68%
- Mean logprob margin: 1.8
- Runaway rate (after cleaning): 3%
- Delimiter leakage: 0%
- Contamination sentinels: All passed
- Median response tokens: 35

SPEC THRESHOLDS (from stage1_data_generation_spec.md):
- Runaway after cleaning: <5% ✓
- Token-limit hits: <10% (need to check)
- No delimiter leakage: 0% ✓
- Median tokens: <40 ✓
- Critic acceptance: ≥50% ✓
- Contamination: All pass ✓

QUESTION: Should I proceed to scale to 15k examples?

REQUIRED RESPONSE FORMAT:
Decision: SCALE / ITERATE / INVESTIGATE
Reasoning: 2-3 sentences justifying decision
Concerns: Any risks or conditions to watch during scale
Action Items: What I should do next
"
```

### Example 2: Methodology Question

```bash
codex exec --full-auto \
  -m "gpt-5-codex" \
  -c 'model_reasoning_effort="medium"' \
"You are advising on a methodology decision for Constitutional AI training.

QUESTION: Should I use temperature=0.7 or temperature=1.0 for Best-of-N response sampling?

CONTEXT:
- Goal: Generate diverse responses for DPO preference pairs
- Model: Qwen-2.5-32B base (4-bit)
- k=3 (generating 3 responses per instruction)
- Current observation: At temp=0.7, seeing some repetition across samples
- Concern: Higher temp may reduce quality

SPEC SAYS: Data gen spec suggests temp≈0.3-0.5 for response generation

QUESTION: Should I deviate from spec and use higher temp for BoN?

REQUIRED RESPONSE:
Recommendation: STAY_WITH_SPEC / USE_0.7 / USE_1.0 / OTHER
Reasoning: Brief justification
Risks: Any concerns with recommendation
"
```

### Example 3: Priority Decision

```bash
codex exec --full-auto \
  -m "gpt-5-codex" \
  -c 'model_reasoning_effort="medium"' \
"You are advising on prioritization for Constitutional AI Bootstrap.

SITUATION: I found 3 issues during code review. Limited time before pilot run.

ISSUES:
1. Memory leak in evaluation (HIGH impact, 2 hours to fix)
2. Missing QC metrics logging (MEDIUM impact, 30 min to fix)
3. Suboptimal batch size (LOW impact, 15 min to fix)

CONSTRAINTS:
- Pilot scheduled in 3 hours
- All 3 issues are real, none are critical blockers
- Want to maximize pilot success probability

QUESTION: What priority order should I tackle these?

REQUIRED RESPONSE:
Priority Order: 1, 2, 3 (with brief reasoning for each)
Skip Any?: Yes/No - Should I skip anything given time constraint?
"
```

### Example 4: Sanity Check (Use Low Reasoning)

```bash
codex exec --full-auto \
  -m "gpt-5-codex" \
  -c 'model_reasoning_effort="low"' \
"Quick sanity check:

I'm about to implement CleanModelLoader following the pattern in BASE_MODEL_TRUTH.md.

Approach:
- Set tokenizer.chat_template = None
- Use add_special_tokens=False
- Add sentinel tests for contamination

Does this match the documented pattern?

RESPOND: YES/NO with 1 sentence explanation.
"
```

---

## Cost Analysis

### Per Review Costs (Estimates)

| Reasoning Level | Time | Tokens | Cost | Use Case |
|----------------|------|--------|------|----------|
| **low** | 1-2 min | 2-3k | ~$0.03 | Sanity checks |
| **medium** | 2-5 min | 3-5k | ~$0.05-0.10 | Most reviews |
| **high** | 5-10 min | 5-10k | ~$0.15-0.25 | Gate decisions |

### Session Costs

**Typical autonomous session:**
- 3-5 medium reviews: ~$0.15-0.50
- 1-2 high reviews (gates): ~$0.30-0.50
- **Total per session**: ~$0.50-1.00

**ROI:**
- Prevent 1 GPU mistake: Save $5-20
- **ROI**: 10-40x return on review costs
- **Worth it**: Absolutely yes for high-value decisions

---

## Logging and Audit Trail

### For High-Stakes Decisions (MUST DO)

When using `reasoning_effort="high"` for gate decisions:

```bash
# Save output to file
codex exec --full-auto \
  -m "gpt-5-codex" \
  -c 'model_reasoning_effort="high"' \
  -o "reviews/autonomous/$(date +%Y%m%d_%H%M%S)_gate_decision.txt" \
  "GATE DECISION PROMPT"

# Then reference in manifest
echo "Codex review: reviews/autonomous/TIMESTAMP_gate_decision.txt" >> \
  artifacts/session_manifest.json
```

### For Routine Reviews (Optional but Good Practice)

```bash
# Write request + response to files for audit
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
echo "REVIEW PROMPT" > reviews/autonomous/${TIMESTAMP}_request.txt

codex exec --full-auto \
  -m "gpt-5-codex" \
  -c 'model_reasoning_effort="medium"' \
  -o "reviews/autonomous/${TIMESTAMP}_response.txt" \
  "REVIEW PROMPT"
```

This creates audit trail:
- `reviews/autonomous/TIMESTAMP_request.txt` - What you asked
- `reviews/autonomous/TIMESTAMP_response.txt` - Codex's answer

---

## Integration with Context Management

### With Checkpoint Pattern

```python
# Phase 1: Analysis
analyze_requirements()
write_checkpoint("artifacts/analysis.md")

# Ask Codex before implementing
codex_response = call_codex_review("Should I proceed with approach X?")

if codex_approved(codex_response):
    # Phase 2: Implementation
    read_checkpoint("artifacts/analysis.md")
    implement_solution()
    write_checkpoint("artifacts/implementation.md")
```

### With Subagent Orchestration

```python
# Orchestrator calls Codex between subagent phases
plan = spawn_subagent("analyze")
codex_review = call_codex_review(f"Review this plan: {plan}")

if codex_approved(codex_review):
    result = spawn_subagent("implement", plan)
```

---

## Common Mistakes to Avoid

### ❌ DON'T: Ask Codex Trivial Questions

```bash
# Bad - wasting time and money
codex exec --full-auto -m "gpt-5-codex" \
  "Should I use batch_size=4 or batch_size=8?"
```

Just use a conservative default (batch_size=4).

### ❌ DON'T: Ask When Spec Already Answers

```bash
# Bad - spec says use 8-bit
codex exec --full-auto -m "gpt-5-codex" \
  "Should I load model in 8-bit or 4-bit?"
```

Read the spec first. Use what spec says unless you have reason to deviate.

### ❌ DON'T: Use --skip-git-repo-check for Real Reviews

```bash
# Bad - prevents Codex from reading project context
codex exec --full-auto --skip-git-repo-check \
  "Methodology question here"
```

Let Codex read project files. That's what makes answers valuable.

### ✅ DO: Ask for High-Stakes Decisions

```bash
# Good - gate decision blocking $15 GPU spend
codex exec --full-auto -m "gpt-5-codex" \
  -c 'model_reasoning_effort="high"' \
  "Pilot QC results: [data]. Should I scale to 15k?"
```

Perfect use case. Worth 5-10 minutes and $0.25.

### ✅ DO: Ask When Spec is Ambiguous

```bash
# Good - spec says "reasonable threshold" without specific value
codex exec --full-auto -m "gpt-5-codex" \
  -c 'model_reasoning_effort="medium"' \
  "Spec says 'reasonable acceptance rate'. Is 68% reasonable?"
```

Codex can interpret based on full project context.

---

## Quick Decision Guide

```
┌─────────────────────────────────────────┐
│ Do I need to make a decision?           │
└─────────────┬───────────────────────────┘
              │
              ▼
      ┌───────────────┐
      │ Is it trivial │ YES → Just decide
      │ or in spec?   │       (don't ask Codex)
      └───────┬───────┘
              │ NO
              ▼
      ┌───────────────┐
      │ Does it block │ YES → Use Codex HIGH
      │ GPU spend?    │       (MUST LOG)
      └───────┬───────┘
              │ NO
              ▼
      ┌───────────────┐
      │ Is it about   │ YES → Use Codex MEDIUM
      │ methodology?  │       (default)
      └───────┬───────┘
              │ NO
              ▼
      ┌───────────────┐
      │ Just need     │ YES → Use Codex LOW
      │ sanity check? │       (quick)
      └───────┬───────┘
              │ NO
              ▼
       Don't use Codex
       (probably execution task)
```

---

## Summary

### When to Use Codex

- Gate decisions (pilot→scale)
- Methodology questions
- Priority decisions
- Spec ambiguity
- High stakes + low confidence

### Model Selection

- **Default**: `gpt-5-codex medium` (2-5 min, ~$0.10)
- **Gates**: `gpt-5-codex high` (5-10 min, ~$0.25, MUST LOG)
- **Sanity checks**: `gpt-5-codex low` (1-2 min, ~$0.03)

### Key Points

- ✅ Let Codex read project context (don't use --skip-git-repo-check)
- ✅ Budget 5-10 minutes per review (worth it)
- ✅ Log high-stakes reviews to manifest
- ✅ ~$1 per session for 5-10 reviews
- ✅ 10-40x ROI (prevents GPU mistakes)

### Integration

- Works with checkpoint pattern (between phases)
- Works with subagent orchestration (between subagents)
- Enables true autonomous decision-making

---

**Last Updated**: 2025-10-07
**Next Review**: After first autonomous session with Codex integration
