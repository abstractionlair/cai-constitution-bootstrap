#!/bin/bash
# RunPod connection helper - handles dynamic ports

# Try direct SSH first (you'll need to update the port each session)
DIRECT_HOST="195.26.233.96"
DIRECT_PORT="${RUNPOD_PORT:-48550}"  # Set RUNPOD_PORT env var or update here
SSH_KEY="$HOME/.ssh/id_ed25519"

# Proxy SSH (stable)
PROXY_HOST="tupdqnn4ka2obr-6441138e@ssh.runpod.io"

echo "RunPod Connection Helper"
echo "========================"

# Function to test direct SSH
test_direct() {
    echo "Testing direct SSH on port $DIRECT_PORT..."
    if ssh -o ConnectTimeout=2 -o StrictHostKeyChecking=no \
        root@$DIRECT_HOST -p $DIRECT_PORT -i $SSH_KEY \
        'echo "Direct SSH OK"' 2>/dev/null; then
        echo "✓ Direct SSH works on port $DIRECT_PORT"
        return 0
    else
        echo "✗ Direct SSH failed on port $DIRECT_PORT"
        return 1
    fi
}

# Function to update port
update_port() {
    echo ""
    echo "Please enter the current SSH port from RunPod UI:"
    echo "(Look for: ssh root@$DIRECT_HOST -p XXXXX)"
    read -p "Port: " new_port
    DIRECT_PORT=$new_port
    export RUNPOD_PORT=$new_port
    echo "Updated port to: $DIRECT_PORT"
}

# Main logic
if [ "$1" == "update" ]; then
    update_port
    test_direct
elif [ "$1" == "scp" ]; then
    # Use for file transfers
    if test_direct; then
        echo "Using direct SCP..."
        shift  # Remove 'scp' argument
        scp -P $DIRECT_PORT -i $SSH_KEY "$@"
    else
        echo "Direct SCP failed. Please update port with: $0 update"
        exit 1
    fi
elif [ "$1" == "ssh" ]; then
    # Interactive SSH
    if test_direct; then
        echo "Connecting via direct SSH..."
        ssh root@$DIRECT_HOST -p $DIRECT_PORT -i $SSH_KEY
    else
        echo "Direct SSH failed. Falling back to proxy..."
        ssh $PROXY_HOST -i $SSH_KEY
    fi
else
    # Default: test connection
    if ! test_direct; then
        echo ""
        echo "Options:"
        echo "  $0 update  - Update the SSH port"
        echo "  $0 ssh     - Connect via SSH"  
        echo "  $0 scp [args] - Transfer files via SCP"
        echo ""
        echo "Proxy SSH (always works): ssh $PROXY_HOST -i $SSH_KEY"
    fi
fi