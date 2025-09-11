# Quick Start Guide for Claude Code

## Current Status
- RunPod instance is provisioned (A100 SXM 80GB)
- SSH access: `ssh -T tupdqnn4ka2obr-6441138e@ssh.runpod.io -i ~/.ssh/id_ed25519`
- Cost: $1.74/hour - BE EFFICIENT!

## Your First Task: Implement Stage 1

### Stage 1: Explicit Instruction Following
1. Read `/specs/stage_1_explicit_instructions.md`
2. Read `/specs/complete_pipeline.md` for context
3. Create these scripts:
   - `scripts/setup_environment.sh` - Install dependencies
   - `scripts/stage1_generate_data.py` - Generate training data
   - `scripts/stage1_train.py` - Train the model
   - `scripts/stage1_evaluate.py` - Test success rate

### Key Requirements for Stage 1:
- Generate 500-1000 explicit instructions
- Examples: "Answer this:", "Complete:", "Generate:"
- Train until 95%+ instruction following
- Save the model checkpoint for Stage 2

### Implementation Steps:
1. **Setup** (30 min)
   - SSH into RunPod
   - Clone this repo
   - Install dependencies (Unsloth, TRL, transformers)
   
2. **Data Generation** (3-4 hours)
   - Generate diverse explicit instructions
   - Get model responses
   - Apply constitutional critique
   - Create preference pairs
   
3. **Training** (2-3 hours)
   - Load Qwen-2.5-32B with QLoRA (4-bit)
   - Train with DPO on preference pairs
   - Monitor instruction-following accuracy
   
4. **Validation** (1 hour)
   - Test on 100 held-out instructions
   - Measure success rate
   - Save checkpoint if >95% accuracy

### Technical Details:
- Use 4-bit quantization for training (QLoRA)
- Use 8-bit or 16-bit for generation (better quality)
- Batch size: Start with 1, increase if memory allows
- Save all outputs to `/workspace` on RunPod

### Remember:
- This is Stage 1 of 6 - it must work well!
- The model from Stage 1 helps create Stage 2 data
- Track costs: ~$10-14 expected for Stage 1
- Stop the pod when taking breaks!

## File Organization:
```
scripts/
├── setup_environment.sh
├── stage1_generate_data.py
├── stage1_train.py
├── stage1_evaluate.py
└── utils/
    ├── constitutional.py  # Constitutional principles
    └── data_utils.py      # Data handling
```

## Success Criteria:
- [ ] 95%+ explicit instruction following
- [ ] Model checkpoint saved
- [ ] Training logs documented
- [ ] Ready for Stage 2

Start with reading the Stage 1 specification, then implement incrementally!
