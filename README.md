# Constitutional AI Bootstrap Experiment

An experiment in maximally automated Constitutional AI training, where a base model bootstraps its own alignment through self-critique and constitutional principles.

## Project Goal

Implement and document a fully automated Constitutional AI training pipeline that uses a base model (Qwen-2.5-32B) to:
1. Generate diverse tasks through self-instruction
2. Critique its own responses against constitutional principles  
3. Create revised, improved responses
4. Train on preference pairs using DPO/ORPO
5. Demonstrate alignment improvements through benchmarks

## Key Features

- **Maximum Automation**: Minimal human intervention in the training loop
- **Reproducibility**: All steps scriptable and deterministic
- **Safety First**: Constitutional safeguards and responsible release practices
- **Publication Ready**: Comprehensive documentation of methods and results

## Technical Stack

- **Model**: Qwen-2.5-32B base model
- **Hardware**: RunPod A100 40GB GPU
- **Training**: QLoRA + DPO via Unsloth/TRL
- **Safety**: Llama Guard 3-8B for content filtering
- **Inference**: Quantizable to run on 24GB consumer GPUs

## Project Structure

```
cai_experiment/
├── constitution.yaml          # Constitutional principles
├── scripts/
│   ├── setup_environment.sh   # Dependencies installation
│   ├── generate_data.py       # Main data generation pipeline
│   ├── train_dpo.py          # DPO training script
│   └── evaluate.py           # Basic evaluation
├── data/                     # Generated datasets
├── checkpoints/              # Model checkpoints
├── specs/                    # Implementation specifications
└── logs/                     # Generation and training logs
```

## Milestones

1. **MVP Pipeline**: 100 preference pairs + validation
2. **Scaled Generation**: 5k filtered pairs with safety checks
3. **Full Training**: Complete alignment + benchmarks
4. **Documentation**: Reproducible artifacts for publication

## Budget

- Target: $50-300 for complete experiment
- ~30-50 hours of A100 40GB time
- Cost optimization through iterative development

## Safety & Ethics

- Default safe constitutional principles (HHH-focused)
- Llama Guard filtering for harmful content
- Staged release (code → data → optional weights)
- OpenRAIL licensing for responsible use

## License

OpenRAIL - See LICENSE file for details
