# Autonomous Session Strategy

**Context**: For long autonomous runs on pod without human intervention.

**Challenge**: Context compaction will happen automatically but at unpredictable times. I can't trigger it myself.

**Solution**: Structure work to create natural checkpoints where compaction is safe.

**See also**:
- [AUTONOMOUS_CODEX_REVIEWS.md](AUTONOMOUS_CODEX_REVIEWS.md) - Request methodology reviews during autonomous work
- [SUBAGENT_ORCHESTRATION.md](SUBAGENT_ORCHESTRATION.md) - Alternative pattern using subagents for indirect context control

---

## Checkpoint-Driven Workflow

### Phase Structure

Each phase should:
1. Load minimal context needed
2. Do focused work
3. **Write results to file** (checkpoint)
4. Complete and ready for compaction
5. Next phase loads checkpoint file

### Example: Implementing Findings #4 and #5

#### Phase 1: Analysis (Compaction-Safe End Point)

```python
# Load and analyze
read_file("reviews/responses/20251006_methodology_audit_codex.md")
read_file("scripts/generate_preference_pairs_logprob.py")
read_file("scripts/utils/instruction_critic.py")
read_file("docs/POST_TRAINING_APPROACHES.md")

# Analyze Finding #4 requirements
analyze_best_of_n_requirements()

# CHECKPOINT: Write implementation plan
write_file("artifacts/finding4_implementation_plan.md", detailed_plan)

# ← Good time for compaction - phase complete, plan saved
```

#### Phase 2: Implementation (Compaction-Safe End Point)

```python
# Load checkpoint
plan = read_file("artifacts/finding4_implementation_plan.md")

# Load only files being modified
read_file("scripts/generate_preference_pairs_logprob.py")

# Implement according to plan
implement_best_of_n(plan)

# CHECKPOINT: Write what was changed
write_file("artifacts/finding4_implementation_complete.md", """
- Modified: generate_preference_pairs_logprob.py
- Added: k parameter for Best-of-N sampling
- Changes: [detailed list]
- Tests needed: [list]
""")

# ← Good time for compaction - implementation done, notes saved
```

#### Phase 3: Testing (Compaction-Safe End Point)

```python
# Load checkpoint
changes = read_file("artifacts/finding4_implementation_complete.md")

# Run tests
test_best_of_n_implementation()

# CHECKPOINT: Write test results
write_file("artifacts/finding4_test_results.md", results)

# ← Good time for compaction - testing done, results saved
```

---

## Principles for Compaction-Resilient Work

### 1. Checkpoint Frequently

**Before any major context shift**:
```python
# BAD: Hold everything in memory
analyze_all_files()
create_complex_plan()
start_implementing()  # ← Compaction here loses analysis

# GOOD: Checkpoint between phases
analyze_all_files()
write_file("analysis.md", findings)  # ← Checkpoint

plan = read_file("analysis.md")
create_implementation_plan(plan)
write_file("plan.md", plan)  # ← Checkpoint

plan = read_file("plan.md")
implement(plan)  # ← Compaction here is safe
```

### 2. Make Phases Self-Contained

Each phase should be runnable from **just reading checkpoint files**:

```python
# Phase can start fresh after compaction
def implement_finding_4():
    # Load checkpoint, not memory
    plan = read_file("artifacts/finding4_plan.md")
    context = read_file("status/CURRENT_WORK_STATUS.md")

    # Load only needed files
    script = read_file("scripts/generate_preference_pairs_logprob.py")

    # Work
    modified_script = apply_changes(script, plan)

    # Save results
    write_file("scripts/generate_preference_pairs_logprob.py", modified_script)
    write_file("artifacts/finding4_complete.md", summary)
```

### 3. Use Incremental Checkpoints

For long implementations:

```python
# Long task: implement Best-of-N
def implement_best_of_n():
    # Subtask 1
    add_k_parameter()
    write_file("artifacts/finding4_progress.md", "✅ Added k parameter")

    # Subtask 2
    implement_multiple_sampling()
    append_file("artifacts/finding4_progress.md", "✅ Multiple sampling")

    # Subtask 3
    implement_ranking()
    append_file("artifacts/finding4_progress.md", "✅ Ranking logic")

    # Can recover from any checkpoint
```

### 4. Prefer Files Over Memory

```python
# BAD: Complex state in memory
findings = []
for script in all_scripts:
    findings.extend(analyze(script))
create_report(findings)  # ← If compaction happens, lose findings

# GOOD: Stream to file
with open("findings.jsonl", "w") as f:
    for script in all_scripts:
        finding = analyze(script)
        f.write(json.dumps(finding) + "\n")
        # ← Compaction safe - already on disk

# Later: read from file
create_report(read_jsonl("findings.jsonl"))
```

---

## Detecting Suboptimal Compaction

If compaction happens at a bad time, I'll notice:

**Symptoms**:
- Losing track of complex reasoning mid-task
- Needing to re-read files I just read
- Forgetting details of the plan I just made

**Recovery**:
1. Check for checkpoint files in `artifacts/`
2. Re-read most recent checkpoint
3. Check `CURRENT_WORK_STATUS.md` for context
4. Continue from last known good state

**Log it**:
```python
write_file("logs/compaction_recovery.log", f"""
{timestamp}: Compaction happened during {current_task}
Recovery: Loaded checkpoint from {checkpoint_file}
Context recovered: {what_i_reloaded}
""")
```

---

## Checkpoint File Structure

### artifacts/finding{N}_plan.md
```markdown
# Finding #{N} Implementation Plan

**Task**: [Brief description]
**Files to modify**: [List]
**Approach**: [Detailed steps]
**Tests needed**: [List]
**Estimated time**: [Hours]
```

### artifacts/finding{N}_progress.md
```markdown
# Finding #{N} Progress

- ✅ Step 1: [What was done]
- ✅ Step 2: [What was done]
- ⏳ Step 3: [In progress]
- ⏸️ Step 4: [Not started]

**Current status**: [Description]
**Next action**: [What to do next]
```

### artifacts/finding{N}_complete.md
```markdown
# Finding #{N} Complete

**Files modified**:
- scripts/foo.py (lines 123-456)
- scripts/bar.py (lines 78-90)

**Changes**:
1. Added [feature]
2. Refactored [component]
3. Fixed [issue]

**Tests run**: [Results]
**Ready for**: [Next phase]
```

---

## Decision Points That Need Codex

Even with checkpointing, some decisions benefit from Codex review:

### When to Request Codex Review

**Before starting major phase**:
```python
# After analysis, before implementation
response = request_codex_review(
    topic="finding4_approach",
    question="I analyzed Best-of-N requirements. Is this approach sound?",
    context={
        "plan": read_file("artifacts/finding4_plan.md"),
        "concerns": ["GPU cost", "complexity"]
    }
)

if not response['approved']:
    revise_plan(response['recommendation'])
    # Write revised plan
    # ← Safe compaction point
```

**At midpoint checks**:
```python
# Halfway through implementation
response = request_codex_review(
    topic="finding4_midpoint",
    question="I'm halfway through Best-of-N. Should I continue or pivot?",
    context={
        "progress": read_file("artifacts/finding4_progress.md"),
        "concern": "More complex than expected"
    }
)
```

---

## Example: Full Finding #4 Implementation

```python
# PHASE 1: Analysis (30 min)
analyze_finding4_requirements()
write_checkpoint("artifacts/finding4_analysis.md")
# ← Compaction safe

# PHASE 2: Planning (15 min)
plan = create_implementation_plan(
    read_checkpoint("artifacts/finding4_analysis.md")
)
write_checkpoint("artifacts/finding4_plan.md")

# Ask Codex before implementing
codex_review = request_codex_review("Is this plan sound?", plan)
if codex_review['approved']:
    write_checkpoint("artifacts/finding4_plan_approved.md")
# ← Compaction safe

# PHASE 3: Implementation Part 1 (1 hour)
plan = read_checkpoint("artifacts/finding4_plan_approved.md")
implement_k_parameter(plan)
write_checkpoint("artifacts/finding4_progress_1.md")
# ← Compaction safe

# PHASE 4: Implementation Part 2 (1 hour)
implement_sampling(read_checkpoint("artifacts/finding4_progress_1.md"))
write_checkpoint("artifacts/finding4_progress_2.md")
# ← Compaction safe

# PHASE 5: Implementation Part 3 (1 hour)
implement_ranking(read_checkpoint("artifacts/finding4_progress_2.md"))
write_checkpoint("artifacts/finding4_complete.md")
# ← Compaction safe

# PHASE 6: Testing (30 min)
test_results = test_implementation(
    read_checkpoint("artifacts/finding4_complete.md")
)
write_checkpoint("artifacts/finding4_tested.md")
# ← Compaction safe
```

Each phase is independent and can survive compaction.

---

---

## Context Management with Subagents

**Key insight discovered**: The primary benefit of subagents is **keeping implementation details out of main context**, not just parallelization.

### The Context Bloat Problem

When implementing complex tasks directly, my context fills with:
- Source code reads (100s-1000s of lines)
- Implementation details (scripts, debugging)
- Data analysis (inspection, counting, pattern matching)
- Multiple iterations and refinements

**Example from Stage 1 remediation**:
- Task: Fix 5 data quality issues from Codex review
- Direct implementation: ~60k tokens (code reads, script writing, analysis, testing)
- With subagents: Would be ~15k tokens (task specs + summaries only)

### When to Use Subagents for Context Management

**Trigger points** - Use a subagent if task requires:
1. Reading >500 lines of source code
2. Writing >100 lines of new code
3. Multiple rounds of data inspection/analysis
4. Detailed debugging or investigation
5. Complex multi-step implementation

**Rule of thumb**: If you're thinking "this is getting detailed", spawn a subagent.

### Pattern: Keep Main Context Clean

```python
# BAD: Direct implementation (bloats main context)
read_file("scripts/utils/clean_model_loader.py")  # 425 lines → context
analyze_sentinel_logic()  # analysis → context
write_file("scripts/repair_data.py")  # 200 lines → context
test_repair()  # test output → context
# Main context now has 1000+ lines of implementation detail

# GOOD: Subagent handles details
spawn_subagent(
    task="Fix sentinel test tolerance and repair data",
    inputs=["data/stage1_sft_data.jsonl", "codex_review_findings.md"],
    outputs=["data/stage1_sft_data_clean.jsonl", "repair_summary.md"]
)
# Subagent returns: "✅ Fixed. 1,120 clean examples, all sentinels passing."
# Main context: Only the summary (1 line)
```

### Real Example: Stage 1 Remediation

**What I did (direct implementation)**:
```
Main context consumption:
├─ Sentinel investigation: 5k tokens (read CleanModelLoader, test logic)
├─ Repair script implementation: 3k tokens (200 lines of code)
├─ Duplication analysis: 8k tokens (data inspection, frequency counting)
├─ QC recomputation: 2k tokens (script implementation)
├─ Eval set expansion: 5k tokens (generation + filtering)
└─ Documentation: 10k tokens

Total: ~33k tokens on implementation details alone
```

**Better approach (with subagents)**:
```
Main context consumption:
├─ Codex review: 2k tokens
├─ Spawn Subagent A: "Fix data quality" (1k task spec)
├─ Subagent A report: "✅ 1,120 clean examples" (0.5k)
├─ Spawn Subagent B: "Expand eval set" (0.5k task spec)
├─ Subagent B report: "✅ 343 test instructions" (0.3k)
├─ Spawn Subagent C: "Generate shards" (0.5k task spec)
└─ Subagent C status: "🔄 Generating..." (0.2k)

Total: ~5k tokens (6× more efficient)
```

### Context Budget Strategy

**For long autonomous sessions**, allocate context budget:

```
Target: 1M token limit
Budget allocation:
├─ Specs and documentation: 50k tokens (read once, reference)
├─ Orchestration and planning: 50k tokens (main agent work)
├─ User communication: 20k tokens
├─ Subagent summaries: 30k tokens (reports from subagents)
└─ Buffer: 850k tokens (safety margin)

With subagents: Can coordinate 20-30 complex tasks before hitting limits
Without subagents: Hit limits after 3-5 complex tasks
```

### When NOT to Use Subagents

**Subagent overhead isn't worth it for**:
1. Simple file edits (<50 lines)
2. Quick analysis tasks (<10 min)
3. Sequential dependencies where you need immediate feedback
4. Tasks where you need to see the details (learning/debugging)

**Use checkpoints instead** for fast linear workflows.

### Lesson from This Session

**Mistake**: Implemented 5 complex fixes directly without subagents
- Filled context with implementation details
- Still succeeded, but inefficient use of context budget

**Better**: After Codex review identified 5 blockers, spawn 2-3 subagents:
- Subagent A: Data quality fixes (5 hours of detailed work)
- Subagent B: Eval set expansion (1 hour)
- Subagent C: Additional shard generation (2 hours)

**Result**: Main context stays focused on high-level orchestration and gate decisions, with 6× more headroom for additional work.

---

## Summary

**Key insight**: Since I can't control compaction timing, I need to make **every phase boundary a safe compaction point**.

**Two complementary strategies**:

### 1. Checkpoint Pattern (for linear workflows)
- Write checkpoints to files frequently
- Make each phase self-contained (load from files, not memory)
- Use incremental progress tracking
- Prefer streaming to files over accumulating in memory

### 2. Subagent Pattern (for context management)
- Spawn subagents for complex/detailed tasks
- Keep main context focused on orchestration
- Get back summaries, not implementation details
- 5-10× more efficient context usage

**Result**: Compaction can happen anytime without disrupting work. Context budget lasts 5-10× longer.

**This makes autonomous work practical** even without manual compaction control.
