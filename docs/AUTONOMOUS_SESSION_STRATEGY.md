# Autonomous Session Strategy

**Context**: For long autonomous runs on pod without human intervention.

**Challenge**: Context compaction will happen automatically but at unpredictable times. I can't trigger it myself.

**Solution**: Structure work to create natural checkpoints where compaction is safe.

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

## Summary

**Key insight**: Since I can't control compaction timing, I need to make **every phase boundary a safe compaction point**.

**Strategy**:
1. Write checkpoints to files frequently
2. Make each phase self-contained (load from files, not memory)
3. Use incremental progress tracking
4. Prefer streaming to files over accumulating in memory

**Result**: Compaction can happen anytime without disrupting work. I always know where I am by reading checkpoint files.

**This makes autonomous work practical** even without manual compaction control.
