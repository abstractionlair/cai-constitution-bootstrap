# Constitutional AI Bootstrap Experiment

An experiment in maximally automated Constitutional AI training, where a base model bootstraps its own alignment through self-critique and constitutional principles.

## Status

Work in progress.

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
- **Hardware**: RunPod A100 SXM 80GB GPU
- **Training**: QLoRA + DPO via Unsloth/TRL
- **Safety**: Llama Guard 3-8B for content filtering
- **Inference**: Flexible - can run at 4-bit, 8-bit, or 16-bit

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

### Progressive Bootstrapping (6 Stages)
1. **Stage 1**: Explicit instruction following (foundation)
2. **Stage 2**: Implicit instructions (questions & context)
3. **Stage 3**: Generation tasks (create examples)
4. **Stage 4**: Evaluation tasks (judge quality)
5. **Stage 5**: Revision tasks (improve text)
6. **Stage 6**: Constitutional integration (full CAI)

Each stage produces a functional model that helps generate training data for the next stage.

## Budget

- Target: $50-150 for complete experiment
- Stages 1-5: ~$10-14 each (~$50-70 total)
- Stage 6 (Constitutional): ~$20-30
- Buffer for experimentation: ~$30-50
- Total: Well within personal project range

## Safety & Ethics

- Default safe constitutional principles (HHH-focused)
- Llama Guard filtering for harmful content
- Staged release (code → data → optional weights)
- OpenRAIL licensing for responsible use

## License

OpenRAIL - See LICENSE file for details
