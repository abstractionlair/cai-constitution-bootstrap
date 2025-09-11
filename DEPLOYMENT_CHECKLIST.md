# Stage 1 Deployment Checklist for Claude Code

## Pre-Deployment Checks
- [ ] User confirms RunPod is running (costs $1.74/hr)
- [ ] SSH credentials available in CLAUDE.md
- [ ] Code review completed (preference pairs exist!)
- [ ] Small local test if possible

## Deployment Steps

### 1. Initial Connection
```bash
# Test SSH connection
ssh tupdqnn4ka2obr-6441138e@ssh.runpod.io -i ~/.ssh/id_ed25519 'echo "Connected to RunPod"'
```

### 2. Setup Repository on RunPod
```bash
# SSH into RunPod
ssh tupdqnn4ka2obr-6441138e@ssh.runpod.io -i ~/.ssh/id_ed25519

# In RunPod:
cd /workspace
git clone https://github.com/abstractionlair/cai-constitution-bootstrap.git
cd cai-constitution-bootstrap
```

### 3. Transfer Latest Code
```bash
# From local Mac:
# Copy all scripts
scp -i ~/.ssh/id_ed25519 -r /Users/scottmcguire/MaximalCAI/scripts/* \
    tupdqnn4ka2obr-6441138e@ssh.runpod.io:/workspace/cai-constitution-bootstrap/scripts/

# Copy constitution
scp -i ~/.ssh/id_ed25519 /Users/scottmcguire/MaximalCAI/constitution.yaml \
    tupdqnn4ka2obr-6441138e@ssh.runpod.io:/workspace/cai-constitution-bootstrap/

# Copy specs (for reference)
scp -i ~/.ssh/id_ed25519 -r /Users/scottmcguire/MaximalCAI/specs/* \
    tupdqnn4ka2obr-6441138e@ssh.runpod.io:/workspace/cai-constitution-bootstrap/specs/
```

### 4. Environment Setup on RunPod
```bash
# SSH into RunPod
ssh tupdqnn4ka2obr-6441138e@ssh.runpod.io -i ~/.ssh/id_ed25519

cd /workspace/cai-constitution-bootstrap

# Run setup script (if exists)
if [ -f scripts/setup_environment.sh ]; then
    bash scripts/setup_environment.sh
else
    # Manual setup
    pip install transformers torch datasets trl peft unsloth
    pip install wandb tqdm pyyaml
fi

# Verify GPU
nvidia-smi
python -c "import torch; print(f'CUDA: {torch.cuda.is_available()}')"
python -c "import torch; print(f'GPU: {torch.cuda.get_device_name(0)}')"
python -c "import torch; print(f'Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f}GB')"
```

### 5. Run Baseline Assessment
```bash
# Still in RunPod
cd /workspace/cai-constitution-bootstrap

# Run baseline (CRITICAL - do this first!)
python scripts/baseline_assessment.py 2>&1 | tee logs/baseline.log

# Check results
ls -la results/
cat results/baseline_assessment.json | python -m json.tool | head -20
```

### 6. Small Test Run
```bash
# Generate 100 instructions as test
python scripts/generate_stage1_data.py --small-test 2>&1 | tee logs/stage1_test.log

# Check generated data
ls -la data/stage1/
wc -l data/stage1/*.jsonl
```

### 7. Full Stage 1 Pipeline
```bash
# If test successful, run full pipeline
python scripts/run_stage1_pipeline.py 2>&1 | tee logs/stage1_full.log

# Monitor in another terminal
watch -n 1 nvidia-smi
```

### 8. Transfer Results Back
```bash
# From local Mac:
# Results
scp -i ~/.ssh/id_ed25519 -r \
    tupdqnn4ka2obr-6441138e@ssh.runpod.io:/workspace/cai-constitution-bootstrap/results/* \
    /Users/scottmcguire/MaximalCAI/results/

# Checkpoints (LoRA adapters)
scp -i ~/.ssh/id_ed25519 -r \
    tupdqnn4ka2obr-6441138e@ssh.runpod.io:/workspace/cai-constitution-bootstrap/checkpoints/* \
    /Users/scottmcguire/MaximalCAI/checkpoints/

# Generated data
scp -i ~/.ssh/id_ed25519 -r \
    tupdqnn4ka2obr-6441138e@ssh.runpod.io:/workspace/cai-constitution-bootstrap/data/* \
    /Users/scottmcguire/MaximalCAI/data/

# Logs
scp -i ~/.ssh/id_ed25519 -r \
    tupdqnn4ka2obr-6441138e@ssh.runpod.io:/workspace/cai-constitution-bootstrap/logs/* \
    /Users/scottmcguire/MaximalCAI/logs/
```

## Time & Cost Estimates
- Baseline Assessment: 30 minutes (~$0.87)
- Small Test (100): 1 hour (~$1.74)
- Full Pipeline (1000): 4-5 hours (~$7-9)
- **Total Stage 1**: ~6 hours (~$10.44)

## Success Criteria
- [ ] Baseline shows <40% instruction following
- [ ] Small test generates valid preference pairs
- [ ] Full run achieves >90% instruction following
- [ ] LoRA checkpoint saved (~500MB)
- [ ] All data transferred back to local

## Post-Deployment
- [ ] STOP RunPod instance (don't terminate!)
- [ ] Commit results to git
- [ ] Document actual times and costs
- [ ] Prepare for Stage 2

## Troubleshooting Commands
```bash
# If out of memory
export PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512

# Clear GPU cache in Python
import torch
torch.cuda.empty_cache()

# Monitor memory usage
watch -n 1 'nvidia-smi | grep MiB'

# Check disk space
df -h /workspace

# Kill stuck Python process
pkill -f python
```

## REMINDER TO USER
**STOP THE POD** when taking a break! It costs $1.74/hour while running.
```bash
python scripts/runpod_manager.py stop tupdqnn4ka2obr
```
