#!/bin/bash
# Setup Environment for Constitutional AI Bootstrap Experiment
# Optimized for RunPod A100 80GB with Ubuntu

set -e

echo "🚀 Setting up Constitutional AI Bootstrap Environment"
echo "📊 Target: RunPod A100 SXM 80GB"
echo ""

# Create project directories
echo "📁 Creating project structure..."
mkdir -p /workspace/MaximalCAI/{data,checkpoints,logs}/{stage1,stage2,stage3,stage4,stage5,stage6}
mkdir -p /workspace/MaximalCAI/scripts/utils
mkdir -p /workspace/MaximalCAI/results

# Update system packages
echo "🔄 Updating system packages..."
apt-get update -qq
apt-get install -y git-lfs tree htop nvtop curl wget

# Setup Git LFS
git lfs install

# Install Python dependencies
echo "🐍 Installing Python dependencies..."

# Core ML stack
pip install --upgrade pip
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Unsloth for efficient training
pip install "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git"

# Hugging Face ecosystem
pip install transformers>=4.36.0
pip install datasets
pip install accelerate
pip install peft

# Training frameworks
pip install trl
pip install bitsandbytes

# Utilities
pip install wandb
pip install matplotlib seaborn
pip install pandas numpy
pip install tqdm
pip install python-dotenv
pip install requests

# Optional: Flash attention for memory efficiency
pip install flash-attn --no-build-isolation

# Verify installations
echo ""
echo "✅ Verifying installations..."

echo "🔥 PyTorch version:"
python -c "import torch; print(f'PyTorch: {torch.__version__}')"
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"
python -c "import torch; print(f'GPU count: {torch.cuda.device_count()}')"

echo "🤗 Hugging Face versions:"
python -c "import transformers; print(f'Transformers: {transformers.__version__}')"
python -c "import datasets; print(f'Datasets: {datasets.__version__}')"

echo "⚡ Unsloth version:"
python -c "import unsloth; print(f'Unsloth: {unsloth.__version__}')"

echo "🔧 TRL version:"
python -c "import trl; print(f'TRL: {trl.__version__}')"

# GPU information
echo ""
echo "🎮 GPU Information:"
nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv,noheader,nounits

# Memory information
echo ""
echo "💾 System Memory:"
free -h

# Disk space information
echo ""
echo "💿 Disk Space:"
df -h /workspace

# Set environment variables
echo ""
echo "🔧 Setting environment variables..."
export TOKENIZERS_PARALLELISM=false
export TRANSFORMERS_CACHE=/workspace/hf_cache
export HF_HOME=/workspace/hf_cache
mkdir -p $TRANSFORMERS_CACHE

# Create a simple test script
cat > /workspace/test_setup.py << 'EOF'
#!/usr/bin/env python3
"""Test script to verify the environment setup"""

import torch
import transformers
import unsloth
from unsloth import FastLanguageModel

def test_environment():
    print("🧪 Testing environment setup...")
    
    # Test CUDA
    print(f"✅ CUDA available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"✅ GPU: {torch.cuda.get_device_name()}")
        print(f"✅ GPU memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
    
    # Test Unsloth model loading (very small model for test)
    try:
        model, tokenizer = FastLanguageModel.from_pretrained(
            model_name="unsloth/tinyllama-bnb-4bit",
            max_seq_length=512,
            dtype=None,
            load_in_4bit=True,
        )
        print("✅ Unsloth model loading works")
        del model, tokenizer
        torch.cuda.empty_cache()
    except Exception as e:
        print(f"❌ Unsloth test failed: {e}")
    
    print("🎉 Environment setup complete!")

if __name__ == "__main__":
    test_environment()
EOF

chmod +x /workspace/test_setup.py

echo ""
echo "🎉 Environment setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Run: python /workspace/test_setup.py"
echo "2. Clone your project: git clone <repo> /workspace/MaximalCAI"
echo "3. Start with Stage 1: python scripts/generate_stage1_data.py"
echo ""
echo "💰 Cost: ~$1.74/hour for A100 80GB"
echo "🔍 Monitor with: nvtop (GPU) or htop (CPU)"
echo ""
echo "⚠️  Remember to STOP the pod when not in use!"