# Project Status

**Last Updated**: 2025-10-03
**Current Phase**: Stage 1 Implementation → Testing & Fixing

---

## Current Focus

Fixing P0 evaluation memory management bug before RunPod deployment. The evaluation script loads all models (base, SFT, DPO) concurrently, causing memory issues and incorrect results. Need to refactor to sequential loading before we can test the pipeline on RunPod.

---

## What's Blocking Progress

**P0 Evaluation Bug**: `evaluate_capability_differentiation.py` loads models concurrently rather than sequentially. This will cause OOM on the GPU and produce wrong results due to adapter conflicts. Must fix before RunPod testing.

See: `/tasks/claude_code/pending/20250912_170000_P0_fix_evaluation_memory_management.md`

---

## Recent Changes

**2025-10-03**: Major documentation restructuring
- Reorganized into DAG architecture with minimal duplication
- Created unified review system (single queue, mandatory assignment)
- Consolidated all standards into single STANDARDS.md
- Created ROADMAP.md with milestone tracking
- Established universal assignment system for tasks and reviews

**2025-09-13**: SFT data generation completed
- Generated 200 high-quality SFT training examples
- Verified chat template contamination fix is working
- Preference pairs created (188 pairs)

**2025-09-12**: External reviews completed
- Gemini technical review: Approved architecture, found 1 P0 bug (eval memory)
- Codex methodology review: Found 2 P0 issues (eval memory, statistical rigor)
- All feedback converted to tasks

---

## Next Steps

1. **Fix P0 evaluation bug** (immediate priority)
   - Refactor to sequential model loading
   - Add explicit GPU cache clearing
   - Test locally before RunPod

2. **Deploy to RunPod** (after P0 fix)
   - Transfer latest code
   - Verify environment setup
   - Run baseline assessment first

3. **Baseline Assessment**
   - Test base model capabilities (expect ~10-30% instruction following)
   - Verify no chat template contamination
   - Document baseline for comparison

4. **Full Stage 1 Training Run**
   - Generate full SFT dataset (500-1000 examples)
   - Train SFT model
   - Train DPO model from SFT checkpoint
   - Evaluate all three models

---

## Context Notes

### The Chat Template Issue
We kept rediscovering a critical bug where the Qwen tokenizer automatically applies chat templates, making the base model appear to follow instructions when it actually shouldn't. This has been properly documented in `/docs/BASE_MODEL_TRUTH.md` with sentinel tests to detect contamination.

### Re-Implementation Prevention
Built comprehensive documentation system (IMPLEMENTATION_REGISTRY, KNOWN_BUGS_AND_FIXES) because we kept re-implementing existing features and reproducing old bugs across sessions.

### Pipeline Status
Core pipeline is implemented and tested locally with small datasets. All 6 scripts exist and work. Just need to fix the P0 bug and then we can do full-scale RunPod testing.

---

**For milestone checklist, see**: `ROADMAP.md`
**For detailed implementation catalog, see**: `/docs/IMPLEMENTATION_REGISTRY.md`
**For current work queue, see**: `/tasks/claude_code/pending/` (14 tasks)
**For review requests, see**: `/reviews/requests/` (currently none pending)
