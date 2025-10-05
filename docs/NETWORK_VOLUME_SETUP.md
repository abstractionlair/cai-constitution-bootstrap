# Network Volume Setup Guide

**Purpose**: Create a self-contained, persistent environment on a RunPod network volume that makes fresh pods "just work".

**Status**: ✅ Implemented (2025-10-05)

---

## Why Network Volume?

**Problems it solves**:
1. ❌ `/workspace` has Xet/MooseFS write quotas → ✅ Network volume uses standard filesystem
2. ❌ `/tmp` lost on pod termination → ✅ Network volume persists across terminations
3. ❌ Limited `/tmp` capacity (20-30GB) → ✅ Network volume sized as needed (100GB)
4. ❌ 10-15 min setup per new pod → ✅ 30 second activation per new pod
5. ❌ Risk of losing work → ✅ Everything persists automatically

**Cost**: ~$10-20/month for 100GB (~3-7% of $300 experiment budget)

---

## Quick Start

### First Time Setup (Run Once)

1. **Create network volume in RunPod dashboard**:
   - Go to Storage → Create Network Volume
   - Name: `maximalcai-experiment`
   - Size: 100GB
   - Region: Same as your pods

2. **Launch pod with volume attached**:
   - Select pod type (H100, A100, etc.)
   - Under "Storage", select your volume
   - Start pod

3. **Run setup script**:
   ```bash
   cd /workspace/maximalcai-experiment

   # Download setup script
   curl -O https://raw.githubusercontent.com/abstractionlair/cai-constitution-bootstrap/main/scripts/setup_network_volume.sh
   chmod +x setup_network_volume.sh

   # Run setup (takes ~5-10 minutes)
   ./setup_network_volume.sh
   ```

4. **Activate environment**:
   ```bash
   source activate_pod.sh
   ```

### Every New Pod (After Termination)

**That's it! Just 2 commands:**

```bash
cd /workspace/maximalcai-experiment
source activate_pod.sh
```

Everything persists: code, packages, credentials, config. Ready to work in 30 seconds.

---

## What Gets Installed on Network Volume

```
/workspace/maximalcai-experiment/
├── cai-constitution-bootstrap/        # Git repo with all code
├── python-env/                        # Virtual environment
│   ├── bin/python3                    # Python 3.x
│   ├── lib/                           # All pip packages:
│   │   ├── torch                      #   - PyTorch (CUDA 12.1)
│   │   ├── transformers               #   - HuggingFace Transformers
│   │   ├── accelerate                 #   - Accelerate (multi-GPU)
│   │   ├── bitsandbytes               #   - BitsAndBytes (quantization)
│   │   ├── peft                       #   - PEFT (LoRA)
│   │   └── ...                        #   - All other dependencies
├── node_modules/                      # npm global packages
│   ├── bin/
│   │   └── claude                     # Claude Code CLI
│   └── @anthropic-ai/
│       └── claude-code/               # Claude Code package
├── .claude/                           # Claude Code config
│   └── config.json                    # Settings (model, editor, etc.)
├── .credentials/                      # Secured credentials (chmod 700)
│   ├── git-config                     # Git user.name and user.email
│   ├── github-token                   # GitHub PAT (chmod 600)
│   └── anthropic-key                  # Anthropic API key (optional, chmod 600)
├── .ssh/                              # SSH keys (stored at /workspace/.ssh)
│   ├── id_ed25519                     # Private key (copied to ~/.ssh with chmod 600)
│   ├── id_ed25519.pub                 # Public key
│   └── known_hosts                    # Known hosts file
├── artifacts/                         # Generated data (persists!)
│   ├── sample_sft_data_*.jsonl
│   ├── sft_data_*.jsonl
│   └── ...
├── activate_pod.sh                    # Quick activation script
└── setup_network_volume.sh            # Initial setup script (saved for reference)
```

---

## What `activate_pod.sh` Does

When you run `source activate_pod.sh`, it:

1. ✅ Activates Python virtual environment
2. ✅ Adds Node.js/npm binaries to PATH
3. ✅ Configures git credentials (name, email)
4. ✅ Sets up GitHub token for authenticated pushes
5. ✅ Loads Anthropic API key (if saved)
6. ✅ Copies SSH keys from `/workspace/.ssh` to `~/.ssh` with correct permissions
7. ✅ Links Claude Code config
8. ✅ Sets MODEL_PATH to shared HuggingFace cache
9. ✅ Changes to repository directory
10. ✅ Checks for git updates

**Total time**: ~5 seconds

---

## Workflow Examples

### Generate Sample Data
```bash
# On any pod (first or subsequent)
cd /workspace/maximalcai-experiment
source activate_pod.sh

# Generate samples (writes to artifacts/ on network volume)
python3 scripts/generate_sample_data.py --count 100

# Results persist! Safe to terminate pod.
```

### Generate Full Dataset (Multi-GPU)
```bash
# Launch pod with 4x GPUs, attach volume
cd /workspace/maximalcai-experiment
source activate_pod.sh

# Generate 15k examples in parallel
accelerate launch --multi_gpu scripts/generate_data_parallel.py --count 15000

# Artifacts saved to network volume, persist across terminations
ls -lh artifacts/
```

### Update Code from Git
```bash
cd /workspace/maximalcai-experiment
source activate_pod.sh

# Pull latest changes
git pull

# Credentials already configured, no re-authentication needed
```

### Commit Results (Claude Code)
```bash
cd /workspace/maximalcai-experiment
source activate_pod.sh

# Claude Code can commit (GitHub token configured)
git add artifacts/sft_data_*.jsonl
git commit -m "Add 15k training examples

- Generated with 4x H100 in parallel
- QC metrics: 98% delimiter detection, 0.2% contamination
- Ready for SFT training

🤖 Generated with Claude Code on RunPod"

git push  # Authenticated via stored token
```

---

## Model Cache Strategy

**HuggingFace model cache**: Still at `/workspace/huggingface_cache/`

**Why not on network volume?**
- Model is 30GB+ (would use most of 50GB volume)
- Model is already cached on most RunPod pods
- We only need READ access (no writes)
- Shared cache means faster pod startup

**How `activate_pod.sh` handles it**:
```bash
# Auto-detects cached Qwen model and sets MODEL_PATH
export MODEL_PATH=/workspace/huggingface_cache/hub/models--Qwen--Qwen2.5-32B/snapshots/<SHA>
```

**If model not cached on pod**:
```bash
# Will download to /workspace/huggingface_cache/ on first use
# Subsequent pods with same cache will skip download
```

---

## Security Notes

### Credentials Storage

**What's stored**:
- Git user name and email (not sensitive)
- GitHub personal access token (sensitive)
- Anthropic API key (sensitive, optional)
- SSH private keys at `/workspace/.ssh` (sensitive)

**Protection**:
- `.credentials/` directory: chmod 700 (owner-only access)
- Token files: chmod 600 (owner-only read/write)
- SSH keys: Stored at `/workspace/.ssh`, copied to `~/.ssh` with chmod 600 on activation
- Network volume: Only accessible from your pods

**Why SSH keys work this way**:
- Network volumes often can't enforce strict Unix permissions (NFS/similar)
- SSH requires private keys to be chmod 600 or refuses to use them
- Solution: Store keys at `/workspace/.ssh`, `activate_pod.sh` copies to `~/.ssh/` with correct perms
- Automatic and transparent

**Risks**:
- If someone gains access to your RunPod account, they can read credentials
- Mitigated by: RunPod account security, MFA, token scoping

**Token scoping recommendations**:
- GitHub PAT: Scope to `repo` only, set expiration (30-90 days)
- Anthropic key: Not needed on pod if using chat subscription

### What NOT to Store

❌ Don't store on network volume:
- Production secrets
- API keys for unrelated projects
- SSH keys for production systems (only project-specific keys)

✅ This setup is safe for:
- Research/experiment projects
- Short-lived GPU pods
- Public or personal repositories

---

## Troubleshooting

### "Network volume not found"
- Check volume is attached to pod in RunPod dashboard
- Verify volume name matches: `maximalcai-experiment`
- Check mount point: `ls /workspace/`

### "Python environment not found"
- Run `setup_network_volume.sh` first (one-time setup)
- Check volume has space: `df -h /workspace/maximalcai-experiment`

### "Claude not found after activation"
- Ensure you used `source activate_pod.sh` (not `./activate_pod.sh`)
- Check PATH: `echo $PATH | grep node_modules`
- Manual fix: `export PATH="/workspace/maximalcai-experiment/node_modules/bin:$PATH"`

### "Git credentials not working"
- Check credentials exist: `ls -la /workspace/maximalcai-experiment/.credentials/`
- Re-run setup: `cd /workspace/maximalcai-experiment && ./setup_network_volume.sh`
- Test git: `git config user.name`

### "MODEL_PATH not set"
- Manually set: `export MODEL_PATH=/workspace/huggingface_cache/hub/models--Qwen--Qwen2.5-32B/snapshots/<SHA>`
- Find SHA: `ls /workspace/huggingface_cache/hub/models--Qwen--Qwen2.5-32B/snapshots/`
- Or let script download: MODEL_PATH defaults to `Qwen/Qwen2.5-32B` if not set

### "Volume full"
- Check usage: `df -h /workspace/maximalcai-experiment`
- Clean old artifacts: `rm artifacts/sample_*.jsonl`
- Increase volume size in RunPod dashboard (can resize without data loss)

---

## Cost Analysis

### Network Volume Cost
- **Storage**: $0.10-0.20/GB/month
- **50GB**: ~$5-10/month
- **2-week experiment**: ~$2.50-5 total

### Savings from Faster Setup
- **Old workflow**: 10-15 min setup per pod
- **New workflow**: 30 sec activation per pod
- **Savings**: ~10-15 min per pod restart
- **Value**: At $2-5/hr GPU cost, saves $0.50-1.00 per restart

### Break-Even
After ~5 pod recreations, network volume pays for itself in time savings alone.

**Plus**:
- Zero risk of data loss
- No manual file transfers
- Can work across multiple pod sessions seamlessly

---

## Comparison: Old vs New Workflow

| Task | Without Network Volume | With Network Volume |
|------|----------------------|-------------------|
| **Initial setup** | 10-15 min | 5-10 min (one-time) |
| **New pod setup** | 10-15 min | 30 seconds |
| **Install packages** | Every pod | One-time |
| **Configure credentials** | Every pod | One-time |
| **Install Claude Code** | Every pod | One-time |
| **Write quotas** | ⚠️ Workaround (/tmp) | ✅ No issues |
| **/tmp capacity** | ⚠️ Limited (20-30GB) | ✅ Not needed |
| **Data persistence** | ❌ Manual download | ✅ Automatic |
| **Pod termination** | 😰 Hope you downloaded | 😌 Everything persists |
| **Cost** | $0 | ~$5-10 total |

---

## Next Steps

1. ✅ Create network volume in RunPod dashboard
2. ✅ Run `setup_network_volume.sh` (one-time)
3. ✅ Test with `source activate_pod.sh`
4. ✅ Generate sample data to verify
5. ✅ Terminate pod and recreate to test persistence
6. ✅ Proceed with full experiment

---

**Questions?** See `/docs/STANDARDS.md` or ask the user.
