# SSH Solution for RunPod File Transfers

## Problem
Getting "PTY errors" and "Connection closed" when trying to use scp or interactive SSH.

## Root Cause
RunPod has TWO different SSH endpoints:
1. **Stable Proxy**: `tupdqnn4ka2obr-6441138e@ssh.runpod.io` - PTY limitations, good for file transfers
2. **Direct SSH**: `root@195.26.233.96 -p 48550` - Interactive, but port changes on restart

## Solution: Use SSH Pipes Instead of SCP

Instead of:
```bash
scp file.py tupdqnn4ka2obr-6441138e@ssh.runpod.io:/remote/path/
```

Use:
```bash
cat file.py | ssh tupdqnn4ka2obr-6441138e@ssh.runpod.io -i ~/.ssh/id_ed25519 'cat > /remote/path/file.py'
```

## Commands to Copy Files to RunPod

### Copy evaluation script:
```bash
cat /Users/scottmcguire/MaximalCAI/scripts/evaluate_final.py | ssh tupdqnn4ka2obr-6441138e@ssh.runpod.io -i ~/.ssh/id_ed25519 'cat > /workspace/runs/stage1_20250911_131105/code/scripts/evaluate_final.py'
```

### Copy test instructions:
```bash
cat /Users/scottmcguire/MaximalCAI/artifacts/held_out_test_instructions_20250911_162708.jsonl | ssh tupdqnn4ka2obr-6441138e@ssh.runpod.io -i ~/.ssh/id_ed25519 'cat > /workspace/runs/stage1_20250911_131105/code/artifacts/held_out_test_instructions.jsonl'
```

## Run Evaluation on RunPod
```bash
ssh tupdqnn4ka2obr-6441138e@ssh.runpod.io -i ~/.ssh/id_ed25519 'cd /workspace/runs/stage1_20250911_131105/code && python scripts/evaluate_final.py'
```# RunPod SSH Solution - WORKING METHOD

## The Problem
- The stable SSH proxy (`tupdqnn4ka2obr-6441138e@ssh.runpod.io`) gives "PTY errors" 
- The direct SSH (`root@195.26.233.96`) works but the port changes when pod restarts

## THE SOLUTION THAT WORKS

### For File Transfers and Commands
Use the **direct SSH with port** (NOT the stable proxy):

```bash
# Set the port (check RunPod dashboard after restart)
export RUNPOD_PORT=48550

# Copy files using SSH pipes
cat local_file.py | ssh -p $RUNPOD_PORT -i ~/.ssh/id_ed25519 -o StrictHostKeyChecking=no root@195.26.233.96 'cat > /remote/path/file.py'

# Run commands
ssh -p $RUNPOD_PORT -i ~/.ssh/id_ed25519 -o StrictHostKeyChecking=no root@195.26.233.96 'cd /workspace/runs/stage1_20250911_131105/code && python scripts/script.py'
```

### Working Example (Tested 2025-09-11)
```bash
# Copy evaluation script
cat /Users/scottmcguire/MaximalCAI/scripts/evaluate_final.py | ssh -p 48550 -i ~/.ssh/id_ed25519 -o StrictHostKeyChecking=no root@195.26.233.96 'cat > /workspace/runs/stage1_20250911_131105/code/scripts/evaluate_final.py'

# Copy test instructions  
cat /Users/scottmcguire/MaximalCAI/artifacts/held_out_test_instructions_20250911_162708.jsonl | ssh -p 48550 -i ~/.ssh/id_ed25519 -o StrictHostKeyChecking=no root@195.26.233.96 'cat > /workspace/runs/stage1_20250911_131105/code/artifacts/held_out_test_instructions.jsonl'

# Run evaluation
ssh -p 48550 -i ~/.ssh/id_ed25519 -o StrictHostKeyChecking=no root@195.26.233.96 'cd /workspace/runs/stage1_20250911_131105/code && python scripts/evaluate_final.py'
```

## Helper Script
Created `/Users/scottmcguire/MaximalCAI/scripts/copy_to_pod.sh` that automates this.

## Important Notes
1. **DO NOT** use the stable proxy for file transfers - it doesn't work despite documentation
2. **DO** use the direct SSH with port for everything
3. **CHECK** the port in RunPod dashboard after each restart
4. **UPDATE** `export RUNPOD_PORT=<new_port>` when it changes

## Why the Stable Proxy Doesn't Work
- The stable proxy (`tupdqnn4ka2obr-6441138e@ssh.runpod.io`) is supposed to work for file transfers
- In practice, it always returns "Error: Your SSH client doesn't support PTY"
- This happens with all flags: `-T`, `-tt`, pipes, etc.
- The sync_claude.sh script has a bug - it uses undefined `$POD_SSH` variable

## Current Pod Configuration (as of 2025-09-11)
- Direct SSH: `root@195.26.233.96`
- Port: `48550` (changes on restart!)
- SSH Key: `~/.ssh/id_ed25519`
- Working directory: `/workspace/runs/stage1_20250911_131105/code/`