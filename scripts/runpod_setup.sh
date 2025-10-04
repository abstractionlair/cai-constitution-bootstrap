#!/bin/bash
# RunPod Quick Setup for Constitutional AI Bootstrap
# Designed for fresh A100 80GB pod with Ubuntu + PyTorch template

set -e  # Exit on any error

echo "🚀 Constitutional AI Bootstrap - RunPod Setup"
echo "=============================================="
echo ""

# Verify we're on RunPod with GPU
if ! command -v nvidia-smi &> /dev/null; then
    echo "❌ Error: nvidia-smi not found. Are you on a GPU pod?"
    exit 1
fi

echo "✅ GPU detected:"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader

echo ""
echo "📦 Installing dependencies..."
echo ""

# Update pip
pip install --upgrade pip -q

# Core dependencies (optimized order for caching)
echo "  Installing transformers ecosystem..."
pip install -q transformers>=4.36.0 tokenizers datasets accelerate

echo "  Installing training frameworks..."
pip install -q torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
pip install -q bitsandbytes peft trl

echo "  Installing Unsloth (efficient training)..."
pip install -q "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git"

echo "  Installing utilities..."
pip install -q pyyaml tqdm python-dotenv requests

# Optional: Flash attention (comment out if issues)
echo "  Installing flash-attention (may take a few minutes)..."
pip install -q flash-attn --no-build-isolation || echo "⚠️  Flash attention install failed (optional, continuing)"

echo ""
echo "🔧 Configuring environment..."

# Set environment variables
export TOKENIZERS_PARALLELISM=false
export TRANSFORMERS_CACHE=/workspace/hf_cache
export HF_HOME=/workspace/hf_cache
mkdir -p $TRANSFORMERS_CACHE

# Add to bashrc for persistence
cat >> ~/.bashrc << 'EOF'

# Constitutional AI Bootstrap environment
export TOKENIZERS_PARALLELISM=false
export TRANSFORMERS_CACHE=/workspace/hf_cache
export HF_HOME=/workspace/hf_cache
export CAI_BASE_DIR=/workspace/MaximalCAI
EOF

echo ""
echo "✅ Verifying installation..."
python3 << 'PYEOF'
import torch
import transformers
print(f"✅ PyTorch: {torch.__version__}")
print(f"✅ CUDA available: {torch.cuda.is_available()}")
print(f"✅ Transformers: {transformers.__version__}")
if torch.cuda.is_available():
    print(f"✅ GPU: {torch.cuda.get_device_name(0)}")
    mem_gb = torch.cuda.get_device_properties(0).total_memory / 1e9
    print(f"✅ GPU Memory: {mem_gb:.1f} GB")
PYEOF

echo ""
echo "📁 Cloning repository..."
cd /workspace
if [ -d "MaximalCAI" ]; then
    echo "⚠️  Directory already exists. Pulling latest..."
    cd MaximalCAI
    git pull
else
    git clone https://github.com/abstractionlair/cai-constitution-bootstrap.git MaximalCAI
    cd MaximalCAI
fi

echo ""
echo "📂 Creating artifact directories..."
mkdir -p artifacts/{sft_data,preference_pairs,models,evaluations,logs}
mkdir -p checkpoints/{stage1_sft,stage1_dpo}

echo ""
echo "🎉 Setup complete!"
echo ""
echo "=========================================="
echo "Next Steps:"
echo "=========================================="
echo ""
echo "1. Review the session plan:"
echo "   cat docs/RUNPOD_SESSION_PLAN.md"
echo ""
echo "2. Start with Phase 1 (Verification):"
echo "   cd /workspace/MaximalCAI"
echo "   python scripts/test_base_model_ultra_clean.py"
echo ""
echo "3. Follow the 9-phase plan in docs/RUNPOD_SESSION_PLAN.md"
echo ""
echo "💰 Cost: ~\$1.74/hour"
echo "⏱️  Estimated time: 9-16 hours total"
echo "💵 Estimated cost: \$15-29"
echo ""
echo "⚠️  REMEMBER TO STOP POD WHEN DONE!"
echo ""
