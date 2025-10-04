# RunPod H100 Session Info

**Created**: 2025-10-04
**GPU**: H100 SXM 80GB @ $2.69/hr
**Budget**: $300 (~111 hours available)
**Storage**: Network volume (check size)

---

## Connection Info

### SSH over TCP (Direct - Recommended)
```bash
ssh root@63.141.33.75 -p 22069 -i ~/.ssh/id_ed25519
```

**Use this for**:
- SCP/SFTP file transfers
- Direct connection (faster, more reliable)
- All production work

### SSH via Proxy (Fallback)
```bash
ssh 3bstq10qli1qmm-64411999@ssh.runpod.io -i ~/.ssh/id_ed25519
```

**Note**: No SCP/SFTP support

### Jupyter Lab
- Port: 8888
- Status: Ready
- URL: (check RunPod dashboard)

### Environment Variables
```bash
export RUNPOD_HOST=63.141.33.75
export RUNPOD_PORT=22069
export RUNPOD_SSH_KEY=~/.ssh/id_ed25519
```

---

## Quick Start Checklist

### 1. Initial Connection & Verification (~5 min)

```bash
# Connect
ssh root@63.141.33.75 -p 22069 -i ~/.ssh/id_ed25519

# Check GPU
nvidia-smi

# Check disk space
df -h /workspace
df -h /tmp

# Check CUDA
nvcc --version
python3 -c "import torch; print(f'CUDA: {torch.cuda.is_available()}, Version: {torch.version.cuda}')"
```

**Expected**:
- H100 SXM 80GB visible
- Network volume mounted at /workspace
- ~100GB available
- CUDA 12.x

---

### 2. Code Deployment (~5 min)

```bash
# Navigate to workspace
cd /workspace

# Clone repo if not exists
if [ ! -d "MaximalCAI" ]; then
    git clone https://github.com/abstractionlair/cai-constitution-bootstrap.git MaximalCAI
fi

cd MaximalCAI

# Pull latest
git pull

# Check we have latest code
git log --oneline -5
# Should show: 6b1a5a9 Update budget plan with H100 GPU selection

# Create directory structure
mkdir -p artifacts checkpoints data logs
```

---

### 3. Environment Setup (~10-15 min)

```bash
# Install dependencies
pip install --upgrade pip
pip install torch transformers accelerate bitsandbytes peft datasets scipy numpy

# Verify installation
python3 -c "import torch, transformers, bitsandbytes; print('All imports OK')"

# Set environment variable
export CAI_BASE_DIR=/workspace/MaximalCAI
echo "export CAI_BASE_DIR=/workspace/MaximalCAI" >> ~/.bashrc
```

---

### 4. Create Session Manifest (~1 min)

```bash
cd /workspace/MaximalCAI

# Create session manifest (once implemented)
# python3 scripts/create_session_manifest.py

# For now, manually log session start
cat > artifacts/session_start_$(date +%Y%m%d_%H%M%S).txt << EOF
Session started: $(date)
GPU: H100 SXM 80GB
Host: 63.141.33.75:22069
Git commit: $(git rev-parse HEAD)
Git branch: $(git rev-parse --abbrev-ref HEAD)
EOF
```

---

### 5. Run Smoke Test (~5-10 min, ~$0.30)

**REQUIRED before any production work!**

```bash
cd /workspace/MaximalCAI

# Run smoke test
python3 scripts/smoke_test_migration.py

# Expected output:
# ✅ ALL SMOKE TESTS PASSED
# Time: ~300-600s
# 🚀 Ready for production runs!
```

**If smoke test fails**: DO NOT proceed. Fix issues first.

**If smoke test passes**: Ready for production!

---

### 6. Monitor During Session

```bash
# GPU utilization
watch -n 1 nvidia-smi

# Disk usage
watch -n 60 'df -h /workspace'

# Training progress (in separate terminal)
tail -f logs/*.log

# Cost tracking
# ~$2.69/hr, check elapsed time regularly
```

---

## File Transfer Commands

### Upload files to pod
```bash
# Single file
scp -P 22069 -i ~/.ssh/id_ed25519 local_file.txt root@63.141.33.75:/workspace/MaximalCAI/

# Directory
scp -r -P 22069 -i ~/.ssh/id_ed25519 local_dir/ root@63.141.33.75:/workspace/MaximalCAI/

# Using tar for large directories
tar czf - local_dir/ | ssh root@63.141.33.75 -p 22069 -i ~/.ssh/id_ed25519 'tar xzf - -C /workspace/MaximalCAI/'
```

### Download files from pod
```bash
# Single file
scp -P 22069 -i ~/.ssh/id_ed25519 root@63.141.33.75:/workspace/MaximalCAI/artifacts/results.json ./

# Directory
scp -r -P 22069 -i ~/.ssh/id_ed25519 root@63.141.33.75:/workspace/MaximalCAI/artifacts/ ./

# Using tar for large directories
ssh root@63.141.33.75 -p 22069 -i ~/.ssh/id_ed25519 'tar czf - /workspace/MaximalCAI/artifacts' | tar xzf -
```

---

## Session End Checklist

### Before stopping (if resuming later)
```bash
# Verify everything saved to /workspace
ls -la /workspace/MaximalCAI/artifacts
ls -la /workspace/MaximalCAI/checkpoints

# Commit any code changes
cd /workspace/MaximalCAI
git status
git add .
git commit -m "Session progress"
git push

# Can safely stop pod (network volume persists)
```

### Before terminating (if done)
```bash
# Download critical artifacts
cd /workspace/MaximalCAI
tar czf ../session_backup_$(date +%Y%m%d).tar.gz \
    artifacts/ \
    checkpoints/ \
    data/ \
    logs/

# Download backup locally
# (from local machine)
scp -P 22069 -i ~/.ssh/id_ed25519 root@63.141.33.75:/workspace/session_backup_*.tar.gz ./

# Network volume persists, but good to have local copy
```

---

## Emergency Recovery

### Lost connection
```bash
# Reconnect
ssh root@63.141.33.75 -p 22069 -i ~/.ssh/id_ed25519

# Check running processes
ps aux | grep python

# Check training progress
tail logs/*.log
```

### Pod terminated accidentally
- Network volume data is safe
- Spin up new pod
- Attach same network volume
- Continue from last checkpoint

### Out of disk space
```bash
# Check usage
du -h --max-depth=2 /workspace/MaximalCAI | sort -hr | head -20

# Clean up intermediate files
rm -rf /workspace/MaximalCAI/checkpoints/intermediate_*
rm -rf /workspace/MaximalCAI/data/raw/*

# Compress logs
gzip /workspace/MaximalCAI/logs/*.log
```

---

## Cost Tracking

**Rate**: $2.69/hr H100
**Budget**: $300 = ~111 hours

**Quick calc**:
- 10 hours = $26.90
- 25 hours = $67.25
- 50 hours = $134.50
- 75 hours = $201.75
- 100 hours = $269.00

**Monitor frequently** - training jobs can run longer than expected!

**Set alerts**: Consider stopping if approaching $250 to preserve buffer.

---

## Next Steps

1. ✅ Connect and verify GPU
2. ✅ Deploy code
3. ✅ Setup environment
4. ✅ Run smoke test (~$0.30)
5. ⏳ **STOP HERE** until P0 tasks complete:
   - Implement evaluation statistics
   - Implement provenance persistence
6. ⏳ Resume for production Session 1 (~$54-73)

**Do not proceed to production work until**:
- Smoke test passes
- P0 tasks implemented (eval stats + provenance)
- Ready to commit to full session

---

## Notes

- This is H100 (2x faster than A100)
- Adjust time estimates accordingly
- Network volume persists across sessions
- Container disk (/tmp) is temporary
- Save everything to /workspace
