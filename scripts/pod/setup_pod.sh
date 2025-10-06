#!/usr/bin/env bash
set -euo pipefail

# Pod bootstrap + repo setup script
# - Assumes only /workspace is persistent
# - Installs nvm + Node.js (no apt-get), and Claude Code CLI
# - Configures env to write all caches/configs under /workspace
# - Configures Git SSH (expects keys in /workspace/.ssh) and clones repo

REPO_SSH="git@github.com:abstractionlair/cai-constitution-bootstrap.git"
REPO_HTTPS="https://github.com/abstractionlair/cai-constitution-bootstrap.git"
REPO_DIR="/workspace/cai-constitution-bootstrap"

banner() {
  echo "============================================================"
  echo "$1"
  echo "============================================================"
}

ensure_dir() {
  mkdir -p "$1"
}

write_env_file() {
  local env_file="/workspace/pod_env.sh"
  cat > "$env_file" << 'EOF'
# Pod environment (source me in each session)
export HOME=/workspace/home
export XDG_CONFIG_HOME=/workspace/.config
export HF_HOME=/workspace/.cache/huggingface
export TRANSFORMERS_CACHE=/workspace/.cache/huggingface/transformers
export HF_DATASETS_CACHE=/workspace/.cache/huggingface/datasets
export TORCH_HOME=/workspace/.cache/torch

# nvm (installed to /workspace/.nvm)
export NVM_DIR=/workspace/.nvm
if [ -s "$NVM_DIR/nvm.sh" ]; then . "$NVM_DIR/nvm.sh"; fi
if [ -s "$NVM_DIR/bash_completion" ]; then . "$NVM_DIR/bash_completion"; fi

# Add common bin paths
export PATH="$HOME/.local/bin:/workspace/.local/bin:$PATH"
EOF
  echo "$env_file"
}

configure_layout() {
  banner "[1/7] Configure /workspace layout and env"
  ensure_dir /workspace/home
  ensure_dir /workspace/.config
  ensure_dir /workspace/.cache/huggingface/datasets
  ensure_dir /workspace/.cache/huggingface/transformers
  ensure_dir /workspace/.cache/torch
  ensure_dir /workspace/models
  ensure_dir /workspace/artifacts /workspace/data /workspace/logs /workspace/results /workspace/checkpoints
  local env_file
  env_file=$(write_env_file)
  # shellcheck disable=SC1090
  . "$env_file"
  echo "Wrote env to $env_file"
}

configure_git_and_ssh() {
  banner "[2/7] Configure Git + SSH"
  if ! command -v git >/dev/null 2>&1; then
    echo "ERROR: git is not installed on this image. Please install git or use an image with git preinstalled." >&2
    exit 1
  fi

  # SSH keys expected in /workspace/.ssh
  if [ -d /workspace/.ssh ]; then
    chmod 700 /workspace/.ssh || true
    # Restrict private keys
    if ls /workspace/.ssh/id_* 1>/dev/null 2>&1; then
      chmod 600 /workspace/.ssh/id_* || true
    fi
    # Add GitHub to known_hosts if missing
    if ! grep -q "github.com" /workspace/.ssh/known_hosts 2>/dev/null; then
      echo "Adding github.com to known_hosts"
      ssh-keyscan -t rsa,ecdsa,ed25519 github.com >> /workspace/.ssh/known_hosts 2>/dev/null || true
      chmod 600 /workspace/.ssh/known_hosts || true
    fi
    # Use these keys explicitly for git SSH operations
    git config --global core.sshCommand "ssh -i /workspace/.ssh/id_rsa -o StrictHostKeyChecking=accept-new"
  else
    echo "Note: /workspace/.ssh not found. SSH-based push will not work until keys are provided."
  fi

  # Basic git identity (user may override)
  git config --global user.name "RunPod User"
  git config --global user.email "runpod@example.local"
}

install_nvm_node() {
  banner "[3/7] Install nvm + Node.js (no apt-get)"
  if ! command -v curl >/dev/null 2>&1; then
    echo "ERROR: curl is required to install nvm. Please install curl or use an image with curl preinstalled." >&2
    exit 1
  fi

  export NVM_DIR=/workspace/.nvm
  if [ ! -d "$NVM_DIR" ]; then
    mkdir -p "$NVM_DIR"
    curl -fsSL https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
  fi
  # shellcheck disable=SC1090
  . "$NVM_DIR/nvm.sh"
  nvm install --lts > /dev/null
  nvm alias default 'lts/*'
  nvm use default > /dev/null
  node -v && npm -v
}

install_claude_code() {
  banner "[4/7] Install Claude Code CLI"
  if ! command -v npm >/dev/null 2>&1; then
    echo "ERROR: npm not found after nvm install. Aborting." >&2
    exit 1
  fi
  npm install -g @anthropic-ai/claude-code
  echo "Installed Claude Code: $(claude-code --version || true)"
}

clone_or_update_repo() {
  banner "[5/7] Clone or update repository"
  if [ -d "$REPO_DIR/.git" ]; then
    echo "Repo already present at $REPO_DIR; pulling latest..."
    (cd "$REPO_DIR" && git remote -v && git pull --ff-only || true)
  else
    # Prefer SSH if /workspace/.ssh exists and key is configured; fallback to HTTPS.
    local url="$REPO_SSH"
    if [ ! -d /workspace/.ssh ]; then
      url="$REPO_HTTPS"
    fi
    echo "Cloning $url into $REPO_DIR"
    git clone "$url" "$REPO_DIR"
  fi
  git config --global --add safe.directory "$REPO_DIR"
}

prestage_models_hint() {
  banner "[6/7] Optional: Pre-stage models"
  cat << 'EOF'
Tip: To avoid repeated network pulls, pre-stage model snapshots under /workspace/models and point loaders to local paths.
Example:
  huggingface-cli snapshot-download Qwen/Qwen2.5-32B \
    --local-dir /workspace/models/Qwen2.5-32B \
    --local-dir-use-symlinks False
EOF
}

print_next_steps() {
  banner "[7/7] Setup Complete — Next Steps"
  cat << EOF
Source pod env in this and future shells:
  source /workspace/pod_env.sh

Enter the repo and read the specs/runbook:
  cd $REPO_DIR
  cat specs/PROGRAM_SPEC.md
  cat runbooks/POD_OPERATIONS.md
  cat runbooks/AGENT_RUNBOOK_STAGE1.md

Claude Code is installed globally (claude-code). Claude can proceed per runbook to install Python deps and run pilots.
EOF
}

# Main
configure_layout
configure_git_and_ssh
install_nvm_node
install_claude_code
clone_or_update_repo
prestage_models_hint
print_next_steps

