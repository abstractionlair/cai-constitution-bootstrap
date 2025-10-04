# Review Management Protocol for Claude Code

## Overview
This project uses a file-based review system for code review and validation. Reviews are managed through the filesystem, not copy/paste. Claude Code should both read existing reviews and write new review requests.

## Directory Structure
```
/Users/scottmcguire/MaximalCAI/reviews/
├── gemini/                  # Technical/implementation reviews
│   ├── pending/            # New review requests for Gemini
│   ├── in_progress/        # Reviews being worked on
│   ├── done/               # Completed review requests
│   └── responses/          # Review responses from Gemini
├── codex/                   # Methodology/approach reviews
│   ├── pending/            # New review requests for Codex
│   ├── in_progress/        # Reviews being worked on
│   ├── done/               # Completed review requests
│   └── responses/          # Review responses from Codex
└── claude_code/            # Self-reviews by Claude Code
    ├── pending/            # Self-review requests
    └── completed/          # Completed self-reviews
```

## Reading Reviews

### Check for New Reviews
Always check these directories for review feedback:
1. `/reviews/gemini/responses/` - Technical feedback from Gemini
2. `/reviews/codex/responses/` - Methodology feedback from Codex
3. `/reviews/claude_code/pending/` - Self-review requests

### Review File Format
Reviews follow this naming convention:
```
YYYYMMDD_HHMMSS_component_review.md
```

Example: `20241228_120000_stage1_verification.md`

### Processing Reviews
1. Read the review file completely
2. Identify issues by priority (FATAL, HIGH, MEDIUM, LOW)
3. Create tasks for fixes in `/tasks/claude_code/pending/`
4. Move processed reviews to `done/` directory
5. Update PERSISTENT_STATE.md with review summary

## Writing Review Requests

### When to Request Reviews
Request reviews when:
- Completing a major component (e.g., Stage 1 implementation)
- Making significant architectural changes
- Before deployment to RunPod
- After fixing critical issues
- When unsure about approach

### Creating Review Requests

#### For Gemini (Technical Review)
Create file in `/reviews/gemini/pending/`:
```markdown
# Review Request: [Component Name]
Date: YYYY-MM-DD HH:MM
Requester: Claude Code
Priority: [High/Medium/Low]

## Component Overview
[Brief description of what this component does]

## Files to Review
- `scripts/[filename].py`
- `scripts/utils/[filename].py`
- [List all relevant files]

## Specific Questions
1. [Specific technical question]
2. [Performance concern]
3. [Implementation approach validation]

## Context
[Any relevant context about decisions made]

## Known Issues
[List any known issues or TODOs]

## Testing Status
- [ ] Unit tests written
- [ ] Integration tests passed
- [ ] Performance benchmarked
- [ ] Edge cases handled

## Checklist for Reviewer
Please check for:
- [ ] Code correctness
- [ ] Performance issues
- [ ] Security concerns
- [ ] Best practices
- [ ] Error handling
- [ ] Documentation completeness
```

#### For Codex (Methodology Review)
Create file in `/reviews/codex/pending/`:
```markdown
# Review Request: [Methodology/Approach Name]
Date: YYYY-MM-DD HH:MM
Requester: Claude Code
Priority: [High/Medium/Low]

## Approach Overview
[Description of the methodology being used]

## Scientific/Methodological Questions
1. [Statistical validity question]
2. [Experimental design question]
3. [Bias or confounding factors]

## Data Pipeline
[Describe data flow and transformations]

## Evaluation Metrics
[List metrics and why they were chosen]

## Assumptions
[List key assumptions being made]

## Alternative Approaches Considered
[What else was considered and why rejected]

## Checklist for Reviewer
Please validate:
- [ ] Statistical rigor
- [ ] Experimental design
- [ ] Data contamination prevention
- [ ] Evaluation validity
- [ ] Reproducibility
- [ ] Scientific claims
```

#### For Self-Review (Claude Code)
Create file in `/reviews/claude_code/pending/`:
```markdown
# Self-Review: [Component Name]
Date: YYYY-MM-DD HH:MM
Stage: [Development/Pre-deployment/Post-fix]

## What I Built
[Summary of implementation]

## Design Decisions
[Key decisions and rationale]

## Potential Issues
[Things I'm uncertain about]

## Testing Performed
[What testing was done]

## Next Steps
[What comes next]

## Questions for Future Review
[Things to validate with human or other reviewers]
```

### Review Response Handling

When a review response arrives in `/reviews/*/responses/`:

1. **Parse the Review**
   - Extract all issues found
   - Categorize by priority (FATAL, HIGH, MEDIUM, LOW)
   - Note specific line numbers or files mentioned

2. **Create Fix Tasks**
   For each issue, create a task in `/tasks/claude_code/pending/`:
   ```markdown
   # [Priority]: Fix [Issue Name]
   Source: [Gemini/Codex] Review YYYYMMDD_HHMMSS
   
   ## Issue Description
   [What the reviewer found]
   
   ## Location
   File: [filename]
   Line: [line numbers if provided]
   
   ## Suggested Fix
   [Reviewer's suggestion if provided]
   
   ## Impact
   [Why this matters]
   ```

3. **Update Tracking**
   - Move review request from `pending/` to `done/`
   - Update PERSISTENT_STATE.md with review summary
   - Log review completion in project log

## Review Priority Guidelines

### Request Review Priority
- **URGENT**: Blocking deployment, critical bugs, safety issues
- **HIGH**: Major functionality, before stage completion
- **MEDIUM**: Optimization, refactoring, best practices
- **LOW**: Documentation, style, minor improvements

### Issue Priority in Reviews
- **FATAL**: Makes results invalid, breaks core functionality
- **HIGH**: Significant issues that should be fixed
- **MEDIUM**: Important but not blocking
- **LOW**: Nice to have, optimization opportunities

## Best Practices

1. **Always Request Reviews For:**
   - Stage completions
   - Major algorithmic changes
   - Before expensive training runs
   - After fixing FATAL issues

2. **Include in Review Requests:**
   - Clear component boundaries
   - Specific questions
   - Known limitations
   - Testing status

3. **When Processing Reviews:**
   - Address FATAL issues first
   - Create detailed fix tasks
   - Update documentation
   - Thank the reviewer in commit messages

4. **File Management:**
   - Use consistent naming: YYYYMMDD_HHMMSS_component_type.md
   - Move files to appropriate directories after processing
   - Never delete review files (archive if needed)
   - Keep review responses for audit trail

## Example Workflow

1. Claude Code completes Stage 1 implementation
2. Creates review requests:
   - `/reviews/gemini/pending/20241228_150000_stage1_implementation.md`
   - `/reviews/codex/pending/20241228_150000_stage1_methodology.md`
3. Waits for responses (continues with other tasks)
4. Finds response in `/reviews/gemini/responses/20241228_160000_stage1_implementation_review.md`
5. Parses issues, creates fix tasks
6. Implements fixes
7. Creates new review request for fixes
8. Moves original request to `done/`
9. Updates PERSISTENT_STATE.md

## Important Notes

- **Never modify review responses** - they are historical records
- **Always create tasks for issues** - don't try to remember them
- **Check for reviews regularly** - at start of each session
- **Be specific in review requests** - help reviewers help you
- **Track everything** - reviews are part of the development history

## Review Request Templates Location
Templates for different types of reviews are in:
`/Users/scottmcguire/MaximalCAI/reviews/templates/`

## Questions?
If unsure about review protocol, check:
1. This file (REVIEW_PROTOCOL.md)
2. PERSISTENT_STATE.md for current review status
3. Example reviews in `done/` directories
