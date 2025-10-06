# RunPod Instance Status

**Last Updated**: 2025-10-04
**Strategy**: Opportunistically using available RunPod GPUs (H100, A100, or other high-end GPUs)
**Current Session**: 2x H100 SXM 80GB @ ~$5.38/hour
**Budget**: $300 total for experimentation

---

## Current Connection Details

### SSH Access (IMPORTANT: Use Direct SSH, NOT Stable Proxy!)

```bash
# Direct SSH (port changes on restart - check dashboard!)
export RUNPOD_PORT=48550  # UPDATE THIS after pod restart!
ssh -p $RUNPOD_PORT -i ~/.ssh/id_ed25519 root@195.26.233.96
```

**Key**: `~/.ssh/id_ed25519` (already configured)

### Why Stable Proxy Doesn't Work

The documented stable proxy is **BROKEN**:
```bash
# This FAILS (don't use):
ssh tupdqnn4ka2obr-6441138e@ssh.runpod.io
```

**Always use direct SSH with current port from dashboard.**

See `/docs/RUNPOD_SSH_SOLUTION.md` for full details.

---

## File Transfer

### DO NOT use scp (broken with proxy)

### DO use SSH pipes:

```bash
# Upload file
cat /local/path/file | ssh -p $RUNPOD_PORT -i ~/.ssh/id_ed25519 root@195.26.233.96 'cat > /workspace/path/file'

# Download file
ssh -p $RUNPOD_PORT -i ~/.ssh/id_ed25519 root@195.26.233.96 'cat /workspace/path/file' > /local/path/file

# Upload directory (tar)
tar czf - /local/dir | ssh -p $RUNPOD_PORT -i ~/.ssh/id_ed25519 root@195.26.233.96 'tar xzf - -C /workspace/'
```

**Helper script**: `/scripts/copy_to_pod.sh` (uses SSH pipes)

---

## Current Pod State

**Status**: Unknown (needs check)
**Last Known Port**: 48550 (may have changed)

**To check**:
1. Log in to RunPod dashboard
2. Check if pod is running or stopped
3. If running, get current port number
4. Update RUNPOD_PORT above

---

## Directory Structure on Pod

```
/workspace/
├── runs/
│   └── stage1_20250911_131105/
│       └── code/
│           ├── scripts/
│           ├── artifacts/
│           ├── checkpoints/
│           └── data/
└── persistent/  (if network volume attached)
```

**Base directory**: `/workspace/runs/stage1_20250911_131105/code`

---

## Environment Setup

### First Time Setup
```bash
# SSH into pod
ssh -p $RUNPOD_PORT -i ~/.ssh/id_ed25519 root@195.26.233.96

# Navigate to workspace
cd /workspace/runs/stage1_20250911_131105/code

# Run setup (if needed)
bash scripts/setup_environment.sh

# Verify GPU
nvidia-smi
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"
```

### Environment Variables
```bash
# On pod, set:
export CAI_BASE_DIR=/workspace/runs/stage1_20250911_131105/code
export RUNPOD_API_KEY=<from_dashboard>  # For programmatic control
```

---

## Typical Workflow

### 1. Start Pod (if stopped)
- Log in to RunPod dashboard
- Start pod
- Note new port number
- Update RUNPOD_PORT in local environment

### 2. Transfer Latest Code
```bash
# From Mac
cd /Users/scottmcguire/MaximalCAI
bash scripts/copy_to_pod.sh  # Uses correct SSH pipe method
```

### 3. Run Scripts
```bash
# SSH into pod
export RUNPOD_PORT=48550
ssh -p $RUNPOD_PORT -i ~/.ssh/id_ed25519 root@195.26.233.96

# Navigate and run
cd /workspace/runs/stage1_20250911_131105/code
python scripts/baseline_assessment.py
```

### 4. Monitor GPU
```bash
# In separate terminal
ssh -p $RUNPOD_PORT -i ~/.ssh/id_ed25519 root@195.26.233.96 'watch -n 1 nvidia-smi'
```

### 5. Download Results
```bash
# From Mac
ssh -p $RUNPOD_PORT -i ~/.ssh/id_ed25519 root@195.26.233.96 \
  'tar czf - /workspace/runs/stage1_20250911_131105/code/artifacts' | \
  tar xzf - -C /Users/scottmcguire/MaximalCAI/
```

### 6. Stop Pod
**IMPORTANT**: Always stop (not terminate) when done to save costs!
```bash
# Via dashboard, or programmatically:
python scripts/runpod_manager.py stop
```

---

## Cost Management

**Hourly Rate**: $1.74
**Budget Estimate**: ~$20 for full Stage 1 run

### Time Estimates
- Baseline assessment: ~30 min ($0.87)
- SFT data generation: ~1 hour ($1.74)
- SFT training: ~1 hour ($1.74)
- Preference pair generation: ~30 min ($0.87)
- DPO training: ~30 min ($0.87)
- Evaluation: ~1 hour ($1.74)
- **Total**: ~5 hours ($8.70)

**Always stop pod between sessions!**

---

## Programmatic Management

Using RunPod GraphQL API:

```python
import requests

RUNPOD_API_KEY = os.getenv('RUNPOD_API_KEY')
headers = {'Authorization': f'Bearer {RUNPOD_API_KEY}'}

# Stop pod
query = '''
mutation { podStop(input: {podId: "YOUR_POD_ID"}) { id } }
'''
requests.post('https://api.runpod.io/graphql',
              json={'query': query}, headers=headers)
```

See `/scripts/runpod_manager.py` for full implementation.

---

## Troubleshooting

### Connection Refused
- Check pod is running in dashboard
- Verify port number (changes on restart!)
- Try pinging: `ping 195.26.233.96`

### File Transfer Fails
- Don't use scp (broken)
- Use SSH pipes (see above)
- Check path exists on remote

### GPU Not Available
```bash
nvidia-smi  # Check GPU is visible
python -c "import torch; print(torch.cuda.is_available())"
```

### Out of Memory
- A100 has 80GB - should be plenty
- Check for zombie processes: `ps aux | grep python`
- Clear GPU cache: `python -c "import torch; torch.cuda.empty_cache()"`

---

## Quick Reference Commands

```bash
# Set port (update after each restart)
export RUNPOD_PORT=48550

# SSH
ssh -p $RUNPOD_PORT -i ~/.ssh/id_ed25519 root@195.26.233.96

# Copy file to pod
cat local_file | ssh -p $RUNPOD_PORT -i ~/.ssh/id_ed25519 root@195.26.233.96 'cat > /workspace/path'

# Run command on pod
ssh -p $RUNPOD_PORT -i ~/.ssh/id_ed25519 root@195.26.233.96 'cd /workspace/runs/stage1_20250911_131105/code && command'

# Monitor GPU
ssh -p $RUNPOD_PORT -i ~/.ssh/id_ed25519 root@195.26.233.96 'nvidia-smi'
```

---

**Before each session**: Update RUNPOD_PORT and verify pod is running
**After each session**: Stop pod to save costs
