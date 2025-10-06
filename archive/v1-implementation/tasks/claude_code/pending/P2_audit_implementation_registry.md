# P2: Audit IMPLEMENTATION_REGISTRY.md for Currency
**Assigned To**: claude_code

**Priority**: P2 (Medium - maintenance task)
**Estimated Time**: 45-60 minutes

## Issue Description

The IMPLEMENTATION_REGISTRY.md is supposed to be the definitive catalog of all implemented scripts, preventing re-implementation and duplication. However, we don't know if it's current and accurate.

**From VERIFICATION_STATUS.md**:
> **Not checked**: Is registry up to date?
> **Not checked**: Does it list all current scripts?
> **Not checked**: Are script descriptions accurate?

## Audit Tasks

### 1. Completeness Check

**Question**: Does the registry list all scripts that exist?

```bash
# Count actual scripts
find scripts -name "*.py" -not -path "*/archived/*" -not -path "*/.DEPRECATED" | wc -l

# Count scripts in registry
grep "^###.*\.py" docs/IMPLEMENTATION_REGISTRY.md | wc -l
```

**Action**:
- List all Python scripts in /scripts/ (excluding archived/)
- Cross-reference with registry entries
- Identify missing scripts
- Add missing scripts to registry

### 2. Accuracy Check

**Question**: Are existing registry entries accurate?

For each script entry in registry:
- [ ] File still exists at stated location
- [ ] Description matches actual functionality
- [ ] Line number references are correct
- [ ] Status markers (✅/❌) are current
- [ ] Dependencies listed are accurate

**Example issues found**:
- Registry says `stage1_generate.py` is "Complete and correct" (line 79)
- But that script is contaminated and has been archived!
- This is incorrect and misleading

### 3. Deprecation Tracking

**Question**: Are deprecated scripts marked as such?

Check that archived scripts are either:
- Removed from registry, OR
- Marked as deprecated with pointer to replacement

**Scripts we just archived**:
- [ ] `stage1_generate.py` - Mark as deprecated, point to generate_stage1_sft_data.py
- [ ] `stage1_generate_robust.py` - Mark as deprecated
- [ ] `generate_stage1_data.py` - Mark as deprecated

### 4. Organization Check

**Question**: Is the registry well-organized and easy to navigate?

Current structure needs review:
- Are scripts grouped logically?
- Are primary/canonical scripts clearly marked?
- Are superseded scripts clearly indicated?
- Is there a table of contents or index?

### 5. Metadata Check

**Question**: Does each entry have sufficient metadata?

Each script entry should have:
- [ ] Purpose (clear, one-line description)
- [ ] Key features (bullet points)
- [ ] Status (✅ current, ⚠️ issues, ❌ deprecated)
- [ ] Dependencies (other scripts, utilities)
- [ ] Line number references for critical features
- [ ] Generated artifacts (if applicable)
- [ ] Last updated timestamp

## Success Criteria

- [ ] All non-archived scripts are listed in registry
- [ ] All registry entries are accurate (tested spot-check of 5-10 scripts)
- [ ] Deprecated scripts are properly marked
- [ ] Registry is well-organized with clear primary scripts
- [ ] Each entry has complete metadata

## Proposed Registry Structure

Consider reorganizing into sections:

```markdown
# Implementation Registry

## Stage 1: Explicit Instruction Following

### Data Generation (Primary)
- ⭐ generate_stage1_sft_data.py - PRIMARY SFT DATA GENERATOR [current, clean]

### Data Generation (Deprecated)
- ❌ stage1_generate.py - DEPRECATED: chat template contamination
- ❌ stage1_generate_robust.py - DEPRECATED: chat template contamination
- ❌ generate_stage1_data.py - DEPRECATED: chat template contamination

### Training
- ✅ train_stage1_sft.py - SFT training [current]
- ✅ train_stage1_dpo_improved.py - DPO training [current]

### Evaluation
- ✅ test_base_model_ultra_clean.py - Base model verification [current, not yet run]
- ❓ evaluate_stage1_comprehensive.py - Comprehensive eval [status unknown]
- ❓ evaluate_stage1_corrected.py - Corrected eval [superseded?]

... etc
```

## Deliverables

1. **Audit Report**: Document in this task file:
   - Missing scripts (list)
   - Inaccurate entries (list with corrections)
   - Organizational issues (recommendations)

2. **Updated Registry**: Make corrections to IMPLEMENTATION_REGISTRY.md

3. **Maintenance Process**: Add to STANDARDS.md:
   - When to update registry (after creating ANY script)
   - What metadata to include
   - How to mark deprecations

## Why This Matters

From STANDARDS.md:
> **Document immediately**: Update `IMPLEMENTATION_REGISTRY.md` after creating

If the registry is out of date:
- Won't prevent re-implementation (defeats its purpose)
- Misleading information (says contaminated script is "correct")
- Wasted time searching for scripts
- Risk of using wrong/deprecated scripts

## Related Files

- `/docs/IMPLEMENTATION_REGISTRY.md` - The registry itself
- `/docs/DEPRECATED_SCRIPTS.md` - Recently created deprecation list
- `/docs/STANDARDS.md` - Documentation standards
- `/docs/VERIFICATION_STATUS.md` - Notes about registry currency

## Time Budget

- Completeness check: 15 minutes
- Accuracy spot-check: 15 minutes
- Deprecation updates: 10 minutes
- Reorganization (if needed): 15 minutes
- Documentation: 10 minutes

Total: ~45-60 minutes

## Notes

This is a P2 (not P0) because:
- Doesn't block training (unlike verification tasks)
- More about maintenance and preventing future issues
- Can be done after P0/P1 tasks complete

But it's important for long-term project health.
