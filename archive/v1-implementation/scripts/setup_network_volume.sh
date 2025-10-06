#!/bin/bash
# Setup Network Volume - Run ONCE on first pod
#
# This script sets up a self-contained environment on a RunPod network volume
# that persists across pod terminations and makes new pods "just work".
#
# USAGE:
#   1. Create 50GB network volume in RunPod dashboard (name: maximalcai-experiment)
#   2. Launch pod with volume attached
#   3. cd /workspace/maximalcai-experiment
#   4. curl -O https://raw.githubusercontent.com/abstractionlair/cai-constitution-bootstrap/main/scripts/setup_network_volume.sh
#   5. chmod +x setup_network_volume.sh
#   6. ./setup_network_volume.sh
#
# After this completes, future pods only need to run activate_pod.sh

set -e  # Exit on error

# Auto-detect volume root or use provided argument
if [ -n "$1" ]; then
    VOLUME_ROOT="$1"
elif [ -f "$(pwd)/cai-constitution-bootstrap/.git/config" ] || [ -f "$(pwd)/.git/config" ]; then
    # Running from volume root or repo directory
    VOLUME_ROOT="$(cd "$(dirname "$(pwd)/cai-constitution-bootstrap")" && pwd)"
else
    # Default to maximalcai-experiment (backward compatible)
    VOLUME_ROOT="/workspace/maximalcai-experiment"
fi

REPO_DIR="$VOLUME_ROOT/cai-constitution-bootstrap"
PYTHON_ENV="$VOLUME_ROOT/python-env"
NODE_PREFIX="$VOLUME_ROOT/node_modules"
CREDENTIALS_DIR="$VOLUME_ROOT/.credentials"

echo "=========================================================================="
echo "Network Volume Setup - Constitutional AI Bootstrap"
echo "=========================================================================="
echo "This will install everything on the network volume for persistence."
echo "After this completes, new pods will 'just work' with activate_pod.sh."
echo ""
echo "Volume root: $VOLUME_ROOT"
echo ""

# Verify we're in the right place
if [ ! -d "$VOLUME_ROOT" ]; then
    echo "❌ Error: $VOLUME_ROOT not found"
    echo "   Make sure network volume is attached and named 'maximalcai-experiment'"
    exit 1
fi

cd "$VOLUME_ROOT"

# ============================================================================
# 1. Clone Repository
# ============================================================================
echo ""
echo "=== Step 1: Clone Repository ==="
if [ -d "$REPO_DIR" ]; then
    echo "Repository already exists, pulling latest..."
    cd "$REPO_DIR"
    git pull
else
    echo "Cloning repository..."
    git clone https://github.com/abstractionlair/cai-constitution-bootstrap.git
    cd "$REPO_DIR"
fi
echo "✅ Repository ready: $REPO_DIR"

# ============================================================================
# 2. Python Environment
# ============================================================================
echo ""
echo "=== Step 2: Python Virtual Environment ==="
if [ -d "$PYTHON_ENV" ]; then
    echo "Python environment already exists: $PYTHON_ENV"
    read -p "Recreate? (y/N): " RECREATE
    if [ "$RECREATE" = "y" ] || [ "$RECREATE" = "Y" ]; then
        rm -rf "$PYTHON_ENV"
        python3 -m venv "$PYTHON_ENV"
    fi
else
    echo "Creating Python virtual environment: $PYTHON_ENV"
    python3 -m venv "$PYTHON_ENV"
fi

echo "Activating environment and installing packages..."
source "$PYTHON_ENV/bin/activate"

# Upgrade pip
pip install --upgrade pip wheel setuptools

# Install core dependencies
echo "Installing PyTorch and transformers..."
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
pip install transformers accelerate bitsandbytes datasets peft

# Install utilities
pip install numpy scipy pandas tqdm jq

echo "✅ Python environment ready: $PYTHON_ENV"

# ============================================================================
# 3. Node.js and npm
# ============================================================================
echo ""
echo "=== Step 3: Node.js and npm ==="
if command -v npm &> /dev/null; then
    echo "npm already installed: $(npm --version)"
else
    echo "Installing Node.js and npm..."
    if command -v apt-get &> /dev/null; then
        apt-get update -qq
        apt-get install -y -qq nodejs npm
    else
        echo "⚠️  apt-get not available, install Node.js manually"
        exit 1
    fi
fi

# Configure npm to use network volume for global installs
mkdir -p "$NODE_PREFIX"
npm config set prefix "$NODE_PREFIX"
echo "✅ npm configured to use: $NODE_PREFIX"

# ============================================================================
# 4. Claude Code Installation
# ============================================================================
echo ""
echo "=== Step 4: Claude Code ==="
echo "Installing Claude Code to network volume..."
npm install -g @anthropic-ai/claude-code

CLAUDE_PATH="$NODE_PREFIX/bin/claude"
if [ -x "$CLAUDE_PATH" ]; then
    echo "✅ Claude Code installed: $CLAUDE_PATH"
else
    echo "⚠️  Claude Code not found at expected location: $CLAUDE_PATH"
    echo "   Check npm prefix: $(npm config get prefix)"
fi

# ============================================================================
# 5. Credentials Setup
# ============================================================================
echo ""
echo "=== Step 5: Credentials ==="
mkdir -p "$CREDENTIALS_DIR"
chmod 700 "$CREDENTIALS_DIR"

# Git credentials
echo ""
echo "Git Configuration:"
read -p "  Git name (default: Scott McGuire): " GIT_NAME
GIT_NAME=${GIT_NAME:-"Scott McGuire"}

read -p "  Git email: " GIT_EMAIL

echo "[user]" > "$CREDENTIALS_DIR/git-config"
echo "	name = $GIT_NAME" >> "$CREDENTIALS_DIR/git-config"
echo "	email = $GIT_EMAIL" >> "$CREDENTIALS_DIR/git-config"

echo "✅ Git config saved: $CREDENTIALS_DIR/git-config"

# GitHub token
echo ""
echo "GitHub Token (for Claude Code commits):"
read -sp "  Enter token (or press enter to skip): " GITHUB_TOKEN
echo ""

if [ -n "$GITHUB_TOKEN" ]; then
    echo "https://$GITHUB_TOKEN@github.com" > "$CREDENTIALS_DIR/github-token"
    chmod 600 "$CREDENTIALS_DIR/github-token"
    echo "✅ GitHub token saved: $CREDENTIALS_DIR/github-token"
else
    echo "⏭️  Skipped GitHub token"
fi

# Anthropic API key (optional - pod uses chat subscription)
echo ""
echo "Anthropic API Key (optional - pod typically uses chat subscription):"
read -sp "  Enter API key (or press enter to skip): " ANTHROPIC_KEY
echo ""

if [ -n "$ANTHROPIC_KEY" ]; then
    echo "$ANTHROPIC_KEY" > "$CREDENTIALS_DIR/anthropic-key"
    chmod 600 "$CREDENTIALS_DIR/anthropic-key"
    echo "✅ Anthropic key saved: $CREDENTIALS_DIR/anthropic-key"
else
    echo "⏭️  Skipped Anthropic key"
fi

# SSH keys (check if already in /workspace/.ssh)
echo ""
echo "SSH Keys:"
if [ -d "/workspace/.ssh" ] && [ -f "/workspace/.ssh/id_ed25519" ]; then
    echo "✅ SSH keys found at /workspace/.ssh/"
    echo "   These will be copied to ~/.ssh/ on pod activation"
else
    echo "⚠️  No SSH keys found at /workspace/.ssh/"
    echo "   If you need SSH access from pod, copy keys to /workspace/.ssh/"
    echo "   Example: scp -P <port> ~/.ssh/id_ed25519* root@<pod-ip>:/workspace/.ssh/"
fi

# ============================================================================
# 6. Claude Code Config
# ============================================================================
echo ""
echo "=== Step 6: Claude Code Configuration ==="
CLAUDE_CONFIG="$VOLUME_ROOT/.claude"
mkdir -p "$CLAUDE_CONFIG"

# Create basic config if not exists
if [ ! -f "$CLAUDE_CONFIG/config.json" ]; then
    cat > "$CLAUDE_CONFIG/config.json" << 'EOF'
{
  "model": "claude-sonnet-4-5",
  "editor": "vim"
}
EOF
    echo "✅ Created default Claude config: $CLAUDE_CONFIG/config.json"
else
    echo "✅ Claude config already exists: $CLAUDE_CONFIG/config.json"
fi

# Prompt for Claude Code API key (for pod usage)
echo ""
echo "Claude Code API Key (for pod - uses chat subscription, not API):"
echo "Note: If using chat subscription, leave blank. API key only needed if using API plan."
read -sp "  Enter API key (or press enter to skip): " CLAUDE_API_KEY
echo ""

if [ -n "$CLAUDE_API_KEY" ]; then
    # Store in .claude directory on network volume
    mkdir -p "$CLAUDE_CONFIG"
    echo "$CLAUDE_API_KEY" > "$CLAUDE_CONFIG/api_key"
    chmod 600 "$CLAUDE_CONFIG/api_key"
    echo "✅ Claude API key saved: $CLAUDE_CONFIG/api_key"
    echo "   (Will be symlinked to ~/.claude/api_key on activation)"
else
    echo "⏭️  Skipped Claude API key (using chat subscription)"
fi

# ============================================================================
# 7. Create Activation Script
# ============================================================================
echo ""
echo "=== Step 7: Create Pod Activation Script ==="

cat > "$VOLUME_ROOT/activate_pod.sh" << ACTIVATE_EOF
#!/bin/bash
# Activate Pod - Run on EVERY new pod to activate the environment
#
# USAGE:
#   cd /workspace/<your-volume-name>
#   source activate_pod.sh

# Auto-detect volume root based on script location
SCRIPT_DIR="\$(cd "\$(dirname "\${BASH_SOURCE[0]}")" && pwd)"
VOLUME_ROOT="\$SCRIPT_DIR"
REPO_DIR="$VOLUME_ROOT/cai-constitution-bootstrap"
PYTHON_ENV="$VOLUME_ROOT/python-env"
NODE_PREFIX="$VOLUME_ROOT/node_modules"
CREDENTIALS_DIR="$VOLUME_ROOT/.credentials"
CLAUDE_CONFIG="$VOLUME_ROOT/.claude"

echo "=========================================================================="
echo "Activating Pod - Constitutional AI Bootstrap"
echo "=========================================================================="

# Activate Python environment
if [ -d "$PYTHON_ENV" ]; then
    source "$PYTHON_ENV/bin/activate"
    echo "✅ Python environment activated: $PYTHON_ENV"
else
    echo "❌ Python environment not found: $PYTHON_ENV"
    echo "   Run setup_network_volume.sh first"
    return 1
fi

# Add Node.js binaries to PATH
if [ -d "$NODE_PREFIX/bin" ]; then
    export PATH="$NODE_PREFIX/bin:$PATH"
    export npm_config_prefix="$NODE_PREFIX"
    echo "✅ Node.js environment activated: $NODE_PREFIX"
else
    echo "⚠️  Node.js environment not found: $NODE_PREFIX"
fi

# Configure git from credentials
if [ -f "$CREDENTIALS_DIR/git-config" ]; then
    git config --global include.path "$CREDENTIALS_DIR/git-config"
    echo "✅ Git credentials loaded"
else
    echo "⚠️  Git credentials not found: $CREDENTIALS_DIR/git-config"
fi

# Setup GitHub token if exists
if [ -f "$CREDENTIALS_DIR/github-token" ]; then
    git config --global credential.helper store
    ln -sf "$CREDENTIALS_DIR/github-token" ~/.git-credentials
    chmod 600 ~/.git-credentials
    echo "✅ GitHub token configured"
fi

# Setup Anthropic API key if exists
if [ -f "$CREDENTIALS_DIR/anthropic-key" ]; then
    export ANTHROPIC_API_KEY=$(cat "$CREDENTIALS_DIR/anthropic-key")
    echo "✅ Anthropic API key loaded"
fi

# Setup SSH keys (copy from /workspace/.ssh with proper permissions)
if [ -d "/workspace/.ssh" ]; then
    mkdir -p ~/.ssh
    chmod 700 ~/.ssh

    # Copy private keys
    if [ -f "/workspace/.ssh/id_ed25519" ]; then
        cp /workspace/.ssh/id_ed25519 ~/.ssh/
        chmod 600 ~/.ssh/id_ed25519
        echo "✅ SSH private key configured (id_ed25519)"
    fi

    if [ -f "/workspace/.ssh/id_rsa" ]; then
        cp /workspace/.ssh/id_rsa ~/.ssh/
        chmod 600 ~/.ssh/id_rsa
        echo "✅ SSH private key configured (id_rsa)"
    fi

    # Copy public keys
    if [ -f "/workspace/.ssh/id_ed25519.pub" ]; then
        cp /workspace/.ssh/id_ed25519.pub ~/.ssh/
        chmod 644 ~/.ssh/id_ed25519.pub
    fi

    if [ -f "/workspace/.ssh/id_rsa.pub" ]; then
        cp /workspace/.ssh/id_rsa.pub ~/.ssh/
        chmod 644 ~/.ssh/id_rsa.pub
    fi

    # Copy known_hosts if exists
    if [ -f "/workspace/.ssh/known_hosts" ]; then
        cp /workspace/.ssh/known_hosts ~/.ssh/
        chmod 644 ~/.ssh/known_hosts
    fi

    # Copy config if exists
    if [ -f "/workspace/.ssh/config" ]; then
        cp /workspace/.ssh/config ~/.ssh/
        chmod 600 ~/.ssh/config
    fi
fi

# Link Claude config
if [ -d "$CLAUDE_CONFIG" ]; then
    ln -sf "$CLAUDE_CONFIG" ~/.claude
    echo "✅ Claude config linked"
fi

# Set MODEL_PATH to shared HuggingFace cache
# Update this path based on your cached model snapshot
if [ -d "/workspace/huggingface_cache" ]; then
    # Try to find Qwen model snapshot
    QWEN_PATH=$(find /workspace/huggingface_cache -type d -name "models--Qwen--Qwen2.5-32B" 2>/dev/null | head -1)
    if [ -n "$QWEN_PATH" ]; then
        # Get most recent snapshot
        SNAPSHOT=$(ls -t "$QWEN_PATH/snapshots" | head -1)
        if [ -n "$SNAPSHOT" ]; then
            export MODEL_PATH="$QWEN_PATH/snapshots/$SNAPSHOT"
            echo "✅ MODEL_PATH set: $MODEL_PATH"
        fi
    fi
fi

# Change to repo directory
if [ -d "$REPO_DIR" ]; then
    cd "$REPO_DIR"
    echo "✅ Changed to: $REPO_DIR"

    # Pull latest changes
    echo ""
    echo "Checking for updates..."
    git fetch
    LOCAL=$(git rev-parse HEAD)
    REMOTE=$(git rev-parse @{u} 2>/dev/null || echo $LOCAL)

    if [ "$LOCAL" != "$REMOTE" ]; then
        echo "⚠️  Updates available. Run 'git pull' to update."
    else
        echo "✅ Repository up to date"
    fi
fi

echo ""
echo "=========================================================================="
echo "✅ Pod activated and ready!"
echo "=========================================================================="
echo "Environment:"
echo "  - Python: $(python --version)"
echo "  - PyTorch: $(python -c 'import torch; print(torch.__version__)' 2>/dev/null || echo 'not installed')"
echo "  - Node.js: $(node --version 2>/dev/null || echo 'not installed')"
echo "  - npm: $(npm --version 2>/dev/null || echo 'not installed')"
echo "  - Claude: $(claude --version 2>/dev/null || echo 'not installed')"
echo "  - Git: $(git config user.name) <$(git config user.email)>"
echo ""
echo "Working directory: $(pwd)"
echo ""
echo "Ready to work! Example commands:"
echo "  python3 scripts/generate_sample_data.py --count 100"
echo "  python3 scripts/generate_data_parallel.py --count 15000"
echo ""
ACTIVATE_EOF

chmod +x "$VOLUME_ROOT/activate_pod.sh"
echo "✅ Created: $VOLUME_ROOT/activate_pod.sh"

# ============================================================================
# 8. Summary
# ============================================================================
echo ""
echo "=========================================================================="
echo "✅ Network Volume Setup Complete!"
echo "=========================================================================="
echo ""
echo "What was installed:"
echo "  - Repository: $REPO_DIR"
echo "  - Python env: $PYTHON_ENV"
echo "  - Node.js: $NODE_PREFIX"
echo "  - Claude Code: $NODE_PREFIX/bin/claude"
echo "  - Credentials: $CREDENTIALS_DIR (secured)"
echo "  - Claude config: $CLAUDE_CONFIG"
echo ""
echo "Next steps:"
echo "  1. Activate this pod:"
echo "     source $VOLUME_ROOT/activate_pod.sh"
echo ""
echo "  2. Test everything works:"
echo "     python3 scripts/generate_sample_data.py --count 10"
echo ""
echo "  3. On FUTURE pods (after termination):"
echo "     cd /workspace/maximalcai-experiment"
echo "     source activate_pod.sh"
echo "     # Everything persists! Ready to work immediately."
echo ""
echo "Volume contents:"
ls -lh "$VOLUME_ROOT"
echo ""
echo "=========================================================================="
