# RunPod Environment Setup - Complete Record

**Date**: 2025-10-06
**Pod Type**: RunPod with network volume (persistent /workspace)
**GPU**: NVIDIA GeForce RTX 4090 (24GB VRAM)
**CUDA**: 12.4

---

## What Was Installed

### 1. Node.js and npm (via nvm)
- **Location**: `/workspace/.nvm/versions/node/v22.20.0/`
- **Node.js**: v22.20.0
- **npm**: 10.9.3
- Installed via `scripts/pod/setup_pod.sh` (already present)

### 2. Codex CLI
```bash
npm install -g @openai/codex
```
- **Version**: codex-cli 0.45.0
- **Location**: `/workspace/.nvm/versions/node/v22.20.0/bin/codex`
- Used for GPT-5 methodology reviews (see `/docs/AUTONOMOUS_CODEX_REVIEWS.md`)

### 3. Python Virtual Environment
```bash
python -m venv /workspace/venv
```
- **Python**: 3.11.10
- **Location**: `/workspace/venv/`
- Isolated from system Python to avoid conflicts

### 4. PyTorch and ML Dependencies
```bash
source /workspace/venv/bin/activate
pip install --upgrade pip wheel setuptools
pip install -r requirements.txt
```

**Key packages installed**:
- **PyTorch**: 2.6.0+cu124 (CUDA 12.4 support)
- **Transformers**: 4.57.0
- **Accelerate**: 1.10.1
- **Bitsandbytes**: 0.48.1 (4-bit quantization)
- **PEFT**: 0.17.1 (LoRA/QLoRA)
- **Datasets**: 4.1.1 (HuggingFace datasets)
- **scipy**: 1.16.2
- **statsmodels**: 0.14.5
- **pandas**: 2.3.3
- **tqdm**: 4.67.1

Full list in `requirements.txt`

---

## Directory Structure Created

All under `/workspace` (persistent storage):

```
/workspace/
├── home/                          # HOME directory
├── .config/                       # XDG_CONFIG_HOME
├── .cache/
│   ├── huggingface/
│   │   ├── datasets/             # HF_DATASETS_CACHE
│   │   └── transformers/         # TRANSFORMERS_CACHE
│   └── torch/                    # TORCH_HOME
├── .nvm/                         # Node Version Manager
├── venv/                         # Python virtual environment
├── models/                       # Pre-downloaded model snapshots
├── artifacts/                    # Training outputs (checkpoints)
├── data/                         # Generated datasets
├── logs/                         # Training logs
├── results/                      # Evaluation results
├── checkpoints/                  # Intermediate training states
├── pod_env.sh                    # Environment variables
├── setup_session.sh              # Session initialization script
└── cai-constitution-bootstrap/   # Project repository
```

---

## Environment Variables

Set via `/workspace/pod_env.sh` (loaded on each session):

```bash
export HOME=/workspace/home
export XDG_CONFIG_HOME=/workspace/.config
export HF_HOME=/workspace/.cache/huggingface
export TRANSFORMERS_CACHE=/workspace/.cache/huggingface/transformers
export HF_DATASETS_CACHE=/workspace/.cache/huggingface/datasets
export TORCH_HOME=/workspace/.cache/torch
export NVM_DIR=/workspace/.nvm
export PATH="$HOME/.local/bin:/workspace/.local/bin:$PATH"
```

---

## Scripts Created

### 1. `/workspace/setup_session.sh`
**Purpose**: Source at the beginning of each pod session
**Usage**:
```bash
source /workspace/setup_session.sh
```

**What it does**:
- Loads environment variables from `pod_env.sh`
- Activates Python virtual environment
- Changes to project directory
- Shows quick status check

### 2. `/workspace/cai-constitution-bootstrap/scripts/pod/validate_setup.py`
**Purpose**: Comprehensive environment validation
**Usage**:
```bash
python scripts/pod/validate_setup.py
```

**What it checks**:
- Environment variables (HOME, HF_*, TORCH_HOME, etc.)
- Directory structure
- Python packages (torch, transformers, accelerate, etc.)
- GPU availability and CUDA version
- Git configuration
- Node.js and Codex CLI

---

## Git Configuration

Already configured by `setup_pod.sh`:
- **User**: RunPod User <runpod@example.local>
- **SSH keys**: `/workspace/.ssh/` (if present)
- **Safe directory**: `/workspace/cai-constitution-bootstrap`

---

## Session Workflow

### Starting a New Session

1. **Source environment**:
   ```bash
   source /workspace/setup_session.sh
   ```

2. **Verify setup** (optional):
   ```bash
   python scripts/pod/validate_setup.py
   ```

3. **Start working**:
   - All caches persist across sessions
   - Virtual environment auto-activates
   - GPU ready for use

### Before Running Training

1. **Pre-download models** (recommended to avoid repeated network pulls):
   ```bash
   huggingface-cli snapshot-download Qwen/Qwen2.5-32B \
     --local-dir /workspace/models/Qwen2.5-32B \
     --local-dir-use-symlinks False
   ```

2. **Point code to local model path**:
   ```python
   model_path = "/workspace/models/Qwen2.5-32B"
   ```

---

## Validation Results

**Date**: 2025-10-06
**Status**: ✓ All checks passed

```
✓ PASS: Environment Variables
✓ PASS: Directory Structure
✓ PASS: Python Packages
✓ PASS: GPU (NVIDIA GeForce RTX 4090, 25.4 GB, CUDA 12.4)
✓ PASS: Git
✓ PASS: Node.js/Codex
```

---

## Notes

### Avoiding apt/apt-get
- All installations used pip (Python) and npm (Node.js)
- No system package manager required
- Everything installed to `/workspace` for persistence

### Package Versions Pinned
- See `requirements.txt` for exact versions
- PyTorch with CUDA 12.4 (matches driver)
- Transformers 4.57.0 (latest stable)

### Future GPU Pods
When switching to a different pod for training:
1. Ensure pod has network volume mounted at `/workspace`
2. Run `source /workspace/setup_session.sh`
3. Validate with `python scripts/pod/validate_setup.py`
4. Environment should be identical

---

## Troubleshooting

### Virtual environment not activating
```bash
source /workspace/venv/bin/activate
```

### Environment variables not set
```bash
source /workspace/pod_env.sh
```

### GPU not detected
```bash
nvidia-smi  # Verify GPU is attached to pod
```

### Package import errors
```bash
source /workspace/setup_session.sh
python -c "import torch; print(torch.cuda.is_available())"
```

---

## References

- Initial pod setup: `/workspace/cai-constitution-bootstrap/scripts/pod/setup_pod.sh`
- Pod operations guide: `/workspace/cai-constitution-bootstrap/runbooks/POD_OPERATIONS.md`
- Project standards: `/workspace/cai-constitution-bootstrap/docs/STANDARDS.md`
