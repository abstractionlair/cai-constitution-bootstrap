# File Audit - Root Directory Cleanup

**Date**: 2025-10-03
**Purpose**: Document decisions for root directory cleanup

---

## Status Documents (Consolidate → /status/)

### Keep & Consolidate Into Single PROJECT_STATUS.md
- `PROJECT_STATUS.md` (2025-09-13) - Most recent general status
- `IMPLEMENTATION_STATUS_AFTER_REVIEWS.md` (2025-09-12) - Post-review state
- `PERSISTENT_STATE.md` (2024-12-28) - Older status, some outdated info

**Decision**: Create new consolidated `/status/PROJECT_STATUS.md`, archive others

### Keep & Move
- `POD_STATUS.md` → `/status/RUNPOD_STATUS.md` (rename for clarity)

---

## Fix/Review Documents (Archive → /archive/)

### Already Fixed - Archive
- `CRITICAL_FIXES.md` - Fixes from Sept 12
- `FIX_REQUEST_COMPREHENSIVE.md` - Old fix request
- `FIXES_APPLIED.md` - Historical fixes
- `REVISED_FIX_PRIORITIES.md` - Old priorities

**Decision**: Move to `/archive/reviews/20250912_fix_cycle/`

### Review Summaries - Archive
- `STAGE1_CODE_REVIEW.md` - Initial review
- `STAGE1_CODE_REVIEW_UPDATED.md` - Updated review
- `REVIEW_SUMMARY_STAGE1.md` - Summary

**Decision**: Move to `/archive/reviews/20250912_stage1_reviews/`

---

## Communication Documents (Archive → /archive/)

### Historical Context - Archive
- `MESSAGE_TO_CLAUDE_CODE.md` - Old message
- `ANSWERS_FOR_CLAUDE_CODE.md` - Old answers
- `START_HERE.md` - Outdated orientation

**Decision**: Move to `/archive/communication/`

---

## Configuration Documents (Keep in Docs → /docs/)

### Move to /docs/ (Permanent Reference)
- `BASE_MODEL_TRUTH.md` → `/docs/` (CRITICAL - prevent regression)
- `DATA_GENERATION_ARCHITECTURE.md` → `/docs/` (Architecture reference)
- `FEW_SHOT_PROMPTING.md` → `/docs/` (Implementation details)
- `RUNPOD_SSH_SOLUTION.md` → `/docs/` (Operational guide)
- `SSH_SOLUTION.md` - Duplicate/older? Merge with above
- `REVIEW_PROTOCOL.md` → `/docs/` (Process documentation)

---

## Strategy/Planning Documents

### Keep in Root (These Change)
- `CLAUDE.md` - Primary instructions (update to reference /docs/ and /status/)
- `README.md` - GitHub overview
- `constitution.yaml` - Core data

### Move to /docs/ (Permanent)
- `DEPLOYMENT_CHECKLIST.md` → `/docs/` (Operational reference)
- `REVIEW_CONTEXT_STRATEGY.md` → `/docs/` or archive?
- `IMPLEMENTATION_STRATEGY.md` - Archive (old strategy)

### Archive (Historical)
- `QUICK_START.md` - Superseded by better docs
- `UPDATED_PROJECT_INSTRUCTIONS.md` - Superseded by CLAUDE.md updates

---

## Agent Configuration

### Keep in Root (Active Configuration)
- `AGENTS.md` → Symlink to `codex.md` (keep as-is)
- `codex.md` - Codex agent config
- `GEMINI.md` - Gemini agent config (or move to /docs/?)
- `AGENT_CONFIG_NOTES.md` - Move to /docs/ or merge into agent configs

**Decision**: Review if these should be in .claude/ instead

---

## Clarification Documents (Archive)

### Superseded - Archive
- `CLARIFICATION_BASE_MODEL.md` - Superseded by BASE_MODEL_TRUTH.md

**Decision**: Archive to `/archive/decisions/`

---

## Summary of Actions

### Create New Consolidated Files in /status/
1. `/status/PROJECT_STATUS.md` - Current state, next steps
2. `/status/RUNPOD_STATUS.md` - Pod config, SSH, current state
3. `/status/REVIEW_STATUS.md` - Pending reviews, recent feedback

### Move to /docs/ (Permanent Reference)
- `BASE_MODEL_TRUTH.md`
- `DATA_GENERATION_ARCHITECTURE.md`
- `FEW_SHOT_PROMPTING.md`
- `RUNPOD_SSH_SOLUTION.md` (merge with SSH_SOLUTION.md)
- `REVIEW_PROTOCOL.md`
- `DEPLOYMENT_CHECKLIST.md`
- `AGENT_CONFIG_NOTES.md` (maybe)

### Archive (Historical)
- `/archive/status/` - Old PROJECT_STATUS, IMPLEMENTATION_STATUS, PERSISTENT_STATE
- `/archive/reviews/20250912_fix_cycle/` - CRITICAL_FIXES, FIX_REQUEST, FIXES_APPLIED, REVISED_FIX_PRIORITIES
- `/archive/reviews/20250912_stage1_reviews/` - CODE_REVIEW docs, REVIEW_SUMMARY
- `/archive/communication/` - MESSAGE_TO_CLAUDE_CODE, ANSWERS, START_HERE
- `/archive/decisions/` - CLARIFICATION_BASE_MODEL
- `/archive/strategy/` - IMPLEMENTATION_STRATEGY, QUICK_START, UPDATED_PROJECT_INSTRUCTIONS, REVIEW_CONTEXT_STRATEGY

### Keep in Root (Minimal)
- `README.md`
- `CLAUDE.md` (update to reference new locations)
- `constitution.yaml`
- `codex.md`, `AGENTS.md`, `GEMINI.md` (agent configs - consider moving to .claude/)
- Configuration files (`.env`, `.gitignore`, etc.)

---

## Root Directory Goal

After cleanup, root should have:
```
/
├── README.md
├── CLAUDE.md
├── constitution.yaml
├── codex.md, AGENTS.md (symlink), GEMINI.md
├── .env, .gitignore, .git*, etc.
└── [That's it!]
```

Everything else organized in:
- `/status/` - Current state
- `/docs/` - Permanent reference
- `/archive/` - Historical
- `/specs/` - Specifications
- `/scripts/` - Implementation
- `/tasks/` - Work tracking

---

**Next**: Execute this reorganization
