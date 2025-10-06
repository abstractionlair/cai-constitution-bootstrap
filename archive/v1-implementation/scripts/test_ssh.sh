#!/bin/bash
# RunPod SSH Connection Tester - Updated for RunPod SSH Proxy

echo "🔑 Testing RunPod SSH Connection..."

# Load credentials
source .env.runpod

# Check for new format first
if [ -n "$RUNPOD_SSH_USER" ] && [ -n "$RUNPOD_SSH_HOST" ]; then
    echo "📡 Connecting via RunPod SSH proxy..."
    echo "   User: $RUNPOD_SSH_USER"
    echo "   Host: $RUNPOD_SSH_HOST"
    
    # Test connection with RunPod's SSH proxy
    if ssh -T -o ConnectTimeout=10 -o StrictHostKeyChecking=no \
       ${RUNPOD_SSH_USER}@${RUNPOD_SSH_HOST} -i ~/.ssh/id_ed25519 \
       'echo "✅ SSH connection successful!" && hostname && date' 2>/dev/null; then
        
        echo "✅ SSH key authentication working!"
        echo ""
        echo "📊 Getting GPU info..."
        ssh -T ${RUNPOD_SSH_USER}@${RUNPOD_SSH_HOST} -i ~/.ssh/id_ed25519 \
            'nvidia-smi --query-gpu=name,memory.total --format=csv,noheader' 2>/dev/null
        
        echo ""
        echo "💾 Checking disk space..."
        ssh -T ${RUNPOD_SSH_USER}@${RUNPOD_SSH_HOST} -i ~/.ssh/id_ed25519 \
            'df -h /workspace' 2>/dev/null
        
    else
        echo "❌ SSH connection failed!"
        echo ""
        echo "Debug with: ssh -vvv ${RUNPOD_SSH_USER}@${RUNPOD_SSH_HOST} -i ~/.ssh/id_ed25519"
        exit 1
    fi
    
# Fall back to old format if available
elif [ -n "$RUNPOD_HOST" ] && [ -n "$RUNPOD_PORT" ]; then
    echo "📡 Connecting directly to $RUNPOD_HOST:$RUNPOD_PORT..."
    
    if ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no \
       root@${RUNPOD_HOST} -p ${RUNPOD_PORT} \
       'echo "✅ SSH connection successful!" && hostname && date' 2>/dev/null; then
        
        echo "✅ SSH key authentication working!"
        
    else
        echo "❌ SSH connection failed!"
        exit 1
    fi
else
    echo "❌ Please set RUNPOD_SSH_USER and RUNPOD_SSH_HOST in .env.runpod"
    exit 1
fi

echo ""
echo "🎉 Ready to start the CAI experiment!"
