# RunPod Quick Start Checklist

**Goal**: Get from zero to working pod in 5-10 minutes (first time) or 30 seconds (subsequent pods)

---

## First Time Setup (One Pod, One Time)

### 1. Create Network Volume (2 min)

In RunPod dashboard:
1. Go to **Storage** → **Network Volumes**
2. Click **Create Network Volume**
3. Settings:
   - **Name**: `maximalcai-experiment`
   - **Size**: 100GB
   - **Region**: (same as where you'll launch pods)
4. Click **Create**

**Cost**: ~$10-20 for entire experiment (~3-7% of budget)

### 2. Launch Pod with Volume (2 min)

1. Go to **Pods** → **+ Deploy**
2. Select GPU (H100, A100, or available high-end GPU)
3. Under **Storage**:
   - Check "Attach Network Volume"
   - Select `maximalcai-experiment`
4. Click **Deploy**
5. Wait for pod to start (~1-2 min)

### 3. Run Setup Script (5-10 min)

SSH to pod, then:

```bash
cd /workspace/maximalcai-experiment

# Download and run setup
curl -O https://raw.githubusercontent.com/abstractionlair/cai-constitution-bootstrap/main/scripts/setup_network_volume.sh
chmod +x setup_network_volume.sh
./setup_network_volume.sh
```

The script will:
- Clone repository
- Create Python virtual environment
- Install PyTorch, transformers, etc.
- Install Node.js and Claude Code
- Configure credentials (git, GitHub, Anthropic)
- Set up Claude Code config
- Create `activate_pod.sh` for future pods

**Follow the prompts** for credentials:
- Git name (default: Scott McGuire)
- Git email
- GitHub token (for commits)
- Anthropic API key (optional - pod uses chat subscription)

### 4. Activate Environment (5 sec)

```bash
source activate_pod.sh
```

### 5. Verify Everything Works (1 min)

```bash
# Check versions
python --version
python -c "import torch; print('PyTorch:', torch.__version__)"
claude --version
git config user.name

# Test generation (optional - 5-10 min)
python3 scripts/generate_sample_data.py --count 10
```

**✅ Done! You're ready to work.**

---

## Every New Pod (After Termination)

### 1. Create New Pod with Volume (2 min)

**When previous pod terminates** (GPU unavailable):

1. Go to **Pods** → **+ Deploy**
2. Select any available GPU
3. Under **Storage**: Attach `maximalcai-experiment` volume
4. Click **Deploy**

### 2. Activate Environment (30 sec)

SSH to new pod, then:

```bash
cd /workspace/maximalcai-experiment
source activate_pod.sh
```

**That's it!** Everything persists:
- ✅ Code and git repo
- ✅ Python packages
- ✅ Node.js and Claude Code
- ✅ Credentials and config
- ✅ Previous artifacts

### 3. Continue Working

```bash
# Pull latest code (if Local Claude committed changes)
git pull

# Continue work
python3 scripts/generate_data_parallel.py --count 15000
```

---

## Common Tasks

### Generate Sample Data (30 min, ~$1-2)
```bash
cd /workspace/maximalcai-experiment
source activate_pod.sh
python3 scripts/generate_sample_data.py --count 100
```

### Generate Full Dataset - Single GPU (4-8 hr, ~$10-20)
```bash
cd /workspace/maximalcai-experiment
source activate_pod.sh
python3 scripts/generate_sample_data.py --count 15000
```

### Generate Full Dataset - Multi-GPU (1-2 hr, ~$12-24)
```bash
# Launch pod with 4 GPUs
cd /workspace/maximalcai-experiment
source activate_pod.sh
accelerate launch --multi_gpu scripts/generate_data_parallel.py --count 15000
```

### Download Results to Local Machine
```bash
# From your MacBook
scp -P <PORT> -i ~/.ssh/id_ed25519 \
  root@<POD_IP>:/workspace/maximalcai-experiment/cai-constitution-bootstrap/artifacts/*.jsonl \
  ~/MaximalCAI/artifacts/
```

### Commit Results (Pod Claude)
```bash
cd /workspace/maximalcai-experiment/cai-constitution-bootstrap
git add artifacts/*.jsonl
git commit -m "Add generated data

- 15k examples, multi-GPU generation
- QC metrics: [insert metrics]

🤖 Generated with Claude Code on RunPod"
git push  # GitHub token configured, no password needed
```

---

## Troubleshooting

### "activate_pod.sh not found"
→ Run setup script first (one-time): `./setup_network_volume.sh`

### "Network volume not found"
→ Check volume attached in RunPod dashboard under pod settings

### "Python/PyTorch not found after activation"
→ Use `source activate_pod.sh` (not `./activate_pod.sh`)

### "Git credentials not working"
→ Re-run setup to reconfigure: `cd /workspace/maximalcai-experiment && ./setup_network_volume.sh`

### "Out of disk space"
→ Check usage: `df -h /workspace/maximalcai-experiment`
→ Clean old artifacts: `rm artifacts/sample_*.jsonl`
→ Or increase volume size in RunPod dashboard

---

## Cost Summary

| Item | Cost | Frequency |
|------|------|-----------|
| Network volume (100GB) | ~$10-20 | One-time (entire experiment) |
| H100 pod | ~$2.69/hr | Per hour running |
| Sample generation (100) | ~$1-2 | ~30 min |
| Full generation (15k) | ~$10-20 | 4-8 hr single GPU |
| Full generation (15k) | ~$12-24 | 1-2 hr multi-GPU |

**Total experiment budget**: $300
**Network volume**: 2-3% of budget
**Break-even after**: ~5 pod recreations (time saved)

---

## Next Steps

1. ✅ Create network volume
2. ✅ Run `setup_network_volume.sh` (one-time)
3. ✅ Test with small sample generation
4. ✅ Proceed with full data generation
5. ✅ Train SFT model
6. ✅ Evaluate and iterate

**Full documentation**: See `/docs/NETWORK_VOLUME_SETUP.md`
