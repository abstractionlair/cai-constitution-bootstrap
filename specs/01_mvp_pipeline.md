# Specification: Qwen-2.5-32B CAI MVP Pipeline

## Goal
Establish a working Constitutional AI pipeline with Qwen-2.5-32B that generates, critiques, and revises responses to create preference pairs for DPO training.

## Context
- Model: Qwen/Qwen2.5-32B (base model)
- Hardware: RunPod A100 40GB instance
- Memory constraint: 32B model at 4-bit ≈ 16GB, leaving headroom for generation
- Framework: Unsloth for efficient QLoRA loading

## Requirements

### Functional Requirements
1. Load Qwen-2.5-32B base model with 4-bit quantization
2. Implement self-instruct task generation (100 diverse prompts)
3. Generate initial answers for each prompt
4. Critique each answer against 2 random constitutional principles
5. Generate revised answers addressing critiques
6. Format as preference pairs (revised=chosen, original=rejected)
7. Run minimal DPO training as validation

### Constitutional Principles
Use standard 15 principles (HHH-focused) from constitution.yaml

### Success Criteria
- Pipeline completes 100 examples in <2 hours
- Manual inspection shows >70% meaningful critiques
- DPO training runs without OOM errors
- Model shows preference for revised answers after training

## Technical Details

### Model Loading (Unsloth)
```python
from unsloth import FastLanguageModel

model, tokenizer = FastLanguageModel.from_pretrained(
    "Qwen/Qwen2.5-32B",
    dtype=torch.bfloat16,
    load_in_4bit=True,
    max_seq_length=4096
)
FastLanguageModel.for_training(model)  # Enable training optimizations
```

### Generation Settings
- Temperature: 0.7 for creativity, 0.3 for critiques
- Max tokens: 500 for answers, 300 for critiques
- Batch size: 1 (memory constraint)

### DPO Configuration
- LoRA rank: 32
- LoRA alpha: 64
- Learning rate: 5e-6
- Beta (DPO temp): 0.1
- Training steps: 100 (MVP only)

## Deliverables
1. `setup_environment.sh` - Reproducible setup
2. `generate_data.py` - Complete generation pipeline
3. `constitution.yaml` - Versioned principles
4. `data/mvp_100_pairs.jsonl` - First 100 preference pairs
5. `checkpoints/mvp_dpo_100/` - Initial trained model
6. `results/mvp_metrics.json` - Quality metrics

## Execution Plan
1. Provision RunPod A100 40GB
2. Clone repo and run setup script (30 min)
3. Generate 100 examples (1.5 hours)
4. Run MVP DPO training (30 min)
5. Evaluate and checkpoint (15 min)
Total: ~3 hours, ~$5-6 cost

## Next Steps
After MVP validation, scale to 5k examples with Llama Guard filtering (Milestone 2)
