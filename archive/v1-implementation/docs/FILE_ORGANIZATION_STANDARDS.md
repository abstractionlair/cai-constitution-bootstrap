# File Organization Standards

**Last Updated**: 2025-10-03

## Guiding Principles

1. **Single Source of Truth**: One canonical document per topic
2. **Temporal Clarity**: Current state vs historical archive clearly separated
3. **Discovery Prevention**: Make it easy to find what's already implemented
4. **Deprecation Over Deletion**: Archive old docs, don't delete (preserve history)

## Directory Structure

```
/
├── docs/                          # Living documentation
│   ├── FILE_ORGANIZATION_STANDARDS.md  # This file
│   ├── IMPLEMENTATION_REGISTRY.md      # What's implemented & where
│   ├── KNOWN_BUGS_AND_FIXES.md         # Bug history to prevent regression
│   └── *.md                            # Other persistent documentation
│
├── status/                        # Current project state (SINGLE SOURCE OF TRUTH)
│   ├── PROJECT_STATUS.md          # Overall progress and next steps
│   ├── RUNPOD_STATUS.md           # Current pod configuration and access
│   └── REVIEW_STATUS.md           # Pending and completed reviews
│
├── archive/                       # Historical documents
│   ├── status/                    # Old status snapshots
│   ├── reviews/                   # Completed review discussions
│   └── decisions/                 # Past decision documents
│
├── tasks/
│   └── claude_code/
│       ├── pending/               # Not started (YYYYMMDD_HHMMSS_PX_description.md)
│       ├── in_progress/           # Currently working on
│       ├── completed/             # Done (with completion notes)
│       ├── blocked/               # Waiting on external dependency
│       └── obsolete/              # No longer relevant
│
├── specs/                         # Design specifications (rarely change)
│   ├── stage_N_*.md               # Stage specifications
│   └── archive/                   # Old/superseded specs
│
├── scripts/                       # Implementation code
│   ├── stage1_*.py                # Stage-specific scripts
│   ├── utils/                     # Shared utilities
│   └── archived/                  # Old/superseded scripts
│
├── data/, artifacts/, checkpoints/, logs/, results/
│   # Runtime outputs (mostly .gitignored)
│
└── Root files (MINIMIZE)
    ├── README.md                  # Project overview for GitHub
    ├── CLAUDE.md                  # Instructions for Claude Code
    ├── constitution.yaml          # Core project data
    └── .gitignore, .env, etc.     # Config files
```

## File Lifecycle

### Status Documents
- **Creation**: When project state changes significantly
- **Update**: Continuously (single living document)
- **Archive**: When a major milestone completes, snapshot to `archive/status/YYYYMMDD_description.md`
- **Location**: `/status/` directory

### Task Files
- **Creation**: When work is identified
- **Naming**: `YYYYMMDD_HHMMSS_PX_short_description.md` (where X is 0-3)
- **Movement**: `pending/` → `in_progress/` → `completed/` or `obsolete/`
- **Completion**: Add completion notes, then move to `completed/`
- **Obsolete**: Move to `obsolete/` (don't delete - preserves history)

### Implementation Code
- **Creation**: When implementing a feature
- **Naming**: `stage{N}_{action}_{noun}.py` or `{verb}_{noun}.py`
- **Documentation**: Register in `IMPLEMENTATION_REGISTRY.md`
- **Superseding**: Move old version to `scripts/archived/`, update registry
- **Testing**: Create corresponding test file in same directory

### Review Documents
- **During**: Live in `/reviews/{reviewer}/pending/`
- **After**: Move to `/reviews/{reviewer}/responses/`
- **Long-term**: Distill insights into `/docs/` or archive

## Critical Anti-Pattern Prevention

### Problem: Re-implementing existing code
**Solution**: `docs/IMPLEMENTATION_REGISTRY.md`
- Lists all implemented features
- Points to exact file and line numbers
- Describes what each script does
- Updated whenever code is written

### Problem: Reproducing old bugs
**Solution**: `docs/KNOWN_BUGS_AND_FIXES.md`
- Documents bugs discovered
- Records the fix applied
- Links to commit or file changes
- Searchable by symptom

### Problem: Multiple "current status" docs
**Solution**: Single source of truth in `/status/`
- ONE PROJECT_STATUS.md
- ONE RUNPOD_STATUS.md
- ONE REVIEW_STATUS.md
- Archive old versions

## Naming Conventions

### Task Files
```
YYYYMMDD_HHMMSS_P{0-3}_short_description.md

Examples:
20251003_140530_P0_fix_memory_leak.md
20251003_141200_P1_improve_logging.md
```

### Status Snapshots (when archiving)
```
YYYYMMDD_description.md

Examples:
archive/status/20250912_post_review_state.md
archive/status/20250913_pre_runpod_deployment.md
```

### Scripts
```
stage{N}_{verb}_{noun}.py          # Stage-specific
{verb}_{noun}.py                   # General utility
test_{script_name}.py              # Tests

Examples:
stage1_generate_sft_data.py
evaluate_capability_differentiation.py
test_data_formatter.py
```

## Root Directory Policy

**ONLY these files allowed in root:**
- `README.md` - GitHub project overview
- `CLAUDE.md` - Claude Code instructions (references `/docs/` and `/status/`)
- `constitution.yaml` - Core project data
- Configuration files: `.gitignore`, `.env*`, `.git*`

**Everything else moves to:**
- Current state → `/status/`
- Documentation → `/docs/`
- Historical → `/archive/`
- Specifications → `/specs/`

## Implementation Checklist

When creating new code:
- [ ] Update `docs/IMPLEMENTATION_REGISTRY.md` with what you built
- [ ] If fixing a bug, document in `docs/KNOWN_BUGS_AND_FIXES.md`
- [ ] Use standard naming convention
- [ ] Place in correct directory
- [ ] Archive any superseded code (don't delete)

When starting new work:
- [ ] Check `docs/IMPLEMENTATION_REGISTRY.md` - does this exist already?
- [ ] Check `docs/KNOWN_BUGS_AND_FIXES.md` - has this bug been fixed before?
- [ ] Check `tasks/claude_code/completed/` - was this already done?
- [ ] Search codebase to verify no duplication

## Migration Notes

These standards are being applied as of 2025-10-03. Existing files will be reorganized according to these rules. See `migration/` directory for transition artifacts.
