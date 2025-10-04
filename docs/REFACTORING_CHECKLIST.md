# Refactoring Checklist

**Purpose**: Prevent partial refactoring that creates multiple patterns

**Created**: 2025-10-04

---

## The Problem

**Partial refactoring is NO BETTER than reimplementation.**

Both create:
- ❌ Multiple sources of truth
- ❌ Inconsistent behavior
- ❌ Maintenance burden
- ❌ Future confusion
- ❌ Documentation lies

---

## Complete Refactoring Checklist

Use this checklist for ANY refactoring that creates shared utilities or consolidates duplicate code.

### Phase 1: Planning

- [ ] **Identify ALL callers** of the pattern being refactored
  ```bash
  # Example: Find all manual chat_template disabling
  grep -rn "chat_template = None" scripts/*.py
  ```

- [ ] **Count callers**: Record exact number (e.g., 15 scripts)

- [ ] **Estimate effort**: Can you migrate ALL in this session?
  - If NO: Don't start yet, create task for future session
  - If YES: Proceed

- [ ] **Check dependencies**: Will migration break anything?

- [ ] **Plan order**: Which scripts to migrate first? (critical → less critical)

### Phase 2: Implementation

- [ ] **Create utility** in appropriate location (usually `scripts/utils/`)

- [ ] **Add comprehensive docstrings**
  - What it does
  - Why it exists
  - How to use it
  - What it replaces

- [ ] **Add tests** (if appropriate)

- [ ] **Verify utility works** before migrating callers

### Phase 3: Migration

- [ ] **Migrate ALL callers** (no exceptions!)
  - Use grep to find each instance
  - Migrate one at a time
  - Test each migration compiles

- [ ] **Track progress**: Update counter (e.g., 3/15, 4/15, ...)

- [ ] **Delete old implementations** (don't leave "working" duplicates)

- [ ] **Comment out nothing** (either migrate or don't)

### Phase 4: Verification

- [ ] **Grep confirms no old pattern remains**
  ```bash
  # Should return ZERO active scripts (only archived/deprecated)
  grep -rn "OLD_PATTERN" scripts/*.py
  ```

- [ ] **All migrated scripts compile**
  ```bash
  # Quick syntax check
  python -m py_compile scripts/migrated_script.py
  ```

- [ ] **Run smoke test** if critical scripts affected

### Phase 5: Documentation

- [ ] **Update IMPLEMENTATION_REGISTRY**
  - Add utility as canonical implementation
  - Mark old pattern as DEPRECATED
  - Note migration completion

- [ ] **Update relevant docs**
  - CLEAN_MODEL_LOADER_MIGRATION.md (if applicable)
  - BASE_MODEL_TRUTH.md (if affects base model work)
  - STANDARDS.md (if new pattern to follow)

- [ ] **Update agent configs** if pattern is common

- [ ] **Update ROADMAP** if blocking other work

### Phase 6: Commit

- [ ] **Create descriptive commit message**
  ```
  Centralize [functionality] in [utility_name]

  Problem: [Description of duplication]
  Solution: Created [utility] and migrated all N callers

  - Created: scripts/utils/[utility].py
  - Migrated: [list all N scripts]
  - Verified: No old pattern remains

  See: docs/[RELEVANT_DOC].md
  ```

- [ ] **Commit atomically** (utility + all migrations together)

- [ ] **Push to remote**

---

## Red Flags (Stop and Reconsider)

If you find yourself thinking:

- ❌ "I'll migrate the critical scripts now, others later"
- ❌ "This script already works, we'll migrate it later"
- ❌ "Just use the new pattern for new scripts"
- ❌ "Partial migration is fine for now"
- ❌ "We're in a hurry, migration can wait"
- ❌ "That script isn't critical, skip it"
- ❌ "Let's document that new scripts should use the utility"

**STOP. You are about to create the partial refactoring anti-pattern.**

**Options**:
1. Migrate ALL callers right now (preferred)
2. Create a task to migrate all in future session
3. DON'T create the utility yet

**DO NOT** create utility and migrate some callers.

---

## Example: CleanModelLoader Migration

### Initial State
- **Pattern**: Manual `chat_template = None` in 15 scripts
- **Problem**: Easy to forget, duplicated in every script
- **Solution**: Create `CleanModelLoader` utility

### Planning
```bash
# Find all callers
grep -rn "chat_template = None" scripts/*.py
# Result: 15 scripts

# Estimate effort: ~1 hour to migrate all
# Decision: Proceed with complete migration
```

### Implementation
- Created: `scripts/utils/clean_model_loader.py`
- Added: Comprehensive docstrings
- Added: Self-test in `if __name__ == '__main__'`

### Migration
- Migrated: 15/15 scripts (100%)
  1. evaluate_instruction_following.py ✅
  2. generate_stage1_sft_data.py ✅
  3. test_base_model_ultra_clean.py ✅
  4. ... (all 15 completed)

### Verification
```bash
# Confirm no old pattern remains
grep -rn "chat_template = None" scripts/*.py
# Should return 0 results (except in archived/ or the utility itself)
```

### Documentation
- Updated: IMPLEMENTATION_REGISTRY.md (added CleanModelLoader)
- Updated: CLEAN_MODEL_LOADER_MIGRATION.md (migration guide)
- Updated: CLAUDE.md, codex.md, GEMINI.md (added warnings)
- Updated: ROADMAP.md (removed blocker)

### Commit
```
Centralize base model loading in CleanModelLoader

Problem: 15 scripts had duplicate chat_template disabling code
Solution: Created CleanModelLoader and migrated all 15 callers

- Created: scripts/utils/clean_model_loader.py
- Migrated: All 15 scripts (100% complete)
- Verified: No manual chat_template disabling remains

Prevents: Chat template contamination
See: docs/CLEAN_MODEL_LOADER_MIGRATION.md
```

---

## Incomplete Migration Example (DON'T DO THIS!)

### ❌ Wrong Approach
```
✅ Created CleanModelLoader
✅ Migrated 2 scripts
❌ Noted in ROADMAP: "Migrate remaining 13 scripts later"
❌ Committed partial work
```

### Result
- 2 scripts use CleanModelLoader
- 13 scripts use manual pattern
- Documentation says "use CleanModelLoader"
- Future contributors confused: "which pattern?"
- You now have TWO patterns instead of one

### Why This Is Worse
**Before refactoring**: 15 scripts with same (bad) pattern - consistent
**After partial refactoring**: 2 + 13 split - inconsistent and confusing

You've made the codebase WORSE, not better.

---

## Quick Reference

**Before creating utility**:
1. Count ALL callers
2. Can you migrate all NOW?
   - YES: Proceed
   - NO: Don't create utility yet

**While migrating**:
- Track: N/M migrated
- Never stop until N = M

**Before committing**:
```bash
# Must return 0 results
grep -rn "OLD_PATTERN" scripts/*.py
```

**Rule**: 100% migration or don't commit.

---

## See Also

- `/docs/STANDARDS.md#dry-principle--single-implementation` - Full policy
- `/docs/CLEAN_MODEL_LOADER_MIGRATION.md` - Real migration example
- `/docs/IMPLEMENTATION_REGISTRY.md` - What exists

---

**Remember**: Partial refactoring = reimplementation. Complete the job or don't start.
