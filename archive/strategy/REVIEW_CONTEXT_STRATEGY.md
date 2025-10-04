# Review Context Management Strategy

## Problem
Gemini and Codex CLIs don't retain session information, making iterative reviews cumbersome.

## Solution: Context Documents

### 1. Create Review Request Documents
Before calling reviewers, create a comprehensive context document:

```bash
# scripts/prepare_review.py
```

This script would:
- Summarize what was implemented
- List what was fixed since last review
- Include specific questions for the reviewer
- Bundle relevant code snippets

### 2. Review Templates

Create templates for common review scenarios:

#### For Gemini (Technical Review):
```markdown
# Technical Review Request for Gemini

## Previous Issues You Found
[List from last review]

## What We Fixed
[List of fixes with file:line references]

## Please Check
1. Are the path fixes correct for RunPod?
2. Is the precision now consistent?
3. Are timeouts appropriate?

## Code to Review
[Include only changed sections]
```

#### For Codex (Methodology Review):
```markdown
# Methodology Review Request for Codex

## Previous Concerns
[List from last review]

## Our Changes
[What we changed and why]

## Please Verify
1. Is the 95% gate properly enforced?
2. Is constitution actually being used?
3. Is data diversity sufficient?

## Key Code Sections
[Include relevant snippets]
```

### 3. Automated Review Script

```python
#!/usr/bin/env python3
"""
prepare_review.py - Prepare context for external reviewers
"""

import json
from pathlib import Path
from datetime import datetime

class ReviewPreparer:
    def __init__(self):
        self.review_dir = Path("reviews")
        self.review_dir.mkdir(exist_ok=True)
        
    def prepare_gemini_review(self, stage: str, previous_issues: list, fixes_made: list):
        """Prepare technical review for Gemini"""
        
        review_doc = f"""# Gemini Technical Review - {stage} - {datetime.now().isoformat()}

## Context
You previously reviewed our {stage} implementation and found these issues:
{self._format_issues(previous_issues)}

## What We Fixed
{self._format_fixes(fixes_made)}

## Files Changed
{self._list_changed_files()}

## Specific Questions
1. Do all scripts use BASE_DIR correctly for RunPod paths?
2. Is the precision consistent between baseline and evaluation?
3. Are the timeouts appropriate for each step?
4. Is the checkpoint selection robust?

## Code Sections to Review
{self._include_key_code_sections()}

Please focus on technical correctness and deployment readiness.
"""
        
        output_file = self.review_dir / f"gemini_review_{stage}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        output_file.write_text(review_doc)
        
        return output_file
    
    def prepare_codex_review(self, stage: str, previous_concerns: list, changes_made: list):
        """Prepare methodology review for Codex"""
        
        review_doc = f"""# Codex Methodology Review - {stage} - {datetime.now().isoformat()}

## Context
You previously reviewed our {stage} implementation methodology and found:
{self._format_issues(previous_concerns)}

## Our Responses
{self._format_fixes(changes_made)}

## Scientific Questions
1. Is the 95% success gate properly enforced?
2. Does the pipeline follow DPO best practices?
3. Is the data generation diverse enough?
4. Are evaluation metrics appropriate?

## Key Algorithms
{self._include_methodology_code()}

Please focus on scientific validity and methodology.
"""
        
        output_file = self.review_dir / f"codex_review_{stage}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        output_file.write_text(review_doc)
        
        return output_file
```

### 4. Quick Review Commands

Add to your workflow:

```bash
# Prepare reviews
python scripts/prepare_review.py --stage 1 --reviewer gemini
python scripts/prepare_review.py --stage 1 --reviewer codex

# Then paste the generated document to the reviewer
cat reviews/gemini_review_stage1_*.md | pbcopy  # Mac
cat reviews/codex_review_stage1_*.md | pbcopy
```

### 5. Review History Tracking

```json
// reviews/review_history.json
{
  "stage_1": {
    "reviews": [
      {
        "date": "2024-XX-XX",
        "reviewer": "gemini",
        "issues_found": [...],
        "fixes_applied": [...],
        "status": "fixed"
      }
    ]
  }
}
```

## Benefits

1. **Reduced Friction**: One command prepares everything
2. **Consistent Context**: Reviewers always get complete information
3. **Trackable Progress**: Clear history of issues and fixes
4. **Focused Reviews**: Reviewers only see what's relevant
5. **Time Efficient**: No need to re-explain everything

Would you like me to implement this review preparation system?
