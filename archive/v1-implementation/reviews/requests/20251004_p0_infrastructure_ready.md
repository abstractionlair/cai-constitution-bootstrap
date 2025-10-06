# Review Request: P0 Infrastructure Complete - Ready for GPU Production

**Date**: 2025-10-04
**Requester**: claude_code
**Assigned Reviewers**: codex, gemini
**Priority**: HIGH (Blocks $300 GPU production work)
**Commit**: 2b6368d

---

## Summary

Implemented both P0 blockers identified in previous Codex review:
1. **Evaluation Statistics**: Publication-quality statistical analysis (McNemar, BH correction, effect sizes, CIs)
2. **Provenance Persistence**: Comprehensive metadata tracking for all artifacts

Plus P2 quality-of-life improvements (requirements.txt).

This unblocks GPU production work. System is now ready for N=1000 paired evaluation with proper statistics and full provenance tracking.

---

## Changes Overview

### Core Infrastructure (P0)

**1. Statistical Analysis** (`scripts/utils/eval_statistics.py`, 603 lines)
- McNemar test for paired binary outcomes (with continuity correction)
- Benjamini-Hochberg multiple testing correction (FDR control)
- Cohen's h effect size for proportion differences
- Wilson confidence intervals (better than normal approximation)
- Bootstrap CIs for arbitrary statistics
- `paired_comparison_analysis()` - Complete pipeline function
- 30 unit tests, all passing

**2. Provenance Tracking** (`scripts/utils/provenance_helper.py`, 345 lines)
- Git commit tracking (full SHA as "safety net")
- Queryable metadata fields (model, params, seeds)
- `create_artifact_metadata()` - Standardized metadata for any artifact
- `create_session_manifest()` - Session-level tracking with environment snapshot
- Detects uncommitted changes (git dirty state)

**3. Session Manifest** (`scripts/create_session_manifest.py`, 130 lines)
- Run at GPU session start
- Captures: git state, environment (Python/PyTorch/CUDA/GPU), planned artifacts
- Warns if uncommitted changes detected

### Quality of Life (P2)

**4. Dependency Management**
- `requirements.txt` - Single-command production install
- `requirements-dev.txt` - Development dependencies
- Updated setup script to use requirements.txt
- Updated documentation

---

## Key Design Decisions

### Statistical Analysis

**Why these specific tests?**
- **McNemar**: Correct test for paired binary data (base vs SFT on same examples)
- **Benjamini-Hochberg**: Less conservative than Bonferroni, controls FDR not FWER
- **Cohen's h**: Standard effect size for proportions (arcsine transformation)
- **Wilson CI**: Better coverage than normal approximation for proportions near 0/1
- **Bootstrap**: For statistics without closed-form CIs (e.g., lift = p2 - p1)

**Evaluation protocol:**
- N = 1000 (target), stratified by instruction type
- Paired design: identical items for base/SFT/DPO
- Deterministic decoding (temperature=0) for baselines
- Report: overall + per-type statistics
- Multiple testing correction across types

**Output structure:**
```json
{
  "overall": {
    "n": 1000,
    "base_rate": 0.15, "base_ci": [0.13, 0.17],
    "sft_rate": 0.78, "sft_ci": [0.75, 0.81],
    "lift": 0.63, "lift_ci_bootstrap": [0.60, 0.66],
    "mcnemar_chi2": 450.2, "mcnemar_p": 1.2e-99,
    "cohens_h": -1.33
  },
  "by_type": {
    "list": {
      "mcnemar_p_raw": 3.4e-20,
      "mcnemar_p_adjusted": 2.4e-19,
      "significant_after_bh": true,
      ...
    }
  },
  "bh_correction": {"fdr": 0.10, "n_tests": 12, "n_significant": 11}
}
```

### Provenance Tracking

**Philosophy:**
- Git commit is "safety net" - can look up any details if needed
- But capture commonly-queried fields for easy filtering/comparison
- Warn if git is dirty (uncommitted changes)

**Metadata fields:**
```json
{
  "git_commit": "abc123...",  // Full SHA (40 chars)
  "timestamp": "2025-10-04T15:30:45",
  "loader_version": "def456...",  // CleanModelLoader git SHA
  "model_name": "Qwen/Qwen2.5-32B",
  "quantization": "4bit",
  "template_disabled": true,
  "script_name": "generate_stage1_sft_data.py",
  "artifact_type": "training_data",
  // Plus any extra fields (seed, temperature, models, dataset)
}
```

**Per-artifact metadata:**
- Training data: Per-record metadata in JSONL
- Evaluation: Per-evaluation metadata in JSON
- Session: Session manifest at session start

---

## Testing

### Statistical Functions
- **Unit tests**: 30 tests, all passing
- **Test coverage**:
  - McNemar: Hand-calculated values, edge cases (no discordant pairs, one-sided)
  - Benjamini-Hochberg: All/none/partial rejection, ordering invariance
  - Cohen's h: Known values, symmetry, edge cases (0%, 100%)
  - Wilson CI: Comparison with scipy, bounds checking, width vs N
  - Bootstrap: Reproducibility, mismatched lengths
  - Integration: Three-way comparison (base→SFT→DPO)

### Provenance Functions
- **Manual testing**: Local testing successful (limited by torch dependency)
- **Will test on GPU**: Full end-to-end test on H100 pod

### Smoke Test
- **H100 smoke test**: Passed (96.5s, ~$0.047)
- All 5 tests passed: loader, generation, contamination, metadata patterns
- Verified CleanModelLoader works correctly with provenance

---

## Integration Plan

### Data Generation Scripts
Add metadata to JSONL records:
```python
from utils.provenance_helper import create_artifact_metadata
from pathlib import Path

example = {
    'instruction': inst,
    'response': resp,
    'metadata': create_artifact_metadata(
        provenance=self.provenance,  # from CleanModelLoader
        script_name=Path(__file__).name,
        artifact_type='training_data',
        seed=42, temperature=0.7, max_new_tokens=150
    )
}
```

### Evaluation Scripts
Add metadata and statistics to output:
```python
from utils.eval_statistics import paired_comparison_analysis
from utils.provenance_helper import create_artifact_metadata

# Run evaluation...

# Statistical analysis
stats = paired_comparison_analysis(
    base_results, sft_results,
    labels=('base', 'sft'),
    instruction_types=types,
    fdr=0.10
)

# Output with metadata and statistics
output = {
    'metadata': create_artifact_metadata(...),
    'results': per_example_results,
    'summary': {'base_acc': ..., 'sft_acc': ...},
    'statistics': stats
}
```

### Session Start
```bash
cd /workspace/MaximalCAI
python3 scripts/create_session_manifest.py
# Warns if git is dirty
```

---

## Review Focus Areas

### Critical Questions

1. **Statistical Validity**:
   - Are these the right tests for paired binary outcomes?
   - Is FDR=0.10 appropriate (vs FWER control)?
   - Is N=1000 sufficient for per-type analysis?
   - Should we use exact McNemar (small n) vs asymptotic?

2. **Provenance Sufficiency**:
   - Are we capturing enough metadata?
   - Are we capturing too much (bloat)?
   - Should session manifest be auto-updated by scripts?
   - How to handle artifacts_generated list?

3. **Integration Complexity**:
   - Is integration into existing scripts straightforward?
   - Do we need helper functions beyond `create_artifact_metadata()`?
   - Should we auto-capture more from CleanModelLoader?

4. **Production Readiness**:
   - Are these utilities complete enough for production?
   - What edge cases might we encounter on GPU?
   - What documentation is missing?

### Code Quality

1. **Correctness**:
   - Statistical formulas match references?
   - Edge cases handled (empty data, extreme proportions)?
   - Error messages clear?

2. **Usability**:
   - APIs intuitive?
   - Docstrings sufficient?
   - Examples clear?

3. **Performance**:
   - Bootstrap (10k samples) fast enough?
   - Git subprocess calls acceptable?

### Documentation

1. **IMPLEMENTATION_REGISTRY**:
   - New utilities documented clearly?
   - Usage examples sufficient?
   - Cross-references correct?

2. **Task Files**:
   - Completion notes comprehensive?
   - Rationale for deferrals clear?
   - Next steps actionable?

---

## Expected Benefits

### Evaluation Statistics
- **Publication quality**: Can report p-values, effect sizes, CIs in paper
- **Correct inference**: Paired tests account for correlation in data
- **Multiple testing**: BH correction prevents false positives
- **Effect size**: Cohen's h quantifies practical significance beyond p-values

### Provenance Tracking
- **Reproducibility**: Can recreate any artifact from git commit
- **Verification**: Can verify contamination controls in all data
- **Debugging**: Can trace issues back to specific runs/configs
- **Comparison**: Can filter/query artifacts by model, params, etc.

### Requirements Management
- **Speed**: Single command vs many pip installs (~5-10 min saved)
- **Reproducibility**: Version bounds documented
- **Documentation**: Clear list of all dependencies

---

## Risks and Mitigations

### Risk: Statistical tests incorrect
- **Mitigation**: Unit tests validate against known values and scipy
- **Mitigation**: Can verify against R/statsmodels for small test cases
- **Mitigation**: Codex review of formulas and implementation

### Risk: Provenance overhead slows generation
- **Mitigation**: Git calls are fast (subprocess overhead minimal)
- **Mitigation**: Metadata is small (<1KB per record)
- **Mitigation**: Can measure overhead on first production run

### Risk: Integration into scripts is complex
- **Mitigation**: APIs designed to be simple (one function call)
- **Mitigation**: Examples provided in task files and docstrings
- **Mitigation**: Can iterate based on first integration experience

---

## Success Criteria

This review is successful if:

1. ✅ Statistical approach validated (correct tests, FDR appropriate, N sufficient)
2. ✅ Provenance design validated (enough metadata, not too much)
3. ✅ No critical bugs or edge cases identified
4. ✅ Documentation sufficient for integration
5. ✅ Green light to begin GPU production work with these utilities

## Timeline

- **Review deadline**: 2025-10-05 (24 hours)
- **Critical path**: This blocks $300 GPU production work
- **Next step after approval**: Resume H100 pod, begin Session 1 data generation

---

## Files to Review

**Core utilities** (high priority):
- `scripts/utils/eval_statistics.py` (603 lines)
- `scripts/utils/provenance_helper.py` (345 lines)
- `scripts/create_session_manifest.py` (130 lines)

**Tests** (important):
- `tests/test_eval_statistics.py` (421 lines)

**Documentation** (review for clarity):
- Task completion notes in `tasks/claude_code/completed/`
- Updated sections in `docs/IMPLEMENTATION_REGISTRY.md`

**Supporting files** (optional):
- `requirements.txt`, `requirements-dev.txt`
- Updated `scripts/setup_runpod_environment.sh`
- Updated `docs/RUNPOD_H100_SESSION.md`

---

## Questions for Reviewers

1. **Codex**: Statistical approach sound? Any issues with test selection, correction method, or N=1000 target?

2. **Gemini**: Provenance design sufficient? Missing any critical metadata fields?

3. **Both**: Ready to proceed with GPU production work using these utilities?

4. **Both**: Any critical bugs or edge cases we should address before production?

5. **Both**: Integration complexity acceptable? Should we provide more helper functions?

---

**Ready for review. This is the final checkpoint before $300 GPU production work begins.**
