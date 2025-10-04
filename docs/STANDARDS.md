# Project Standards

**Last Updated**: 2025-10-03

Comprehensive standards for the Constitutional AI Bootstrap project. All contributors (human and AI) must follow these conventions.

---

## Table of Contents

1. [File Organization](#file-organization)
2. [Code Standards](#code-standards)
3. [Documentation Standards](#documentation-standards)
4. [Review System](#review-system)
5. [Assignment System](#assignment-system)
6. [Git Workflow](#git-workflow)

---

## File Organization

### Guiding Principles

1. **Single Source of Truth**: One canonical document per topic
2. **Temporal Clarity**: Current state vs. historical archive clearly separated
3. **Discovery Prevention**: Make it easy to find what's already implemented
4. **Deprecation Over Deletion**: Archive old docs, don't delete (preserve history)

### Directory Structure

```
/
├── README.md                      # Project goals + navigation
├── ROADMAP.md                     # Milestone checklist
├── CLAUDE.md, codex.md, GEMINI.md # Agent configurations
├── constitution.yaml              # Core project data
│
├── docs/                          # Permanent documentation
│   ├── STANDARDS.md               # This file
│   ├── IMPLEMENTATION_REGISTRY.md # What's implemented
│   ├── KNOWN_BUGS_AND_FIXES.md    # Bug history
│   ├── BASE_MODEL_TRUTH.md        # Critical: chat template issue
│   └── [other technical docs]
│
├── status/                        # Current state
│   ├── PROJECT_STATUS.md          # Narrative context
│   └── RUNPOD_STATUS.md           # Infrastructure
│
├── tasks/                         # Work tracking
│   └── claude_code/
│       ├── pending/               # Todo
│       ├── in_progress/           # Doing
│       ├── completed/             # Done
│       ├── blocked/               # Waiting
│       └── obsolete/              # No longer relevant
│
├── reviews/                       # Review system
│   ├── README.md                  # System documentation
│   ├── requests/                  # All review requests
│   ├── responses/                 # All review responses
│   └── archive/                   # Completed reviews
│
├── specs/                         # Design specifications
│   ├── sequential_bootstrapping_architecture.md
│   ├── stage_N_*.md
│   └── archive/
│
├── scripts/                       # Implementation (40+ files)
│   ├── stage1_*.py
│   ├── train_*.py
│   ├── evaluate_*.py
│   ├── generate_*.py
│   ├── utils/                     # Shared utilities
│   └── archived/                  # Superseded scripts
│
├── archive/                       # Historical
│   ├── status/                    # Old status snapshots
│   ├── reviews/                   # Past review cycles
│   └── decisions/                 # Past decisions
│
└── data/, artifacts/, checkpoints/, logs/, results/
    # Runtime outputs (mostly .gitignored)
```

### File Lifecycle

**Status Documents**:
- Update continuously (living documents)
- Archive when milestone completes: `archive/status/YYYYMMDD_description.md`
- Location: `/status/`

**Task Files**:
- Naming: `YYYYMMDD_HHMMSS_PX_description.md` (X = 0-3 priority)
- Movement: `pending/ → in_progress/ → completed/` or `obsolete/`
- Add completion notes before moving to `completed/`

**Review Files**:
- Requests: `/reviews/requests/YYYYMMDD_topic.md`
- Responses: `/reviews/responses/YYYYMMDD_topic_reviewer.md`
- Archive when all assigned reviewers complete

**Implementation Code**:
- Naming: `stage{N}_{verb}_{noun}.py` or `{verb}_{noun}.py`
- Document in `IMPLEMENTATION_REGISTRY.md` immediately after creating
- Superseded code → `scripts/archived/`, update registry

### Root Directory Policy

**ONLY allowed in root**:
- `README.md`, `ROADMAP.md`
- `CLAUDE.md`, `codex.md`, `GEMINI.md`, `AGENTS.md` (symlink)
- `constitution.yaml`
- Configuration files: `.gitignore`, `.env*`, `.git*`

**Everything else** goes in subdirectories.

---

## Code Standards

### General Principles

1. **Check before implementing**: Search `IMPLEMENTATION_REGISTRY.md` first
2. **Document immediately**: Update `IMPLEMENTATION_REGISTRY.md` after creating
3. **Fix bugs once**: Document in `KNOWN_BUGS_AND_FIXES.md`
4. **Reproducibility**: Set seeds, log versions, save configs

### Python Style

- Follow PEP 8
- Type hints for function signatures
- Docstrings for all public functions
- Clear variable names (avoid abbreviations)

### Script Structure

```python
#!/usr/bin/env python3
"""
Brief description of what this script does

Key features:
- Feature 1
- Feature 2
"""

import standard_library
import third_party
import local_modules

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Setup paths
BASE_DIR = Path(os.getenv('CAI_BASE_DIR', '/workspace/runs/stage1_20250911_131105/code'))
ARTIFACTS_DIR = BASE_DIR / "artifacts"

# Main implementation
class MyComponent:
    """Docstring explaining purpose"""
    pass

def main():
    """Entry point"""
    pass

if __name__ == "__main__":
    main()
```

### Critical Patterns

**Chat Template Contamination Prevention**:
```python
# ALWAYS do this when loading Qwen base model
tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-32B")
tokenizer.chat_template = None  # Disable chat template
inputs = tokenizer(prompt, add_special_tokens=False, return_tensors="pt")
```

See `BASE_MODEL_TRUTH.md` for full details and sentinel tests.

**Few-Shot Completion Prompting**:
```python
# Use CompletionStylePrompts for base model generation
from utils.data_formatter import CompletionStylePrompts
prompt = CompletionStylePrompts.create_response_generation_prompt(instruction)
```

See `DATA_GENERATION_ARCHITECTURE.md` for architecture details.

### Error Handling

- Always catch specific exceptions
- Log errors with context
- Fail gracefully with clear messages
- Make scripts resumable (save checkpoints)

### Memory Management

- Clear GPU cache between model loads: `torch.cuda.empty_cache()`
- Load models sequentially, not concurrently
- Monitor memory with `nvidia-smi`
- Use 4-bit quantization for training, 8-bit/16-bit for inference

---

## Documentation Standards

### Types of Documentation

**IMPLEMENTATION_REGISTRY.md**:
- Purpose: Catalog of all implemented features
- Update: After creating ANY new script
- Content: File:line references, what it does, when to use

**KNOWN_BUGS_AND_FIXES.md**:
- Purpose: Bug history to prevent regression
- Update: When discovering OR fixing bugs
- Content: Symptom, root cause, fix applied, how to detect

**Technical Docs** (`/docs/*.md`):
- Purpose: Permanent reference material
- Examples: BASE_MODEL_TRUTH, DATA_GENERATION_ARCHITECTURE
- Update: When discovering important patterns or gotchas

**Status Files** (`/status/*.md`):
- Purpose: Current project state
- Update: Frequently (living documents)
- Archive: When milestone completes

### Documentation Checklist

Before considering feature complete:
- [ ] Code has docstrings
- [ ] Script added to IMPLEMENTATION_REGISTRY.md
- [ ] Any bugs fixed documented in KNOWN_BUGS_AND_FIXES.md
- [ ] Critical patterns extracted to technical docs if reusable
- [ ] README references updated if needed

---

## Review System

### Overview

Unified review queue with mandatory reviewer assignment. Filesystem is the source of truth (no separate dashboard).

### Directory Structure

```
/reviews/
├── README.md           # Review system documentation
├── requests/           # All review requests (single queue)
├── responses/          # All review responses
└── archive/            # Completed review cycles
```

### Review Request Format

**File naming**: `YYYYMMDD_HHMMSS_topic.md` or `YYYYMMDD_topic.md`

**Mandatory header**:
```markdown
# Review Request: [Topic]

**Date**: YYYY-MM-DD
**Requestor**: [agent name]
**Priority**: [High/Medium/Low]
**Assigned Reviewers**: gemini, codex  # MANDATORY, comma-separated
**Type**: [Pre-deployment/Bug Fix/Architecture/etc.]

## Context
[Why this review is needed]

## Files to Review
- `path/to/file.py`

## Specific Questions
[What you want reviewed]
```

**Assignment is mandatory**. Must specify which reviewer(s).

### Review Response Format

**File naming**: `YYYYMMDD_topic_reviewer.md` (matches request, adds reviewer name)

**Structure**:
```markdown
# Review Response: [Topic]

**Reviewer**: [gemini/codex/claude_code]
**Date**: YYYY-MM-DD
**Request**: YYYYMMDD_topic.md

## Summary
[✅ Approved / ⚠️ Issues Found / ❌ Major Problems]

## Issues Found

### 🚨 CRITICAL
1. [Issue with location and fix]

### ⚠️ HIGH
[...]

### 💡 SUGGESTIONS
[...]

## Recommendations
[Next steps]
```

### Review Lifecycle

1. **Create request** in `/reviews/requests/` with mandatory `Assigned Reviewers` field
2. **Reviewers respond** by creating `/reviews/responses/YYYYMMDD_topic_{reviewer}.md`
3. **Check completion**: Request complete when all assigned reviewers have responded
4. **Archive**: Move request + all responses to `/archive/YYYYMMDD_cycle/` when complete

### Finding Assigned Reviews

**For reviewers** (check at session start):
```bash
# Gemini
grep -l "Assigned Reviewers.*gemini" reviews/requests/*.md

# Codex
grep -l "Assigned Reviewers.*codex" reviews/requests/*.md

# Claude Code (rare)
grep -l "Assigned Reviewers.*claude_code" reviews/requests/*.md
```

### When to Request Reviews

- Completing major component
- Before RunPod deployment
- After fixing critical issues
- Significant architectural changes
- When unsure about approach

---

## Assignment System

### Core Principles

1. **Every work item must have explicit assignment** (tasks and reviews)
2. **Defaults exist but are flexible** (can deviate for specific needs)
3. **Every agent checks both queues** (tasks + reviews)
4. **No rigid topic-based rules** (assign based on specific situation)

### Default Roles

- **claude_code**: Implementation (primary)
- **gemini**: Reviews (primary)
- **codex**: Reviews (primary)

**BUT**: Any agent can be assigned any work. Assignments are flexible.

### Task Assignment Format

**Mandatory header in all task files**:
```markdown
# [Priority]: [Description]

**Priority**: P0/P1/P2/P3
**Assigned To**: claude_code  # MANDATORY
**Estimated Time**: [time]
**Created**: YYYY-MM-DD

[Task content...]
```

### Finding Assigned Work

**Every agent must check BOTH locations at session start**:

```bash
# Check for implementation tasks assigned to you
grep -l "Assigned To: {your_agent_name}" tasks/claude_code/pending/*.md

# Check for review requests assigned to you
grep -l "Assigned Reviewers.*{your_agent_name}" reviews/requests/*.md
```

**Process in priority order**: P0 → P1 → P2 → P3

### Assignment Examples

**Implementation tasks**:
```markdown
Assigned To: claude_code          # Most implementation
Assigned To: codex                # Statistical analysis code
Assigned To: gemini               # Performance optimization code
Assigned To: claude_code, gemini  # Collaborative implementation (rare)
```

**Review requests**:
```markdown
Assigned Reviewers: gemini              # Technical review
Assigned Reviewers: codex               # Methodology review
Assigned Reviewers: gemini, codex       # Comprehensive review
Assigned Reviewers: claude_code         # Self-review (rare)
```

### Assignment Guidelines (NOT Rules)

These are suggestions, not rigid requirements:

- **Gemini** often good for: Technical correctness, memory, performance, GPU optimization
- **Codex** often good for: Methodology, statistics, experimental design, publication quality
- **Claude Code** often good for: Implementation, integration, pipeline work

**But assign flexibly based on actual need**, not topic categories.

---

## Git Workflow

### Branching

- **main**: Production-ready code
- Feature branches: Use for major changes
- Direct commits to main: OK for documentation, small fixes

### Commits

**Creating commits** (only when user requests):

```bash
# Check status
git status
git diff

# Stage relevant files
git add [files]

# Commit with proper message
git commit -m "$(cat <<'EOF'
Brief description of changes

- Detail 1
- Detail 2

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

**Important**:
- NEVER commit without user request
- NEVER skip hooks (--no-verify)
- NEVER force push to main
- ALWAYS check authorship before amending

### What to Commit

**Commit**:
- Source code
- Documentation
- Specs
- Configuration (except secrets)

**Don't commit** (use .gitignore):
- Model files (*.bin, *.safetensors, *.pt)
- Data files (*.jsonl, *.json - except specific exceptions)
- Checkpoints
- Logs
- .env files
- Large artifacts

### Commit Messages

- First line: Brief summary (imperative mood)
- Blank line
- Details (bullet points)
- Include co-authorship attribution

---

## Quick Reference

### Before Implementing Anything

1. ✅ Check `IMPLEMENTATION_REGISTRY.md` - does this exist?
2. ✅ Check `KNOWN_BUGS_AND_FIXES.md` - has this bug been fixed before?
3. ✅ Search codebase to verify no duplication

### After Implementing

1. ✅ Update `IMPLEMENTATION_REGISTRY.md`
2. ✅ Document any bugs fixed in `KNOWN_BUGS_AND_FIXES.md`
3. ✅ Add docstrings and comments
4. ✅ Test the implementation

### At Session Start (All Agents)

1. ✅ Check assigned tasks: `grep -l "Assigned To: {you}" tasks/claude_code/pending/*.md`
2. ✅ Check assigned reviews: `grep -l "Assigned Reviewers.*{you}" reviews/requests/*.md`
3. ✅ Read `ROADMAP.md` for current milestone
4. ✅ Read `status/PROJECT_STATUS.md` for context

### Creating Work Items

**Tasks**:
- Add to `/tasks/claude_code/pending/YYYYMMDD_HHMMSS_PX_description.md`
- Include `Assigned To: {agent}` header

**Review Requests**:
- Add to `/reviews/requests/YYYYMMDD_topic.md`
- Include `Assigned Reviewers: {agent1}, {agent2}` header

---

**See also**:
- `IMPLEMENTATION_REGISTRY.md` - What's been built
- `KNOWN_BUGS_AND_FIXES.md` - Bug history
- `BASE_MODEL_TRUTH.md` - Critical chat template issue
- `FILE_ORGANIZATION_STANDARDS.md` - Detailed file org (being consolidated into this doc)
- `REVIEW_PROTOCOL.md` - Review details (being consolidated into this doc)
