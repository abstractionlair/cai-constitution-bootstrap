# RunPod Quick Start

**5-minute setup for fresh A100 80GB pod**

---

## Prerequisites

- Fresh RunPod pod with A100 SXM 80GB
- Ubuntu with PyTorch template (recommended)
- SSH access configured

---

## Setup (One Command)

SSH into your pod and run:

```bash
curl -sSL https://raw.githubusercontent.com/abstractionlair/cai-constitution-bootstrap/main/scripts/runpod_setup.sh | bash
```

**Or manually:**

```bash
# SSH into pod
ssh -p <PORT> root@<HOST>

# Clone repo
cd /workspace
git clone https://github.com/abstractionlair/cai-constitution-bootstrap.git MaximalCAI
cd MaximalCAI

# Run setup
bash scripts/runpod_setup.sh
```

**Installs:**
- PyTorch with CUDA 12.1
- Transformers, Datasets, Accelerate
- Unsloth (efficient training)
- TRL, PEFT, BitsAndBytes
- Flash Attention (optional)
- All utilities

**Time**: ~5-10 minutes

---

## What's in Git

✅ **All scripts** (40+ Python files)
- Data generation
- Training (SFT + DPO)
- Evaluation
- Utilities

✅ **All documentation**
- Session plan (`docs/RUNPOD_SESSION_PLAN.md`)
- Technical guides
- Standards and protocols

✅ **Configuration**
- `constitution.yaml`
- Specs for all 6 stages

❌ **NOT in git** (as expected):
- Model weights (download on pod)
- Generated data (create on pod)
- Checkpoints (save on pod)
- Artifacts (create on pod)

---

## Verify Setup

After `runpod_setup.sh` completes:

```bash
# Check GPU
nvidia-smi

# Test environment
python3 << EOF
import torch
import transformers
print(f"PyTorch: {torch.__version__}")
print(f"CUDA: {torch.cuda.is_available()}")
print(f"GPU: {torch.cuda.get_device_name(0)}")
EOF

# Verify scripts
ls scripts/*.py | wc -l  # Should see 40+ scripts
```

---

## Start Working

```bash
cd /workspace/MaximalCAI

# Phase 1: Verify base model is clean
python scripts/test_base_model_ultra_clean.py

# Follow the session plan
cat docs/RUNPOD_SESSION_PLAN.md
```

---

## If You Need to Recreate Pod

**All code is in git** - nothing will be lost!

1. Terminate old pod
2. Create new A100 80GB pod
3. Run `runpod_setup.sh` again
4. Continue from where you left off

**Data persistence options:**
- Use network volumes (recommended for future)
- Transfer artifacts back to local: `scp -P <PORT> root@<HOST>:/workspace/MaximalCAI/artifacts/* ./artifacts/`
- Commit results to git (only small JSON summaries, not raw data)

---

## Cost Management

**Hourly rate**: $1.74 for A100 SXM 80GB

**Stage 1 estimate**: 9-16 hours = $15-29

**Tips:**
- Stop pod when not actively training/generating
- Use `screen` or `tmux` to keep processes running if SSH drops
- Set up billing alerts in RunPod

---

## Troubleshooting

### "No module named X"
```bash
cd /workspace/MaximalCAI
bash scripts/runpod_setup.sh
```

### "CUDA out of memory"
- Reduce batch size in training script
- Use 4-bit quantization (already default)
- Check for zombie processes: `ps aux | grep python`

### "Git clone failed"
```bash
# Check internet
ping github.com

# Try with token if private repo
git clone https://<TOKEN>@github.com/abstractionlair/cai-constitution-bootstrap.git
```

### "Flash attention won't install"
- It's optional - script continues without it
- Training will be slightly slower but still works

---

## Session Plan

See `/docs/RUNPOD_SESSION_PLAN.md` for complete 9-phase plan with:
- Exact commands for each phase
- Success criteria
- Time/cost estimates
- Decision points (when to stop if issues)
- Troubleshooting

---

## After Session Complete

```bash
# Transfer artifacts back
scp -P <PORT> -r root@<HOST>:/workspace/MaximalCAI/artifacts ./artifacts/

# Update documentation locally
# Update ROADMAP.md with results
# Commit and push

# STOP THE POD (important!)
```

---

**Ready?** Run `runpod_setup.sh` and start with Phase 1!
