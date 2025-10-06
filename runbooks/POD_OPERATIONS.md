# Pod Operations Guide (Persistent /workspace)

Durable Root & Env
- Treat /workspace as the only durable root on pods.
- Export on every session:
  - HOME=/workspace/home
  - XDG_CONFIG_HOME=/workspace/.config
  - HF_HOME=/workspace/.cache/huggingface
  - TRANSFORMERS_CACHE=/workspace/.cache/huggingface/transformers
  - HF_DATASETS_CACHE=/workspace/.cache/huggingface/datasets
  - TORCH_HOME=/workspace/.cache/torch

Git Auth
- Preferred: HTTPS + PAT stored at /workspace/.git-credentials
  - git config --global credential.helper 'store --file=/workspace/.git-credentials'
- If SSH required: decrypt keys to /dev/shm/.ssh (chmod 700 dir, 600 keys) and start ssh-agent for the session. Do not store private keys on /workspace permanently.

Model Caches
- Prefer local snapshots (e.g., /workspace/models/Qwen2.5-32B) using HF snapshot-download with --local-dir-use-symlinks False.
- Point loaders to local model paths first to avoid repeated network pulls.

GPU Preflight
- Verify at least one visible GPU; fail fast if none detected and request human to attach GPU resources.

Write Quotas & Large Files
- Keep transient caches small; persist only essential artifacts (datasets, checkpoints, manifests).
- If network FS quotas are encountered, back heavy artifacts to object storage or use local ephemeral disk for temp caches.

Containers
- Maintain pinned images for CUDA and ROCm stacks with known-good torch/transformers/bitsandbytes (CUDA) and validated ROCm equivalents.

