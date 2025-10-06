# Stage 1 Implementation Scripts

Complete implementation of Stage 1: Explicit Instruction Following for the Constitutional AI Bootstrap experiment.

## Quick Start

### 1. Environment Setup (On RunPod)
```bash
# Upload your project to RunPod
# Then run setup
chmod +x setup_environment.sh
./setup_environment.sh
```

### 2. Run Complete Pipeline
```bash
# Full pipeline (recommended)
python run_stage1_pipeline.py

# Quick test (for debugging)
python run_stage1_pipeline.py --quick-test
```

### 3. Or Run Individual Steps
```bash
# Step 1: Baseline assessment (MUST DO FIRST!)
python baseline_assessment.py

# Step 2: Generate training data
python generate_stage1_data.py --count 1000

# Step 3: Train with DPO
python train_stage1_dpo.py --epochs 3

# Step 4: Evaluate results
python evaluate_stage1.py
```

## Script Overview

### Core Pipeline Scripts

#### `baseline_assessment.py` 🧪
**CRITICAL FIRST STEP**: Tests what the base model can already do.
```bash
python baseline_assessment.py
```
- Tests Qwen-2.5-32B base model (NOT Instruct version)
- Measures capabilities across completions, questions, instructions, commands
- Expected: completions ~80%, questions ~30%, instructions ~10%
- Saves results to `results/baseline_assessment.json`

#### `generate_stage1_data.py` 📝
Generates training data for instruction following improvement.
```bash
python generate_stage1_data.py --count 1000
python generate_stage1_data.py --small-test  # 100 examples for testing
```
- Generates diverse explicit instructions (4 types)
- Creates initial responses with base model
- Critiques responses against Stage 1 principles
- Generates improved responses
- Creates preference pairs for DPO training
- Saves to `data/stage1/`

#### `train_stage1_dpo.py` 🏋️
Trains the model using DPO with LoRA adapters.
```bash
python train_stage1_dpo.py --epochs 3 --batch-size 4
python train_stage1_dpo.py --quick-test  # 1 epoch for testing
```
- Uses LoRA for efficient training (saves ~500MB vs 65GB)
- DPO training on preference pairs
- Saves only LoRA adapters to `checkpoints/stage1/`
- Supports Weights & Biases logging

#### `evaluate_stage1.py` 📊
Comprehensive evaluation comparing base vs trained model.
```bash
python evaluate_stage1.py
python evaluate_stage1.py --checkpoint path/to/adapters --eval-size 200
python evaluate_stage1.py --quick  # Quick test with 20 examples
```
- Loads base model and trained model with LoRA
- Generates fresh evaluation set
- Compares performance across instruction types
- Shows improvement delta (e.g., 10% → 95%)
- Saves detailed results to `results/`

#### `run_stage1_pipeline.py` 🚀
Master orchestrator for the complete pipeline.
```bash
# Full pipeline
python run_stage1_pipeline.py

# With custom settings
python run_stage1_pipeline.py --instructions 500 --epochs 2 --batch-size 8

# Quick test
python run_stage1_pipeline.py --quick-test
```
- Runs all steps in sequence
- Handles dependencies and error recovery
- Skips steps if outputs already exist
- Comprehensive logging and reporting

### Utility Modules

#### `utils/model_loader.py`
Unsloth-based model loading with memory optimization.
- 4-bit quantization for training
- LoRA configuration management
- GPU memory monitoring

#### `utils/data_formatter.py`
Data generation and formatting utilities.
- Stage1DataGenerator: Creates diverse instruction sets
- Preference pair formatting for DPO
- Train/test splitting

#### `utils/metrics.py`
Evaluation metrics and success criteria.
- InstructionFollowingEvaluator: Automated evaluation
- StageEvaluator: Performance tracking
- Comparison with baseline results

### Support Scripts

#### `runpod_manager.py`
RunPod instance management and cost tracking.
```bash
python runpod_manager.py list
python runpod_manager.py stop POD_ID
python runpod_manager.py start POD_ID
```

#### `test_ssh.sh`
Test RunPod SSH connectivity.
```bash
./test_ssh.sh
```

## Expected Results

### Baseline Assessment
- **Completions**: 70-90% (model completes "The sun is a..." → "star")
- **Questions**: 20-40% (model may not answer "What is X?")
- **Instructions**: 5-15% (model likely ignores "Answer this:")
- **Commands**: 5-15% (model likely ignores "Write a sentence about...")

### After Stage 1 Training
- **All categories**: 95%+ success rate
- **Key improvement**: Instructions and commands jump from ~10% to 95%
- **Foundation ready**: Model can now reliably follow explicit instructions

## File Structure

```
scripts/
├── README.md                    # This file
├── setup_environment.sh         # Environment setup for RunPod
├── run_stage1_pipeline.py      # Master pipeline orchestrator
├── baseline_assessment.py      # CRITICAL: Test base model capabilities
├── generate_stage1_data.py     # Generate training data
├── train_stage1_dpo.py         # DPO training with LoRA
├── evaluate_stage1.py          # Comprehensive evaluation
├── runpod_manager.py           # RunPod management utilities
├── test_ssh.sh                 # SSH connectivity test
└── utils/
    ├── __init__.py
    ├── model_loader.py          # Unsloth model loading
    ├── data_formatter.py        # Data generation utilities
    └── metrics.py               # Evaluation metrics

# Generated during execution:
data/stage1/
├── raw_instructions.jsonl
├── initial_responses.jsonl
├── critiques.jsonl
├── improvements.jsonl
├── preference_pairs.jsonl
├── train_preference_pairs.jsonl
└── test_preference_pairs.jsonl

checkpoints/stage1/
└── run_YYYYMMDD_HHMMSS/
    └── final_lora_adapters/     # ~500MB LoRA adapters

results/
├── baseline_assessment.json
└── stage1_evaluation_YYYYMMDD_HHMMSS.json

logs/
└── stage1_pipeline_YYYYMMDD_HHMMSS.log
```

## Key Design Decisions

### 1. Baseline Assessment First
- **Critical**: Must establish what base model can already do
- **Honest**: Shows true improvement delta
- **Scientific**: Provides defensible baseline

### 2. LoRA-Only Saving
- **Storage**: 500MB vs 65GB per stage
- **Transfer**: Easy to download/upload
- **Flexible**: Can merge when needed for generation

### 3. Automated Evaluation
- **Objective**: Clear pass/fail criteria
- **Scalable**: No human bottleneck
- **Reproducible**: Same metrics across experiments

### 4. Progressive Bootstrapping
- **Stage 1**: Learn explicit instruction following
- **Foundation**: Enables all subsequent stages
- **Critical**: Must achieve 95%+ success before Stage 2

## Troubleshooting

### Common Issues

1. **"Training data not found"**
   ```bash
   # Run data generation first
   python generate_stage1_data.py
   ```

2. **"No checkpoint found"**
   ```bash
   # Train model first
   python train_stage1_dpo.py
   ```

3. **Out of memory during training**
   ```bash
   # Reduce batch size
   python train_stage1_dpo.py --batch-size 2
   ```

4. **SSH connection fails**
   ```bash
   ./test_ssh.sh
   # Check .env.runpod credentials
   ```

### Performance Expectations

- **Baseline assessment**: ~30 minutes
- **Data generation (1000 examples)**: ~2-3 hours
- **Training (3 epochs)**: ~2-3 hours  
- **Evaluation**: ~30 minutes
- **Total**: ~6-8 hours (~$12-14 on A100 80GB)

## Success Criteria

✅ **Stage 1 Complete When**:
- Baseline assessment shows starting capabilities
- Training data generated (500+ preference pairs)
- Model trained and achieves 95%+ instruction following
- Comprehensive evaluation shows improvement delta
- Ready to generate Stage 2 training data

## Next Steps

After Stage 1 success:
1. Use trained Stage 1 model to generate Stage 2 data
2. Stage 2: Learn implicit instructions (questions → answers)
3. Continue through all 6 stages of progressive bootstrapping

## Cost Tracking

All scripts include cost awareness:
- Pipeline logs estimated costs
- RunPod manager tracks usage
- Stop pods between sessions to save money
- A100 80GB: ~$1.74/hour

Remember: **STOP YOUR POD** when not in use! 🚨