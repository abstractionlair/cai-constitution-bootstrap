#!/bin/bash
# Copy files to RunPod using the working method

# Try using the direct SSH with port (if pod is running)
DIRECT_SSH="root@195.26.233.96"
POD_PORT="${RUNPOD_PORT:-48550}"
SSH_KEY="$HOME/.ssh/id_ed25519"

echo "Attempting to copy files to RunPod..."

# Method 1: Try direct SSH with port
echo "Trying direct SSH on port $POD_PORT..."
cat /Users/scottmcguire/MaximalCAI/scripts/evaluate_final.py | ssh -p $POD_PORT -i $SSH_KEY -o StrictHostKeyChecking=no $DIRECT_SSH 'cat > /workspace/runs/stage1_20250911_131105/code/scripts/evaluate_final.py' 2>/dev/null

if [ $? -eq 0 ]; then
    echo "✅ Successfully copied evaluate_final.py"
    
    # Copy test instructions too
    cat /Users/scottmcguire/MaximalCAI/artifacts/held_out_test_instructions_20250911_162708.jsonl | ssh -p $POD_PORT -i $SSH_KEY -o StrictHostKeyChecking=no $DIRECT_SSH 'cat > /workspace/runs/stage1_20250911_131105/code/artifacts/held_out_test_instructions.jsonl'
    
    if [ $? -eq 0 ]; then
        echo "✅ Successfully copied test instructions"
        echo ""
        echo "Now you can run evaluation with:"
        echo "ssh -p $POD_PORT -i $SSH_KEY $DIRECT_SSH 'cd /workspace/runs/stage1_20250911_131105/code && python scripts/evaluate_final.py'"
    else
        echo "❌ Failed to copy test instructions"
    fi
else
    echo "❌ Direct SSH failed. The port may have changed."
    echo "Please check RunPod dashboard for the current SSH port and run:"
    echo "export RUNPOD_PORT=<new_port>"
    echo "Then try this script again."
fi