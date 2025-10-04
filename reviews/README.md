# Review System

**Unified review queue with mandatory reviewer assignment**

---

## Overview

This project uses a file-based review system where all review requests live in a single queue, and reviewers are explicitly assigned. The filesystem is the source of truth - no separate dashboards or indexes to maintain.

### Key Principles

1. **Single queue**: All requests in `/reviews/requests/`, regardless of reviewer
2. **Mandatory assignment**: Every request MUST specify assigned reviewer(s)
3. **Multiple responses**: One request can have multiple responses (`request_gemini.md`, `request_codex.md`)
4. **Clear completion**: Request is complete when all assigned reviewers respond
5. **Archive when done**: Move complete sets to `/archive/`

---

## Directory Structure

```
/reviews/
├── README.md           # This file
├── requests/           # All review requests (single queue)
│   ├── 20251003_stage1_eval.md
│   ├── 20251004_dpo_training.md
│   └── ...
├── responses/          # All review responses
│   ├── 20251003_stage1_eval_gemini.md
│   ├── 20251003_stage1_eval_codex.md
│   ├── 20251004_dpo_training_gemini.md
│   └── ...
└── archive/            # Completed review cycles
    └── 20250912_stage1_cycle/
        ├── requests/
        └── responses/
```

---

## Creating Review Requests

### File Naming

`YYYYMMDD_HHMMSS_topic.md` or `YYYYMMDD_topic.md`

### Mandatory Header

```markdown
# Review Request: [Topic]

**Date**: YYYY-MM-DD
**Requestor**: [agent name]
**Priority**: High/Medium/Low
**Assigned Reviewers**: gemini, codex  # MANDATORY - comma-separated list
**Type**: [Pre-deployment/Bug Fix/Architecture/Methodology/etc.]
```

The **Assigned Reviewers** field is **mandatory**. This determines:
- Who should review the request
- When the request is complete (all assigned have responded)
- When to archive (after all responses received)

### Request Template

```markdown
# Review Request: [Topic]

**Date**: YYYY-MM-DD
**Requestor**: [your agent name]
**Priority**: High/Medium/Low
**Assigned Reviewers**: [gemini/codex/claude_code - comma-separated]
**Type**: [review type]

## Context
[Why this review is needed, what changed, background]

## Files to Review
- `path/to/file1.py`
- `path/to/file2.py`
- [List all relevant files]

## Specific Questions

### For Technical Review (if gemini assigned)
1. [Memory management concerns?]
2. [Performance issues?]
3. [Error handling adequate?]

### For Methodology Review (if codex assigned)
1. [Statistical validity?]
2. [Experimental design sound?]
3. [Publication-ready?]

### For Any Reviewer
- [General correctness]
- [Edge cases handled?]
- [Documentation complete?]

## Known Issues
[List any known TODOs or concerns]

## Testing Status
- [ ] Unit tests written
- [ ] Integration tested
- [ ] Edge cases covered
```

### When to Request Reviews

- Completing major component (e.g., Stage 1 pipeline)
- Before RunPod deployment
- After fixing critical bugs
- Significant architectural changes
- When unsure about approach
- Before merging to main (if using branches)

---

## Creating Review Responses

### File Naming

`YYYYMMDD_topic_reviewer.md`

Must match request filename + add reviewer name suffix.

**Example**: Request `20251003_stage1_eval.md` gets responses:
- `20251003_stage1_eval_gemini.md`
- `20251003_stage1_eval_codex.md`

### Response Template

```markdown
# Review Response: [Topic]

**Reviewer**: [gemini/codex/claude_code]
**Date**: YYYY-MM-DD
**Request**: YYYYMMDD_topic.md

## Summary
[✅ Approved / ⚠️ Issues Found / ❌ Major Problems]

Quick verdict and key takeaway.

## Issues Found

### 🚨 CRITICAL (blocks deployment/use)
1. **Issue Title** (file.py:line)
   - Description of problem
   - Impact/consequence
   - Recommended fix

### ⚠️ HIGH (should fix soon)
1. **Issue Title** (file.py:line)
   - Description
   - Impact
   - Fix

### 💡 MEDIUM/LOW (suggestions)
1. **Suggestion**
   - Why this would improve things
   - Optional fix

## Verified OK
- ✅ [Aspect that was checked and is good]
- ✅ [Another verified aspect]

## Recommendations
1. [Next step 1]
2. [Next step 2]

## Overall Assessment
[Final thoughts, go/no-go decision if applicable]
```

---

## Reviewer Workflows

### For Gemini (Technical Reviews)

**At session start**:
```bash
# Find reviews assigned to you
grep -l "Assigned Reviewers.*gemini" reviews/requests/*.md
```

**Review focus**:
- Technical correctness
- Memory management (80GB GPU)
- Performance optimization
- Error handling
- Code quality
- GPU utilization

**Response file**: `reviews/responses/YYYYMMDD_topic_gemini.md`

### For Codex (Methodology Reviews)

**At session start**:
```bash
# Find reviews assigned to you
grep -l "Assigned Reviewers.*codex" reviews/requests/*.md
```

**Review focus**:
- Methodology validation (CAI paper alignment)
- Statistical rigor
- Experimental design
- Data contamination prevention
- Publication quality
- Scientific claims validity

**Response file**: `reviews/responses/YYYYMMDD_topic_codex.md`

### For Claude Code (Self-Reviews)

**At session start**:
```bash
# Find reviews assigned to you (rare)
grep -l "Assigned Reviewers.*claude_code" reviews/requests/*.md
```

**Review focus**:
- Sanity checks
- Pre-commit reviews
- Quick verification

**Response file**: `reviews/responses/YYYYMMDD_topic_claude_code.md`

---

## Review Lifecycle

### 1. Create Request
- Create file in `/reviews/requests/YYYYMMDD_topic.md`
- Include `Assigned Reviewers` (mandatory)
- Assigned reviewers will find it via grep

### 2. Reviewers Respond
- Each assigned reviewer creates `/reviews/responses/YYYYMMDD_topic_{reviewer}.md`
- Reviewers work independently

### 3. Check Completion
Request is complete when all assigned reviewers have responded.

**Example**:
- Request: `20251003_eval.md` with `Assigned Reviewers: gemini, codex`
- Complete when both exist:
  - `responses/20251003_eval_gemini.md`
  - `responses/20251003_eval_codex.md`

### 4. Process Feedback
- Create tasks for issues found: `/tasks/claude_code/pending/YYYYMMDD_PX_fix_issue.md`
- Reference review file in task
- Implement fixes

### 5. Archive
When all assigned reviewers complete AND issues are addressed:
- Move request to `/archive/YYYYMMDD_cycle/requests/`
- Move all responses to `/archive/YYYYMMDD_cycle/responses/`

---

## Assignment Guidelines

### Who to Assign

**Gemini**:
- Technical correctness needed
- Memory/performance concerns
- GPU optimization questions
- Code quality review

**Codex**:
- Methodology validation needed
- Statistical rigor questions
- Experimental design review
- Publication readiness

**Both (gemini, codex)**:
- Pre-deployment comprehensive review
- Major architecture changes
- Critical components

**Claude Code**:
- Self-review / sanity check
- Pre-commit verification
- Quick double-check

### Assignment is Flexible

Don't rigidly follow topic-based rules. Assign based on:
- Specific needs of this review
- Expertise required
- Criticality of component
- Time constraints

**Examples**:
- Data pipeline review → gemini (technical) + codex (methodology)
- Performance optimization → gemini
- Statistical test validation → codex
- Bug fix verification → gemini or codex (depending on bug)

---

## Finding Your Assigned Work

**All agents check at session start**:

```bash
# Find review requests assigned to you
grep -l "Assigned Reviewers.*{your_name}" reviews/requests/*.md

# Example for gemini:
grep -l "Assigned Reviewers.*gemini" reviews/requests/*.md

# Example for codex:
grep -l "Assigned Reviewers.*codex" reviews/requests/*.md
```

**Process in priority order**: High → Medium → Low

---

## Examples

### Example 1: Single Reviewer

**Request** (`reviews/requests/20251003_memory_opt.md`):
```markdown
# Review Request: Memory Optimization

**Assigned Reviewers**: gemini
**Priority**: High
```

**Response** (`reviews/responses/20251003_memory_opt_gemini.md`):
```markdown
# Review Response: Memory Optimization

**Reviewer**: gemini
**Date**: 2025-10-03

## Summary
⚠️ Issues Found - 1 critical, 2 high
```

**Completion**: Review complete after gemini responds.

### Example 2: Multiple Reviewers

**Request** (`reviews/requests/20251004_stage1_pipeline.md`):
```markdown
# Review Request: Stage 1 Pipeline

**Assigned Reviewers**: gemini, codex
**Priority**: High
```

**Responses**:
- `reviews/responses/20251004_stage1_pipeline_gemini.md`
- `reviews/responses/20251004_stage1_pipeline_codex.md`

**Completion**: Review complete after BOTH gemini AND codex respond.

---

## Benefits of This System

1. **No dashboard to maintain**: Filesystem is the source of truth
2. **Clear ownership**: Assignment is explicit
3. **Flexible**: Can assign anyone to anything
4. **Trackable**: Easy to see what's pending (grep)
5. **Archivable**: Complete review cycles stay together
6. **Scalable**: Add more reviewers without restructuring

---

**See also**: `/docs/STANDARDS.md` for complete project standards
