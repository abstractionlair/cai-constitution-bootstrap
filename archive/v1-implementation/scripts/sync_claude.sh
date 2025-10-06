#!/bin/bash
# Claude Code Session Sync for Local ↔ RunPod
# Enables running Claude directly on pod with session continuity

set -e

# Configuration
POD_SSH_PROXY="tupdqnn4ka2obr-6441138e@ssh.runpod.io"  # Stable proxy for file transfers
POD_SSH_DIRECT="root@195.26.233.96"  # Direct for commands (port may change)
POD_PORT="${RUNPOD_PORT:-48550}"     # Update this when pod restarts
SSH_KEY="$HOME/.ssh/id_ed25519"
SSH_OPTS="-o StrictHostKeyChecking=no"

# Paths
LOCAL_CLAUDE="$HOME/.claude"
POD_CLAUDE_HOME="/root/.claude"
POD_PERSISTENT="/workspace/claude-sessions"

# Project mappings
LOCAL_PROJECT="-Users-scottmcguire-MaximalCAI"
POD_PROJECT_BASE="-workspace-runs-stage1_"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
echo_success() { echo -e "${GREEN}✅ $1${NC}"; }
echo_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
echo_error() { echo -e "${RED}❌ $1${NC}"; }

# Function to find latest pod project directory
find_pod_project() {
    ssh -p $POD_PORT -i $SSH_KEY $SSH_OPTS $POD_SSH \
        "ls -1 /workspace/runs/ | grep stage1_ | sort -r | head -1" 2>/dev/null || echo ""
}

# Function to get pod project encoded name
get_pod_project_name() {
    local run_dir="$1"
    if [ -n "$run_dir" ]; then
        echo "${POD_PROJECT_BASE}${run_dir}-code"
    fi
}

# Check SSH connectivity
check_ssh() {
    echo_info "Testing SSH connection to pod (stable proxy)..."
    if ssh -i $SSH_KEY $SSH_OPTS -o ConnectTimeout=5 $POD_SSH 'echo "Connected"' >/dev/null 2>&1; then
        echo_success "SSH connection OK"
        return 0
    else
        echo_error "SSH connection failed"
        echo "Please check:"
        echo "  - Pod is running"  
        echo "  - SSH key exists at $SSH_KEY"
        return 1
    fi
}

# Setup persistent storage on pod
setup_pod_storage() {
    echo_info "Setting up persistent Claude storage on pod..."
    
    ssh -p $POD_PORT -i $SSH_KEY $SSH_OPTS $POD_SSH << 'SETUP_EOF'
# Create persistent directory
mkdir -p /workspace/claude-sessions/projects
mkdir -p /workspace/claude-sessions/todos
mkdir -p /workspace/claude-sessions/settings

# Create ~/.claude directory if it doesn't exist
mkdir -p /root/.claude

# Create symlinks to persistent storage
if [ ! -L "/root/.claude/projects" ]; then
    rm -rf /root/.claude/projects 2>/dev/null
    ln -s /workspace/claude-sessions/projects /root/.claude/projects
fi

if [ ! -L "/root/.claude/todos" ]; then
    rm -rf /root/.claude/todos 2>/dev/null  
    ln -s /workspace/claude-sessions/todos /root/.claude/todos
fi

echo "Persistent storage setup complete"
ls -la /root/.claude/
SETUP_EOF
    
    echo_success "Pod storage setup complete"
}

# Install Claude Code on pod
install_claude_on_pod() {
    echo_info "Installing Claude Code on pod..."
    
    ssh -p $POD_PORT -i $SSH_KEY $SSH_OPTS $POD_SSH << 'INSTALL_EOF'
# Check if claude is already installed
if command -v claude >/dev/null 2>&1; then
    echo "Claude Code already installed: $(claude --version 2>/dev/null || echo 'version unknown')"
    exit 0
fi

echo "Installing Claude Code..."
curl -fsSL https://console.anthropic.com/install.sh | sh

# Add to PATH for this session
export PATH="$HOME/.local/bin:$PATH"

# Add to bashrc for future sessions
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc

# Test installation
if command -v claude >/dev/null 2>&1; then
    echo "✅ Claude Code installed successfully: $(claude --version)"
else
    echo "❌ Claude Code installation failed"
    exit 1
fi
INSTALL_EOF
    
    echo_success "Claude Code installation complete"
}

# Sync local sessions to pod
sync_to_pod() {
    echo_info "Syncing sessions from local to pod..."
    
    if [ ! -d "$LOCAL_CLAUDE/projects" ]; then
        echo_error "Local Claude sessions not found at $LOCAL_CLAUDE/projects"
        return 1
    fi
    
    # Find current pod project
    local run_dir=$(find_pod_project)
    local pod_project=$(get_pod_project_name "$run_dir")
    
    if [ -z "$run_dir" ]; then
        echo_warning "No pod project found, syncing general sessions"
    else
        echo_info "Found pod project: $run_dir → $pod_project"
    fi
    
    # Copy local MaximalCAI sessions to pod
    echo_info "Transferring session files..."
    
    # Create project directory on pod
    ssh -i $SSH_KEY $SSH_OPTS $POD_SSH \
        "mkdir -p $POD_PERSISTENT/projects/$LOCAL_PROJECT"
    
    # Transfer session files using SSH (no rsync/scp needed)
    for session_file in "$LOCAL_CLAUDE/projects/$LOCAL_PROJECT"/*.jsonl; do
        if [ -f "$session_file" ]; then
            local filename=$(basename "$session_file")
            echo_info "Transferring $filename..."
            cat "$session_file" | ssh -i $SSH_KEY $SSH_OPTS $POD_SSH \
                "cat > $POD_PERSISTENT/projects/$LOCAL_PROJECT/$filename"
        fi
    done
    
    # If we have a pod project, create a symlink for easy access
    if [ -n "$pod_project" ]; then
        ssh -i $SSH_KEY $SSH_OPTS $POD_SSH \
            "ln -sf $POD_PERSISTENT/projects/$LOCAL_PROJECT $POD_PERSISTENT/projects/$pod_project"
        echo_info "Created symlink: $pod_project → $LOCAL_PROJECT"
    fi
    
    # Sync settings if they exist
    if [ -f "$LOCAL_CLAUDE/settings.json" ]; then
        cat "$LOCAL_CLAUDE/settings.json" | ssh -i $SSH_KEY $SSH_OPTS $POD_SSH \
            "cat > $POD_PERSISTENT/settings/settings.json"
        echo_info "Settings synced"
    fi
    
    echo_success "Sessions synced to pod"
}

# Sync pod sessions back to local
sync_from_pod() {
    echo_info "Syncing sessions from pod to local..."
    
    # Create local directories
    mkdir -p "$LOCAL_CLAUDE/projects/$LOCAL_PROJECT"
    
    # Get list of session files from pod
    local session_files=$(ssh -i $SSH_KEY $SSH_OPTS $POD_SSH \
        "ls $POD_PERSISTENT/projects/$LOCAL_PROJECT/*.jsonl 2>/dev/null || true")
    
    # Transfer each session file back
    for session_path in $session_files; do
        if [ -n "$session_path" ]; then
            local filename=$(basename "$session_path")
            echo_info "Retrieving $filename..."
            ssh -i $SSH_KEY $SSH_OPTS $POD_SSH "cat $session_path" > \
                "$LOCAL_CLAUDE/projects/$LOCAL_PROJECT/$filename"
        fi
    done
    
    echo_success "Sessions synced from pod"
}

# Launch Claude on pod with context
launch_claude_on_pod() {
    local run_dir=$(find_pod_project)
    
    if [ -z "$run_dir" ]; then
        echo_error "No pod project found"
        return 1
    fi
    
    echo_info "Launching Claude Code on pod in project: $run_dir"
    echo_info "Claude will have access to session history"
    echo_info "Exit with 'exit' or Ctrl+D when done"
    
    # First sync sessions to pod
    sync_to_pod
    
    # Launch interactive Claude session
    ssh -t -i $SSH_KEY $SSH_OPTS $POD_SSH \
        "cd /workspace/runs/$run_dir/code && export PATH=\"\$HOME/.local/bin:\$PATH\" && claude --continue"
}

# Show status
show_status() {
    echo_info "Claude Sync Status"
    echo "===================="
    
    echo "Local Claude:"
    if [ -d "$LOCAL_CLAUDE/projects/$LOCAL_PROJECT" ]; then
        local session_count=$(ls -1 "$LOCAL_CLAUDE/projects/$LOCAL_PROJECT"/*.jsonl 2>/dev/null | wc -l)
        local latest_session=$(ls -t "$LOCAL_CLAUDE/projects/$LOCAL_PROJECT"/*.jsonl 2>/dev/null | head -1)
        echo "  Sessions: $session_count"
        if [ -n "$latest_session" ]; then
            local size=$(du -h "$latest_session" | cut -f1)
            echo "  Latest: $(basename "$latest_session") ($size)"
        fi
    else
        echo "  No sessions found"
    fi
    
    echo ""
    echo "Pod Status:"
    if check_ssh >/dev/null 2>&1; then
        local run_dir=$(find_pod_project)
        if [ -n "$run_dir" ]; then
            echo "  Project: $run_dir"
            
            # Check if Claude is installed
            local claude_status=$(ssh -i $SSH_KEY $SSH_OPTS $POD_SSH \
                'export PATH="$HOME/.local/bin:$PATH"; command -v claude >/dev/null && echo "installed" || echo "not installed"' 2>/dev/null)
            echo "  Claude Code: $claude_status"
            
            # Check session sync status
            local pod_sessions=$(ssh -i $SSH_KEY $SSH_OPTS $POD_SSH \
                "ls -1 $POD_PERSISTENT/projects/$LOCAL_PROJECT/*.jsonl 2>/dev/null | wc -l" 2>/dev/null || echo "0")
            echo "  Synced sessions: $pod_sessions"
        else
            echo "  No project found"
        fi
    else
        echo "  Not accessible"
    fi
}

# Main menu
case "$1" in
    status)
        show_status
        ;;
    check)
        check_ssh
        ;;
    setup)
        check_ssh && setup_pod_storage && install_claude_on_pod
        ;;
    push)
        check_ssh && sync_to_pod
        ;;
    pull)
        check_ssh && sync_from_pod
        ;;
    launch)
        launch_claude_on_pod
        ;;
    *)
        echo "Claude Code Session Sync"
        echo "========================"
        echo ""
        echo "Usage: $0 {command}"
        echo ""
        echo "Commands:"
        echo "  status  - Show local and pod status"
        echo "  check   - Test SSH connection"
        echo "  setup   - Setup pod storage and install Claude"
        echo "  push    - Sync local sessions to pod"
        echo "  pull    - Sync pod sessions to local"
        echo "  launch  - Launch Claude Code on pod"
        echo ""
        echo "Workflow:"
        echo "  1. ./sync_claude.sh setup    # One-time setup"
        echo "  2. ./sync_claude.sh launch   # Work on pod"
        echo "  3. ./sync_claude.sh pull     # Sync back when done"
        echo ""
        exit 1
        ;;
esac