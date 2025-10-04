#!/bin/bash
# Setup RunPod environment for Constitutional AI Bootstrap
# This script installs all dependencies and sets up Claude Code

set -e  # Exit on any error

echo "════════════════════════════════════════════════════════════════"
echo "  RunPod Environment Setup for Constitutional AI Bootstrap"
echo "════════════════════════════════════════════════════════════════"
echo ""

# Check we're on the pod (has /workspace)
if [ ! -d "/workspace" ]; then
    echo "❌ ERROR: /workspace not found. Are you on RunPod?"
    echo "   This script should be run ON the pod, not locally."
    exit 1
fi

echo "✅ Running on RunPod pod"
echo ""

# ============================================================================
# 1. System Information
# ============================================================================

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "1. System Information"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo "Hostname: $(hostname)"
echo "Python: $(python3 --version)"
echo "Pip: $(pip --version)"

if command -v nvcc &> /dev/null; then
    echo "CUDA: $(nvcc --version | grep release | awk '{print $5}' | sed 's/,//')"
else
    echo "CUDA: nvcc not found"
fi

if command -v nvidia-smi &> /dev/null; then
    echo ""
    nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
else
    echo "WARNING: nvidia-smi not found"
fi

echo ""
echo "Disk space:"
df -h /workspace | tail -1
echo ""

# ============================================================================
# 2. Python Dependencies
# ============================================================================

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "2. Installing Python Dependencies"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo ""
echo "Upgrading pip..."
pip install --upgrade pip -q

echo ""
echo "Installing ML frameworks (this may take a few minutes)..."
pip install -q \
    torch>=2.1.0 \
    transformers>=4.35.0 \
    accelerate>=0.24.0

echo ""
echo "Installing quantization and training libraries..."
pip install -q \
    bitsandbytes>=0.41.0 \
    peft>=0.6.0

echo ""
echo "Installing HuggingFace utilities..."
pip install -q \
    hf-transfer>=0.1.0 \
    datasets>=2.14.0

echo ""
echo "Installing scientific computing libraries..."
pip install -q \
    numpy>=1.24.0 \
    scipy>=1.11.0 \
    statsmodels>=0.14.0

echo ""
echo "Installing utilities..."
pip install -q \
    tqdm>=4.66.0

echo ""
echo "✅ Python dependencies installed"
echo ""

# Verify critical imports
echo "Verifying installations..."
python3 << 'PYEOF'
import sys
try:
    import torch
    import transformers
    import bitsandbytes
    import peft
    import scipy
    import numpy
    print("✅ All critical imports successful")
    print(f"   PyTorch: {torch.__version__}")
    print(f"   Transformers: {transformers.__version__}")
    if torch.cuda.is_available():
        print(f"   CUDA available: {torch.version.cuda}")
        print(f"   GPU: {torch.cuda.get_device_name(0)}")
    else:
        print("   ⚠️  CUDA not available")
except ImportError as e:
    print(f"❌ Import failed: {e}")
    sys.exit(1)
PYEOF

echo ""

# ============================================================================
# 3. Claude Code Installation
# ============================================================================

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "3. Installing Claude Code"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Check if already installed
if command -v claude &> /dev/null; then
    echo "Claude Code already installed: $(which claude)"
    echo "Version: $(claude --version 2>/dev/null || echo 'unknown')"
    read -p "Reinstall? (y/N): " reinstall
    if [[ ! $reinstall =~ ^[Yy]$ ]]; then
        echo "Skipping Claude Code installation"
    else
        echo "Reinstalling Claude Code..."
        npm install -g @anthropic-ai/claude-code
    fi
else
    echo ""
    echo "Installing Claude Code via npm..."

    # Check if npm is available
    if ! command -v npm &> /dev/null; then
        echo "❌ npm not found. Installing Node.js and npm..."

        # Try to install nodejs (method depends on OS)
        if command -v apt-get &> /dev/null; then
            apt-get update -qq
            apt-get install -y -qq nodejs npm
        elif command -v yum &> /dev/null; then
            yum install -y -q nodejs npm
        else
            echo "❌ Cannot install Node.js automatically."
            echo "   Please install Node.js and npm manually, then run:"
            echo "   npm install -g @anthropic-ai/claude-code"
            exit 1
        fi
    fi

    echo "Installing Claude Code..."
    npm install -g @anthropic-ai/claude-code

    echo ""
    echo "✅ Claude Code installed: $(which claude)"
fi

echo ""

# ============================================================================
# 4. Project Setup
# ============================================================================

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "4. Project Setup"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

cd /workspace

# Clone repo if not exists
if [ ! -d "MaximalCAI" ]; then
    echo ""
    echo "Cloning repository..."
    git clone https://github.com/abstractionlair/cai-constitution-bootstrap.git MaximalCAI
    echo "✅ Repository cloned"
else
    echo ""
    echo "Repository already exists at /workspace/MaximalCAI"
    cd MaximalCAI

    echo "Pulling latest changes..."
    git pull
    echo "✅ Repository updated"
fi

cd /workspace/MaximalCAI

echo ""
echo "Creating directory structure..."
mkdir -p artifacts checkpoints data logs
mkdir -p data/raw data/filtered data/final

echo "✅ Directories created:"
echo "   - artifacts/  (evaluation results)"
echo "   - checkpoints/  (model weights)"
echo "   - data/  (training data)"
echo "   - logs/  (session logs)"

echo ""

# ============================================================================
# 5. Environment Configuration
# ============================================================================

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "5. Environment Configuration"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo ""
echo "Setting environment variables..."

# Add to .bashrc if not already there
if ! grep -q "CAI_BASE_DIR" ~/.bashrc; then
    echo "" >> ~/.bashrc
    echo "# Constitutional AI Bootstrap" >> ~/.bashrc
    echo "export CAI_BASE_DIR=/workspace/MaximalCAI" >> ~/.bashrc
    echo "export HF_HOME=/workspace/huggingface_cache" >> ~/.bashrc
    echo "export TRANSFORMERS_CACHE=/workspace/huggingface_cache" >> ~/.bashrc
    echo "✅ Added environment variables to ~/.bashrc"
else
    echo "✅ Environment variables already in ~/.bashrc"
fi

# Set for current session
export CAI_BASE_DIR=/workspace/MaximalCAI
export HF_HOME=/workspace/huggingface_cache
export TRANSFORMERS_CACHE=/workspace/huggingface_cache

echo ""
echo "Environment variables:"
echo "  CAI_BASE_DIR=$CAI_BASE_DIR"
echo "  HF_HOME=$HF_HOME"
echo "  TRANSFORMERS_CACHE=$TRANSFORMERS_CACHE"

echo ""

# Create HF cache directory
mkdir -p /workspace/huggingface_cache
echo "✅ HuggingFace cache directory created"

echo ""

# ============================================================================
# 6. Session Manifest
# ============================================================================

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "6. Creating Session Manifest"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

cd /workspace/MaximalCAI

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
MANIFEST_FILE="artifacts/session_setup_${TIMESTAMP}.txt"

cat > "$MANIFEST_FILE" << EOF
RunPod Environment Setup
========================

Date: $(date)
Hostname: $(hostname)

Git Information:
  Branch: $(git rev-parse --abbrev-ref HEAD)
  Commit: $(git rev-parse HEAD)
  Short:  $(git rev-parse --short HEAD)

System:
  Python: $(python3 --version)
  PyTorch: $(python3 -c "import torch; print(torch.__version__)")
  Transformers: $(python3 -c "import transformers; print(transformers.__version__)")
  CUDA: $(python3 -c "import torch; print(torch.version.cuda if torch.cuda.is_available() else 'N/A')")

GPU:
$(nvidia-smi --query-gpu=index,name,memory.total,memory.free --format=csv,noheader 2>/dev/null || echo "  N/A")

Disk:
$(df -h /workspace | tail -1)

Setup complete: $(date)
EOF

echo ""
echo "✅ Session manifest saved: $MANIFEST_FILE"
cat "$MANIFEST_FILE"

echo ""

# ============================================================================
# 7. Final Verification
# ============================================================================

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "7. Final Verification"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo ""
echo "Checking critical components..."

# Check Python packages
python3 << 'PYEOF'
import sys
checks = []

try:
    import torch
    checks.append(("PyTorch", True, torch.__version__))
except:
    checks.append(("PyTorch", False, ""))

try:
    import transformers
    checks.append(("Transformers", True, transformers.__version__))
except:
    checks.append(("Transformers", False, ""))

try:
    import bitsandbytes
    checks.append(("BitsAndBytes", True, ""))
except:
    checks.append(("BitsAndBytes", False, ""))

try:
    import peft
    checks.append(("PEFT", True, ""))
except:
    checks.append(("PEFT", False, ""))

try:
    import torch
    cuda = torch.cuda.is_available()
    checks.append(("CUDA", cuda, torch.version.cuda if cuda else ""))
except:
    checks.append(("CUDA", False, ""))

all_ok = all(ok for _, ok, _ in checks)

for name, ok, version in checks:
    status = "✅" if ok else "❌"
    ver_str = f" ({version})" if version else ""
    print(f"  {status} {name}{ver_str}")

sys.exit(0 if all_ok else 1)
PYEOF

PYCHECK=$?

# Check Claude Code
if command -v claude &> /dev/null; then
    echo "  ✅ Claude Code ($(which claude))"
    CLAUDE_OK=0
else
    echo "  ❌ Claude Code"
    CLAUDE_OK=1
fi

# Check directories
if [ -d "/workspace/MaximalCAI" ]; then
    echo "  ✅ Project directory"
    DIR_OK=0
else
    echo "  ❌ Project directory"
    DIR_OK=1
fi

echo ""

# ============================================================================
# Summary
# ============================================================================

if [ $PYCHECK -eq 0 ] && [ $CLAUDE_OK -eq 0 ] && [ $DIR_OK -eq 0 ]; then
    echo "════════════════════════════════════════════════════════════════"
    echo "  ✅ SETUP COMPLETE - Ready for GPU work!"
    echo "════════════════════════════════════════════════════════════════"
    echo ""
    echo "Next steps:"
    echo "  1. cd /workspace/MaximalCAI"
    echo "  2. source ~/.bashrc  # Load environment variables"
    echo "  3. python3 scripts/smoke_test_migration.py  # Verify setup"
    echo ""
    echo "To launch Claude Code:"
    echo "  claude"
    echo ""
    echo "To start a new session:"
    echo "  cd /workspace/MaximalCAI"
    echo "  claude"
    echo ""
    exit 0
else
    echo "════════════════════════════════════════════════════════════════"
    echo "  ⚠️  SETUP INCOMPLETE - Some components failed"
    echo "════════════════════════════════════════════════════════════════"
    echo ""
    echo "Please check the errors above and retry."
    echo ""
    exit 1
fi
