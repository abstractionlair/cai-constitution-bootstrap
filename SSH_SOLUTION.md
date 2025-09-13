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
```