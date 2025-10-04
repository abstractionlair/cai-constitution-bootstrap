# Agent Startup Checklist

**Purpose**: Quick reference for all agents (Claude Code, Gemini, Codex) at session start

**NOTE**: This document is now supplemented by `/docs/STANDARDS.md` which contains comprehensive standards. This checklist remains for quick reference.

---

## Every Session: Read These First

### 1. Project Goals
**`README.md`**
- Understand project vision and goals
- Navigation hub to all resources

### 2. Current Milestones
**`ROADMAP.md`**
- Milestone checklist (✅/⏳/📋)
- High-level progress tracking

### 3. How We Work
**`/docs/STANDARDS.md`**
- Comprehensive standards (files, code, docs, reviews, assignments, git)
- **READ THIS ONCE** early in project

### 4. Current Context
**`/status/PROJECT_STATUS.md`**
- Current focus and blockers
- Recent changes and context

### 5. Check Your Work Queue
**Both locations** (assignments are flexible):
```bash
# Implementation tasks
grep -l "Assigned To: {your_name}" tasks/claude_code/pending/*.md

# Review requests
grep -l "Assigned Reviewers.*{your_name}" reviews/requests/*.md
```

---

## Universal Queue Check (All Agents)

**Every agent must check BOTH queues**:

```bash
# Find implementation tasks assigned to you
grep -l "Assigned To: {your_agent_name}" tasks/claude_code/pending/*.md

# Find review requests assigned to you
grep -l "Assigned Reviewers.*{your_agent_name}" reviews/requests/*.md
```

**Why both?** Assignments are flexible - any agent can be assigned any work.

**Default roles**:
- claude_code: Implementation (primary)
- gemini, codex: Reviews (primary)

But check both queues for atypical assignments.

## Role-Specific Quick Start

### Claude Code (Implementation)
**See**: `CLAUDE.md` for full instructions

**Queue check**:
```bash
grep -l "Assigned To: claude_code" tasks/claude_code/pending/*.md
grep -l "Assigned Reviewers.*claude_code" reviews/requests/*.md
```

**Before coding**: Check IMPLEMENTATION_REGISTRY, KNOWN_BUGS_AND_FIXES, BASE_MODEL_TRUTH

### Gemini (Technical Review)
**See**: `GEMINI.md` for full instructions

**Queue check**:
```bash
grep -l "Assigned Reviewers.*gemini" reviews/requests/*.md
grep -l "Assigned To: gemini" tasks/claude_code/pending/*.md
```

**Review focus**: Technical correctness, memory, performance, code quality

### Codex (Methodology Review)
**See**: `codex.md` for full instructions

**Queue check**:
```bash
grep -l "Assigned Reviewers.*codex" reviews/requests/*.md
grep -l "Assigned To: codex" tasks/claude_code/pending/*.md
```

**Review focus**: Methodology, statistics, experimental design, publication quality

---

## Critical Documents (Never Skip)

### BASE_MODEL_TRUTH.md 🚨
**Read this before ANY base model work**
- Chat template contamination bug
- We've rediscovered this multiple times
- Contains sentinel tests to detect contamination
- CRITICAL for evaluation validity

### IMPLEMENTATION_REGISTRY.md 📋
**Check FIRST before implementing**
- Prevents re-implementing existing features
- Prevents reproducing old bugs
- Saves time by finding existing solutions

### KNOWN_BUGS_AND_FIXES.md 🐛
**Check when debugging or reviewing**
- Complete bug history
- How bugs were fixed
- Regression prevention
- Searchable by symptom

---

## Quick File Locations

```
Project Root
├── /status/              ← Current state (living docs)
│   ├── PROJECT_STATUS.md      (SINGLE SOURCE OF TRUTH)
│   ├── RUNPOD_STATUS.md       (Infrastructure)
│   └── REVIEW_STATUS.md       (Recent feedback)
│
├── /docs/                ← Permanent reference
│   ├── IMPLEMENTATION_REGISTRY.md  (What exists)
│   ├── KNOWN_BUGS_AND_FIXES.md    (Bug history)
│   ├── BASE_MODEL_TRUTH.md        (Chat template issue)
│   ├── FILE_ORGANIZATION_STANDARDS.md
│   └── [other permanent docs]
│
├── /tasks/claude_code/   ← Work tracking
│   ├── pending/           (14 tasks to do)
│   ├── in_progress/       (Currently working)
│   ├── completed/         (Done)
│   └── obsolete/          (No longer relevant)
│
├── /reviews/             ← Review system
│   ├── gemini/pending/    (Gemini review requests)
│   ├── codex/pending/     (Codex review requests)
│   └── */responses/       (Completed reviews)
│
├── /archive/             ← Historical (read-only)
│   ├── status/            (Old status snapshots)
│   ├── reviews/           (Past review cycles)
│   └── [other historical]
│
├── /scripts/             ← Implementation (40+ files)
│   ├── stage1_*.py        (Stage-specific)
│   ├── utils/             (Shared utilities)
│   └── [other scripts]
│
└── /specs/               ← Design specifications
    ├── stage_1_explicit_instructions.md
    └── [other specs]
```

---

## Common Scenarios

### "I need to implement X"
1. Check IMPLEMENTATION_REGISTRY.md - does X exist?
2. If yes: Use existing implementation, don't rewrite
3. If no: Check specs/ for requirements, then implement
4. After implementing: Update IMPLEMENTATION_REGISTRY.md

### "I found a bug"
1. Check KNOWN_BUGS_AND_FIXES.md - is this known?
2. If yes: Use documented fix
3. If no: Fix bug, then document in KNOWN_BUGS_AND_FIXES.md
4. Prevents future re-discovery

### "Where do I put this file?"
1. Check FILE_ORGANIZATION_STANDARDS.md
2. Status info → `/status/`
3. Permanent docs → `/docs/`
4. Historical → `/archive/`
5. Specs → `/specs/`
6. Code → `/scripts/`
7. Tasks → `/tasks/claude_code/pending/`

### "What's the current state?"
1. Read `/status/PROJECT_STATUS.md` (SINGLE SOURCE OF TRUTH)
2. Check date at top (is this current?)
3. See "Next Steps" section
4. Check `/tasks/claude_code/pending/` for work queue

---

## Anti-Patterns to Avoid

❌ **Don't**: Implement without checking IMPLEMENTATION_REGISTRY.md
✅ **Do**: Search registry first, reuse existing code

❌ **Don't**: Fix a bug without checking KNOWN_BUGS_AND_FIXES.md
✅ **Do**: Check if this bug was fixed before, use documented solution

❌ **Don't**: Read multiple status docs to find current state
✅ **Do**: Read `/status/PROJECT_STATUS.md` (single source of truth)

❌ **Don't**: Create files in root directory
✅ **Do**: Use appropriate subdirectory per FILE_ORGANIZATION_STANDARDS.md

❌ **Don't**: Assume base model follows instructions well
✅ **Do**: Read BASE_MODEL_TRUTH.md, check for chat template contamination

---

## Session Start Template

```
1. Read /status/PROJECT_STATUS.md - What's the current state?
2. Check /tasks/claude_code/pending/ - What needs doing? (if Claude Code)
3. Check /reviews/[agent]/pending/ - Any review requests? (if Gemini/Codex)
4. Review IMPLEMENTATION_REGISTRY.md - What already exists?
5. Scan KNOWN_BUGS_AND_FIXES.md - What should I watch for?
6. Begin work
```

---

**Remember**: These documents exist to prevent re-implementation and bug reproduction. Use them!
