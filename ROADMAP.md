# Project Roadmap

**Constitutional AI Bootstrap Experiment**

Progress markers: ✅ Done | ⏳ In Progress | 📋 Todo

---

## Milestone 1: Foundation Infrastructure ✅ DONE

**Goal**: Establish project structure, documentation, and development workflow

- [x] Project structure and file organization
- [x] Documentation system (DAG architecture)
- [x] Anti-re-implementation safeguards (IMPLEMENTATION_REGISTRY, KNOWN_BUGS_AND_FIXES)
- [x] File organization standards
- [x] Review protocol and workflow
- [x] Task tracking system
- [x] Git repository setup

**Completed**: 2025-10-03

---

## Milestone 2: Stage 1 Pipeline Implementation ⏳ DOING

**Goal**: Build complete SFT→DPO training pipeline for explicit instruction following

### Core Pipeline ✅
- [x] Data generation script (`generate_stage1_sft_data.py`)
- [x] SFT training script (`train_stage1_sft.py`)
- [x] Preference pair generation (`generate_diverse_negatives.py`, `create_preference_pairs_improved.py`)
- [x] DPO training script (`train_stage1_dpo_improved.py`)
- [x] Evaluation script (`evaluate_stage1_comprehensive.py`)
- [x] Utility modules (CompletionStylePrompts, model_loader, data_validation)

### Data Generation ✅
- [x] 200 SFT training examples generated
- [x] 188 preference pairs created
- [x] 130 held-out test instructions
- [x] Few-shot completion prompting implemented
- [x] Chat template contamination fix applied
- [x] Base model completion mode verified (no instruction template leakage)

### Critical Fixes ⏳
- [x] Chat template contamination documented and fixed (BASE_MODEL_TRUTH.md)
- [x] Base model completion mode implementation (CompletionStylePrompts)
- [x] Few-shot prompting architecture implemented
- [x] Loss masking for SFT implemented
- [ ] P0: Evaluation memory management bug
- [ ] P0: Statistical rigor improvements
- [ ] P1: Data quality verification

### External Validation ✅
- [x] Gemini technical review (2025-09-12)
- [x] Codex methodology review (2025-09-12)
- [x] Review feedback converted to tasks

### Deployment Preparation 📋
- [ ] Fix P0 evaluation bug
- [ ] Verify all critical fixes applied
- [ ] Test pipeline locally (dry run)
- [ ] Deploy to RunPod
- [ ] Verify GPU setup and environment

**Target Completion**: 2025-10-15

---

## Milestone 3: Stage 1 Baseline & Training 📋 TODO

**Goal**: Run baseline assessment and complete first full training run

### Evaluation Framework 📋
- [ ] Write instruction-following eval (self-contained, reviewable)
- [ ] Test eval on base model (establish baseline ~10-30% expected)
- [ ] Verify no chat template contamination in baseline
- [ ] Document eval methodology and metrics

### Baseline Assessment 📋
- [ ] Run full evaluation on base model (Qwen-2.5-32B)
- [ ] Document base model capabilities
- [ ] Save baseline results for comparison

### Full Training Run 📋
- [ ] Generate full SFT dataset (5-10k examples for 32B model)
- [ ] Train SFT model
- [ ] Generate preference pairs from SFT model with improvements:
  - [ ] Use Best-of-N (BoN) sampling (k=2-4 candidates per prompt)
  - [ ] Apply confidence filtering (high-margin pairs only)
  - [ ] Include diverse hard negatives (refusals, hallucinations, format violations)
  - [ ] Target 10-30k high-quality pairs (10k minimum for clear win)
- [ ] Train DPO model from SFT checkpoint (β ≈ 0.1-0.3)
- [ ] Save LoRA adapters
- [ ] Optional: Online refresh (regenerate with DPO model, relabel, retrain)

### Validation 📋
- [ ] Apply eval to SFT model
- [ ] Apply eval to DPO model
- [ ] Compare all three models (base, SFT, DPO)
- [ ] Verify performance improvements
- [ ] Document training time and costs

**Target Completion**: 2025-10-22

---

## Milestone 4: Stage 1 Results & Analysis 📋 TODO

**Goal**: Analyze results and prepare for publication

### Statistical Analysis 📋
- [ ] Implement proper statistical tests
- [ ] Compare models with significance testing
- [ ] Analyze error patterns
- [ ] Document failure modes

### Model Evaluation 📋
- [ ] Comprehensive evaluation on held-out test set
- [ ] Compare SFT-only vs. SFT→DPO
- [ ] Generate evaluation report
- [ ] Create visualizations

### Documentation 📋
- [ ] Write methodology documentation
- [ ] Document all hyperparameters
- [ ] Record training costs
- [ ] Create reproducibility guide

### Success Criteria 📋
- [ ] Base model: ~10-30% instruction following
- [ ] SFT model: ~70-80% instruction following
- [ ] SFT+DPO model: ~90-95% instruction following
- [ ] Statistical significance demonstrated
- [ ] No data leakage confirmed

**Target Completion**: 2025-10-29

---

## Milestone 5: Stage 2 Planning 📋 TODO

**Goal**: Design Stage 2 (Implicit Instructions) based on Stage 1 learnings

### Design 📋
- [ ] Review Stage 1 results and lessons learned
- [ ] Design Stage 2 data generation approach
- [ ] Plan how Stage 1 model will generate Stage 2 data
- [ ] Define Stage 2 success criteria

### Preparation 📋
- [ ] Merge Stage 1 LoRA adapters
- [ ] Test Stage 1 model for Stage 2 data generation
- [ ] Create Stage 2 specifications

**Target Completion**: 2025-11-05

---

## Stages 3-6 📋 TODO

**High-level placeholders** (detailed planning after Stage 2 completes):

### Stage 3: Generation Tasks 📋
**Goal**: Learn to generate examples of specific types
**Depends on**: Stage 2 completion

### Stage 4: Evaluation Tasks 📋
**Goal**: Learn to judge and evaluate text
**Depends on**: Stage 3 completion

### Stage 5: Revision Tasks 📋
**Goal**: Learn to improve existing text
**Depends on**: Stage 4 completion

### Stage 6: Constitutional Integration 📋
**Goal**: Full Constitutional AI with all principles
**Depends on**: Stage 5 completion

---

## Future Research Directions 📋 TODO

**Exploration beyond initial 6-stage plan** (detailed planning after Stage 6):

### Multi-Agent Reasoning 📋
**Core Idea**: Models already "understand" roles like PhD advisor, Socratic tutor, skeptical reviewer. Use minimal post-training or even prompting to have models embody these roles and interact.

**Hypothesis**: Reasoning might emerge from interaction patterns between models in different roles, rather than requiring extensive RL to learn reasoning from scratch.

**Potential Benefits**:
- More sample-efficient than pure RL approaches
- Leverages latent capabilities already in base models
- Transparent reasoning traces (can inspect advisor/student interactions)
- Naturally generates high-quality reasoning examples

**Exploration Steps**:
- [ ] Experiment with role-based prompting (advisor, student, critic)
- [ ] Test if interaction produces reasoning-like behavior
- [ ] Compare minimal post-training vs. pure prompting
- [ ] Evaluate whether separate models needed or single model can play roles

### Reasoning Distillation 📋
**Core Idea**: Use multi-agent reasoning system to generate training data for single-model reasoners.

**Pipeline**:
1. Multi-agent system collaborates to solve problems (with natural error correction)
2. Generate high-quality, vetted reasoning traces from interactions
3. Use traces as training data to distill reasoning into single model
4. Potentially bootstrap by adding trained model back into ensemble

**Potential Benefits**:
- Avoids expensive RL for reasoning discovery
- Built-in quality control (adversarial agents catch errors)
- Transparent training signal (can inspect what patterns are taught)
- Iterative improvement through bootstrapping

**Exploration Steps**:
- [ ] Design multi-agent interaction protocol
- [ ] Generate reasoning traces from agent interactions
- [ ] Train single model on traces
- [ ] Evaluate reasoning quality vs. traditional approaches
- [ ] Test bootstrapping: trained model joining ensemble

**Depends on**: Completion of Stages 1-6 (foundation capabilities needed)

---

## Budget Tracking

| Milestone | Estimated Cost | Actual Cost | Status |
|-----------|----------------|-------------|--------|
| M1: Foundation | $0 | $0 | ✅ Done |
| M2: Pipeline | $0 (dev only) | $0 | ⏳ Doing |
| M3: Training | $20 | - | 📋 Todo |
| M4: Analysis | $5 | - | 📋 Todo |
| M5-M6: Future Stages | $125 | - | 📋 Todo |
| **Total** | **$150** | **$0** | - |

---

## Key Risks & Mitigations

### Technical Risks
- **Chat template contamination**: ✅ Mitigated (documented in BASE_MODEL_TRUTH.md, fixed in code)
- **Memory issues on GPU**: ⏳ Being addressed (P0 evaluation bug)
- **Re-implementing existing code**: ✅ Mitigated (IMPLEMENTATION_REGISTRY)
- **Reproducing old bugs**: ✅ Mitigated (KNOWN_BUGS_AND_FIXES)
- **Training instability with RL**: ✅ Avoided (using DPO instead of PPO/GRPO)
- **Sample inefficiency**: ✅ Addressed (BoN sampling, confidence filtering, hard negatives)

### Process Risks
- **Context loss between sessions**: ✅ Mitigated (comprehensive documentation)
- **Unclear project state**: ✅ Mitigated (this roadmap + PROJECT_STATUS)

---

**Last Updated**: 2025-10-03

See `/status/PROJECT_STATUS.md` for current narrative and context.
