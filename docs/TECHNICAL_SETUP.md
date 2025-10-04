# Technical Setup

This document contains the technical decisions, infrastructure details, and implementation specifics for the project.

---

## Model Selection

**Base Model**: Qwen-2.5-32B (base version, not instruction-tuned)

**Why Qwen?**
- Strong base capabilities
- 32B parameters (good balance of capability and cost)
- Not instruction-tuned (lets us control the entire post-training process)
- Open weights and license

---

## Hardware & Infrastructure

**Training Hardware**: RunPod A100 SXM 80GB GPU
- Cost: $1.74/hour
- 80GB VRAM allows training 32B models with 4-bit quantization
- On-demand availability (no long-term commitment)

**Development**: Local MacBook for code development and testing

**File Transfer**: SSH pipes (not scp) for reliable large file transfers to/from RunPod

See `/status/RUNPOD_STATUS.md` for current infrastructure state and connection details.

---

## Training Framework

**Method**: QLoRA (4-bit quantized) + DPO (Direct Preference Optimization)

**Libraries**:
- **Unsloth**: Efficient training with memory optimization
- **TRL** (Transformer Reinforcement Learning): DPO implementation
- **PyTorch**: Base framework
- **Transformers**: Model loading and inference

**Quantization Strategy**:
- 4-bit during training (QLoRA) - memory efficient
- 8-bit or 16-bit for inference/evaluation - quality
- Base model in fp16 for few-shot prompting

---

## Safety & Filtering

**Constitutional Principles**: HHH-focused (Helpful, Harmless, Honest)
- Defined in `/constitution.yaml`
- Used for critique generation and preference labeling

**Content Filtering**: Llama Guard 3-8B
- Filters harmful content from generated data
- Runs during data generation pipeline
- Safety-focused categories enabled

**Evaluation**: Custom benchmarks + capability differentiation tests

---

## Data Generation Strategy

**Completion-Style Prompting**: 3-4 random examples + target → base model completes
- Avoids instruction-template contamination (see BASE_MODEL_TRUTH.md)
- Uses base model's completion capabilities directly
- Critical for Stage 1 before instruction-following is taught

**Progressive Stages**: Each stage generates training data for the next
- Stage 1: Base model generates explicit instruction examples
- Stage 2: Stage 1 model generates implicit instruction examples
- Stage 3-6: Similar progressive approach

---

## Key Technical Innovations

### Chat Template Contamination Prevention
**Problem**: Qwen's tokenizer auto-applies instruction templates during tokenization, making base model appear instruction-tuned when it's not.

**Solution**:
- Use `add_generation_prompt=False` during base model prompting
- Documented with detection tests in `/docs/BASE_MODEL_TRUTH.md`
- We discovered this bug multiple times—now properly documented

### Anti-Re-Implementation System
**Problem**: Long project spans multiple sessions, leading to re-implementing existing features and reproducing old bugs.

**Solution**:
- **IMPLEMENTATION_REGISTRY.md**: Catalog of all 40+ scripts (check before implementing)
- **KNOWN_BUGS_AND_FIXES.md**: Complete bug history (check before debugging)

### Few-Shot Completion Prompting
**Why**: Base models don't follow instructions reliably before instruction-tuning.

**Approach**: Show 3-4 random examples of desired pattern, then let model complete.

**Result**: Generates diverse, high-quality training data without instruction-following capability.

---

## Budget Breakdown

| Phase | GPU Hours | Cost | Status |
|-------|-----------|------|--------|
| Foundation & Implementation | 0 | $0 | ✅ Done (local) |
| Stage 1 Training (~5 epochs) | ~8 hours | ~$14 | 📋 Todo |
| Stage 1 Evaluation | ~6 hours | ~$10 | 📋 Todo |
| Stages 2-6 (estimated) | ~70 hours | ~$120 | 📋 Todo |
| **Total** | **~84 hours** | **~$150** | - |

**Cost Control**:
- Development done locally (free)
- RunPod only for training/evaluation (charged per second)
- 4-bit quantization reduces memory requirements
- Efficient scripts minimize GPU time

---

## Reproducibility Measures

**Random Seeds**: All generation and training scripts use fixed seeds
- Data generation: seed=42
- Training: seed=42
- Evaluation: seed=42 (where applicable)

**Version Tracking**: Log all package versions in run directories
- Transformers version
- Unsloth version
- TRL version
- PyTorch version

**Complete Configs**: Save all hyperparameters and configs
- Data generation parameters
- Training hyperparameters
- Model configurations
- Constitutional principles used

**Deterministic Operations**: Where possible, enable deterministic algorithms

---

## Project Structure

```
MaximalCAI/
├── scripts/                   # Implementation (40+ files)
│   ├── stage1_*.py           # Stage 1 pipeline
│   ├── stage2_*.py           # Stage 2 pipeline (future)
│   ├── utils/                # Shared utilities
│   └── [other scripts]
│
├── data/                      # Generated datasets
├── artifacts/                 # Trained model checkpoints
├── checkpoints/               # Intermediate training states
├── logs/                      # Training logs
├── runs/                      # Per-run directories with full configs
│
├── specs/                     # Design specifications
├── docs/                      # Permanent documentation
├── status/                    # Current state
├── tasks/                     # Work tracking
├── reviews/                   # Review system
└── archive/                   # Historical documents
```

See `/docs/STANDARDS.md` for complete file organization standards.

---

## Development Workflow

1. **Local Development**: Write and test code locally
2. **Transfer to RunPod**: Use SSH pipes to copy scripts/data
3. **Remote Execution**: Run training/evaluation on RunPod GPU
4. **Transfer Results**: Copy artifacts and logs back to local
5. **Analysis**: Analyze results locally, plan next iteration

See `/docs/STANDARDS.md#git-workflow` for version control practices.

---

**For More Details**:
- Infrastructure: `/status/RUNPOD_STATUS.md`
- Implementation: `/docs/IMPLEMENTATION_REGISTRY.md`
- Known Issues: `/docs/KNOWN_BUGS_AND_FIXES.md`
- Base Model Quirks: `/docs/BASE_MODEL_TRUTH.md`
