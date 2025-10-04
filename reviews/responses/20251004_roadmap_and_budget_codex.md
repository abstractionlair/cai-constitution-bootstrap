# Review Response: Roadmap and Budget Analysis

**Reviewer**: codex
**Date**: 2025-10-04
**Request**: Big-picture roadmap review and efficient frontier analysis
**Budget Decision**: $300 approved

---

## Summary

Codex reviewed the overall path and provided:
1. ✅ Validation that overall approach is solid
2. 🎯 Identified key risks (statistics, provenance persistence, cost/time pressure)
3. 📊 Efficient frontier analysis ($10-$300 budgets)
4. 📋 Detailed $300 execution plan (~165-175 GPU hours)

**Key insight**: Current $20 cap is too low for publication-quality results. $300 enables strong paired statistics (N=800-1200), limited ablations, and reproducibility.

---

## What's Strong (Per Codex)

✅ **Process**:
- Clear milestones and blockers
- Migration completed and verified
- Tight DRY policy, verification scripts
- RunPod session plan with phased goals
- Explicit success targets, cost awareness

✅ **Technical**:
- Staged SFT→DPO pipeline
- Strong contamination controls
- Disciplined documentation

---

## Key Risks Identified

### 1. Statistical Rigor (P0)
**Issue**: Current eval N=12 won't support publication claims
**Impact**: Can't make credible significance claims

**Required**:
- N ≥ 800-1200 (paired design)
- McNemar tests with Benjamini-Hochberg correction
- Wilson CIs + Cohen's h effect sizes
- Deterministic decoding (temperature=0) for baselines

**Status**: Not yet wired into Stage 3/4 scripts

### 2. Provenance Persistence (HIGH)
**Issue**: Provenance captured but not persisted to artifacts
**Impact**: Can't verify contamination controls in historical data

**Required**:
- Per-record metadata (model, loader version, seeds, params)
- Per-evaluation metadata (decoding params, versions, checksums)
- Leakage prevention (hash-based dedup, overlap=0)

**Status**: Design complete (PROVENANCE_PERSISTENCE_RECOMMENDATIONS.md), implementation pending

### 3. Cost/Time Pressure (MEDIUM)
**Issue**: Original $20 budget insufficient for credible results
**Impact**: Risk of underpowered evaluation or rushed runs

**Original plan**: 10k SFT + 10-30k DPO pairs on 32B model
**Reality**: Would yield N≈200-300 eval, CI≈±5-6%, no ablations

**Resolution**: $300 budget approved

### 4. P0 Evaluation Bug (TRACKED)
**Issue**: Concurrent model loading in evaluate_capability_differentiation.py
**Impact**: OOM and incorrect results

**Status**: Sequential version exists (evaluate_capability_differentiation_sequential.py)
**Action**: Verify all eval scripts use sequential loading before baseline

---

## Efficient Frontier Analysis

Codex provided compute/stats tradeoffs across budgets:

| Budget | GPU Hours | N (eval) | Overall CI | Outcome |
|--------|-----------|----------|------------|---------|
| $10 | ~6h | 150-200 | ±6-8% | Feasibility only, weak stats |
| $20 | ~11h | 200-300 | ±5-6% | SFT win, basic significance, no DPO |
| $50 | ~29h | 300-500 | ±3.5-4.5% | End-to-end SFT→DPO, credible overall |
| $100 | ~58h | 500-800 | ±3% | Publication-quality Stage 1 |
| $150 | ~86h | 800-1200 | ±2-2.5% | Paper-ready with ablations |
| **$300** | **~172h** | **800-1200** | **±2-2.5%** | **Strong paper + robustness** |

**Recommendation**: $300 enables publication-quality results with ablations and reproducibility checks.

---

## $300 Budget Plan (Approved)

### Compute Allocation (~165-175h)

- **Baseline eval**: 1-2h (N=800-1200, deterministic)
- **SFT data gen**: 10-14h (15-20k examples)
- **SFT train**: 12-18h (QLoRA, 3-5 epochs, early stop)
- **Preference pairs**: 10-14h (BoN k=3-4, 20-30k pairs)
- **DPO train**: 12-18h (β≈0.1-0.2, 2-3 epochs)
- **Core evals**: 3-5h (base/SFT/DPO, N=1000)
- **Ablation A (β)**: 11-16h (train + eval)
- **Ablation B (BoN k)**: 16-24h (pairs + train + eval)
- **Robustness buffer**: 25-35h (retries, OOMs)

**Total**: ~160-175h @ $1.74/hr = ~$278-305

### Execution Phases

**Phase 0: Readiness Gates** (local, no GPU)
- ✅ Verify migration complete
- ⏳ Lock eval protocol (N, stratification, seeds)
- ⏳ Enable provenance logging
- ⏳ Define early-stop thresholds

**Phase 1: Baseline** (~1-2h)
- Run base eval (N=800-1200, temperature=0, greedy)
- Stratified by instruction type
- Save full JSON with metadata

**Phase 2: SFT Data + Train** (~22-32h)
- Generate 15-20k SFT examples with provenance
- Train SFT (QLoRA, 3-5 epochs, early stop)
- Intermediate eval

**Phase 3: Preference Pairs + DPO** (~22-32h)
- Generate 20-30k pairs (BoN k=3-4, margin filter)
- Train DPO (β≈0.1-0.2, 2-3 epochs, early stop)

**Phase 4: Core Evaluations** (~3-5h)
- Evaluate base/SFT/DPO on identical N=1000 set (paired)
- Deterministic decoding
- Full metadata per result

**Phase 5: Ablations** (~27-40h)
- **A: β ablation** (0.3 vs 0.1-0.2, reuse pairs)
- **B: BoN ablation** (k=2 vs 4 on 10-15k subset)
- Optional: seed robustness check

**Phase 6: Analysis + Reporting** (local)
- Statistical tests (McNemar + BH correction)
- Effect sizes (Cohen's h) + CIs (Wilson, bootstrap)
- Error analysis
- Automation metrics

### Statistical Design

**Primary endpoint**: Instruction-following success rate (binary)

**Design**:
- Paired comparisons (identical items): base↔SFT, SFT↔DPO, base↔DPO
- N = 800-1200, stratified by instruction type

**Tests**:
- McNemar for paired binary outcomes (overall + per-type)
- Benjamini-Hochberg correction (FDR=0.10) across types

**Effect sizes & intervals**:
- Cohen's h (overall + per-type)
- Wilson 95% CIs for proportions
- Bootstrap CIs for deltas

**Power targets**:
- At N=1000, p≈0.7-0.9: overall CI ≈ ±2.5-3.0%
- Expected SFT lift: +40-60pp over base
- Expected DPO lift: +10-20pp over SFT on constraints

### Early-Stop Gates

**Contamination**:
- Any sentinel or token-ID check fails → STOP
- Fix loader or prompt path before continuing

**SFT**:
- If dev success after epoch 1 < baseline + 10pp → PAUSE
- Inspect data quality/hyperparameters

**DPO**:
- If improvement over SFT < +5pp after epoch 1 → PAUSE
- Inspect pair margins/diversity

**Compute**:
- If projected hours exceed budget by >10% → skip ablation B

---

## Recommendations (Codex)

### 1. Evaluation Design (P0)
- ⏳ Lock protocol: N=1000, paired design, stratification
- ⏳ Wire McNemar + BH into eval scripts
- ⏳ Add Wilson CIs and Cohen's h to outputs
- ⏳ Default deterministic (temperature=0) for baselines

**Action**: Create task for eval statistics upgrade

### 2. Provenance Persistence (HIGH)
- ⏳ Implement helper utility (provenance_helper.py)
- ⏳ Update data generation scripts
- ⏳ Update evaluation scripts
- ⏳ Add session manifest to RunPod workflow

**Action**: Already designed (PROVENANCE_PERSISTENCE_RECOMMENDATIONS.md), needs implementation

### 3. Data Integrity (HIGH)
- ⏳ Hash-based dedup across SFT/pairs/held-out
- ⏳ Log overlap counts (must be 0)
- ⏳ Per-record contamination flags in metadata

**Action**: Add to data generation scripts

### 4. Documentation Alignment (MEDIUM)
- ✅ Migration status docs aligned (completed this session)
- ⚠️ Methodology change notice not needed (no old results being used)
- ⏳ Update PROJECT_STATUS.md (still shows 2025-10-03)

### 5. Automation Metrics (RECOMMENDED)
- ⏳ Track: % auto-executed, % examples without edits, human-minutes per 1k
- ⏳ Log QC pass rates

**Action**: Add to data generation and eval outputs

---

## Implementation Priority

### P0 (Before GPU Work)
1. ⏳ Close P0 eval bug (verify all scripts use sequential loading)
2. ⏳ Lock eval protocol (N=1000, tests, CIs, effect sizes)
3. ⏳ Implement provenance persistence (at minimum: helper utility + data gen)
4. ⏳ Enable session manifest logging
5. ✅ Run smoke test on GPU (~$0.30) - script ready

### P1 (During GPU Work)
6. ⏳ Early-stop gates in training scripts
7. ⏳ Hash-based dedup and leakage checks
8. ⏳ Automation metrics tracking

### P2 (Analysis Phase)
9. ⏳ Statistical analysis script (McNemar, BH, CIs, effect sizes)
10. ⏳ Error analysis and automation report
11. ⏳ Reproducibility appendix

---

## Proposed Session Strategy

Codex suggests 3 GPU sessions:

**Session 1** (~40-55h, ~$70-96):
- Baseline eval
- SFT data gen (~10-12k)
- SFT train (3-4 epochs)
- Interim eval

**Session 2** (~55-70h, ~$96-122):
- Complete SFT data (~5-8k more)
- Preference pairs (20-30k)
- DPO train
- Core eval (N=1000)

**Session 3** (~55-65h, ~$96-113):
- Ablation A (β)
- Ablation B (BoN k)
- Final evals
- Analysis and reports

**Total**: ~150-190h, ~$262-332

---

## Action Items

### Immediate (This Session)
1. ✅ Review Codex response
2. ⏳ Create tasks for P0 items:
   - Eval statistics upgrade (P0)
   - Provenance persistence implementation (HIGH)
   - Data integrity checks (HIGH)
3. ⏳ Update PROJECT_STATUS.md
4. ⏳ Update ROADMAP.md with $300 budget and session plan

### Before GPU Session 1
5. ⏳ Implement provenance helper utility
6. ⏳ Update data generation with provenance
7. ⏳ Lock eval protocol (wire in statistics)
8. ⏳ Verify all eval scripts use sequential loading
9. ⏳ Add early-stop gates to training scripts
10. ⏳ Run smoke test on GPU

### During GPU Sessions
11. ⏳ Follow 3-session plan
12. ⏳ Monitor early-stop gates
13. ⏳ Track automation metrics
14. ⏳ Verify provenance in all artifacts

---

## Overall Assessment

✅ **Path validated**: Staged SFT→DPO pipeline is sound
✅ **Budget justified**: $300 enables publication-quality results
⚠️ **Statistics gap**: Need to wire in proper tests/CIs before GPU work
⚠️ **Provenance gap**: Need to implement persistence before production data
✅ **Process strong**: DRY policy, verification, documentation in place

**Recommendation**: Complete P0 items (eval statistics, provenance persistence, eval bug verification) before first GPU session. Budget is sufficient for strong paper.

---

## Questions Resolved

1. **Is overall path sound?** → Yes, with statistical rigor upgrade
2. **What budget is needed?** → $300 for publication-quality (vs $20 for weak feasibility)
3. **What's achievable at $300?** → End-to-end Stage 1 with N=1000, paired tests, CIs, effect sizes, 2 ablations, robustness
4. **What's blocking GPU work?** → Eval statistics implementation, provenance persistence, eval bug verification

**Next**: Convert recommendations to tasks and implement P0 items.
