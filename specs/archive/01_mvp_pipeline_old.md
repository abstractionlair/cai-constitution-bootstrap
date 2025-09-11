# Specification: Qwen-2.5-32B CAI MVP Pipeline

## Goal
Establish a working Constitutional AI pipeline with Qwen-2.5-32B that generates, critiques, and revises responses to create preference pairs for DPO training.

## Context
- Model: Qwen/Qwen2.5-32B (base model)
- Hardware: RunPod A100 SXM 80GB (plenty of memory!)
- Memory: 32B model at 4-bit ≈ 16GB, leaving 64GB headroom
- Framework: Unsloth for efficient QLoRA training
- Opportunity: Can experiment with larger batch sizes or different quantization

## Milestone Progression

### Milestone 0: Single Example Test (30 minutes)
**Goal**: Verify the self-critique mechanism works
1. Generate ONE instruction/question
2. Generate initial answer (A0)
3. Select ONE constitutional principle
4. Critique A0 against that principle
5. Generate revised answer (A1)
6. Create ONE preference pair (chosen=A1, rejected=A0)
7. Run 1-step DPO training (just to verify no crashes)
8. **Success Criteria**: Pipeline completes, critique is meaningful

### Milestone 1: Small Batch Test (1 hour)
**Goal**: Validate quality at small scale
1. Generate 10 diverse instructions
2. For each: answer → critique (2 principles) → revise
3. Create 10 preference pairs
4. Train DPO for ~10 steps
5. Evaluate: Does model prefer revised answers?
6. **Success Criteria**: >70% meaningful critiques, training converges

### Milestone 2: MVP Scale (2-3 hours)
**Goal**: First real training run
1. Generate 100 diverse instructions
2. Complete full pipeline for all 100
3. Train DPO for 100+ steps
4. Basic evaluation metrics
5. **Success Criteria**: Clear preference for revised answers

### Milestone 3: Production Scale (5+ hours)
**Goal**: Full experiment
1. Generate 5,000+ instructions
2. Add Llama Guard filtering
3. Multiple epochs of DPO training
4. Complete benchmark evaluation
5. **Success Criteria**: Measurable improvement on safety/helpfulness

## Technical Details

### Quantization Strategy
```python
# For Training - QLoRA approach
from unsloth import FastLanguageModel

model, tokenizer = FastLanguageModel.from_pretrained(
    "Qwen/Qwen2.5-32B",
    dtype=torch.bfloat16,
    load_in_4bit=True,  # Use 4-bit for base model
    max_seq_length=4096
)

# LoRA adapters will be in bf16/fp16
# This gives us best memory efficiency while maintaining quality
```

**Why 4-bit?**
- Proven to work well with QLoRA
- Allows larger batch sizes
- We can always test 8-bit or fp16 later (we have 80GB!)

### Generation Settings
- Temperature: 0.7 for tasks/answers, 0.3 for critiques
- Max tokens: 500 for answers, 300 for critiques
- Batch size: Start with 1, can increase with 80GB

### DPO Configuration
- LoRA rank: 32
- LoRA alpha: 64
- Learning rate: 5e-6
- Beta (DPO temp): 0.1
- Training steps: Scale with data (1 for M0, 10 for M1, 100+ for M2)

## Constitutional Principles
Use the 15 principles from `constitution.yaml`:
- Helpful and accurate information
- Avoid harmful/dangerous/illegal advice
- Respect privacy
- Acknowledge uncertainty
- [etc...]

## Data Format
Each example should have:
```json
{
  "instruction": "User's question or task",
  "initial_answer": "Model's first attempt",
  "principle": "Constitutional principle used",
  "critique": "What's wrong with initial answer",
  "revised_answer": "Improved version",
  "preference_pair": {
    "prompt": "instruction",
    "chosen": "revised_answer",
    "rejected": "initial_answer"
  }
}
```

## Implementation Structure
```
cai_experiment/
├── scripts/
│   ├── test_single.py        # Milestone 0: One example
│   ├── test_batch.py         # Milestone 1: 10 examples
│   ├── generate_mvp.py       # Milestone 2: 100 examples
│   ├── generate_full.py      # Milestone 3: 5k+ examples
│   └── train_dpo.py          # DPO training (scales with data)
├── data/
│   ├── single/               # Milestone 0 output
│   ├── batch/                # Milestone 1 output
│   ├── mvp/                  # Milestone 2 output
│   └── full/                 # Milestone 3 output
└── checkpoints/
    └── [milestone_name]/     # Saved models
```

## Execution Plan

### Start Here (Milestone 0):
1. SSH into RunPod
2. Clone repo
3. Install dependencies
4. Run `test_single.py`
5. Verify output quality
6. Time: ~30 minutes, Cost: ~$0.87

### Then Scale Up:
- M1: ~1 hour, ~$1.74
- M2: ~3 hours, ~$5.22
- M3: As needed for full experiment

## Key Decisions

### Why Start Small?
- Verify the mechanism works before scaling
- Catch issues early (cheaper to fix)
- Build confidence in the approach
- Get early signal on quality

### Why QLoRA?
- Proven technique with excellent results
- Memory efficient (important even with 80GB)
- Fast training
- Easy to implement with Unsloth

### Why These Milestones?
- Each builds on the previous
- Early validation saves money
- Clear go/no-go gates
- Natural debugging progression

## Success Metrics

### Milestone 0:
- Pipeline runs without errors
- Critique identifies real issues
- Revision addresses the critique

### Milestone 1:
- 7/10 critiques are meaningful
- Revisions improve quality
- DPO loss decreases

### Milestone 2:
- Model prefers revised answers >80% of time
- Quality metrics improve
- No catastrophic forgetting

### Milestone 3:
- HarmBench scores improve
- MT-Bench scores maintained or improved
- Publication-ready results
