#!/usr/bin/env python3
"""
Create session manifest at start of GPU session.

Records environment, planned work, and provides tracking structure.
Should be run at the start of each production session on the GPU pod.

Usage:
    python3 scripts/create_session_manifest.py

Output:
    artifacts/session_manifest_YYYYMMDD_HHMMSS.json

The manifest captures:
- Session ID and start time
- Git commit, branch, and dirty state
- Environment details (Python, PyTorch, CUDA, GPU)
- Planned artifacts for this session
- List of artifacts generated (updated by scripts)

Example manifest:
{
  "session_id": "20251004_153045",
  "session_start": "2025-10-04T15:30:45",
  "git_commit": "abc123...",
  "git_branch": "main",
  "git_dirty": false,
  "environment": {
    "hostname": "runpod-...",
    "python": "3.10.12",
    "torch": "2.1.0",
    "transformers": "4.35.0",
    "cuda": "12.1",
    "gpu": "NVIDIA H100-SXM 80GB",
    "gpu_memory_gb": 80.0
  },
  "planned_artifacts": [...],
  "artifacts_generated": []
}
"""

import json
import sys
from pathlib import Path

# Add scripts/utils to path
sys.path.insert(0, str(Path(__file__).parent / 'utils'))

from provenance_helper import create_session_manifest


def main():
    """Create and save session manifest."""
    # Define planned artifacts for Stage 1
    planned = [
        "sft_training_data_*.jsonl (15-20k examples)",
        "preference_pairs_*.jsonl (20-30k pairs)",
        "checkpoints/stage1_sft_* (LoRA adapters)",
        "checkpoints/stage1_dpo_* (LoRA adapters)",
        "evaluation_*.json (N=1000, paired design)",
        "ablation_*.json (2 DPO variants)",
    ]

    # Create manifest
    try:
        manifest, session_id = create_session_manifest(planned_artifacts=planned)
    except Exception as e:
        print(f"❌ Failed to create session manifest: {e}")
        return 1

    # Add transformers version
    try:
        import transformers
        manifest['environment']['transformers'] = transformers.__version__
    except ImportError:
        print("⚠️  Warning: transformers not installed, version not recorded")
        manifest['environment']['transformers'] = None

    # Save manifest
    output_dir = Path('artifacts')
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / f'session_manifest_{session_id}.json'

    try:
        with open(output_path, 'w') as f:
            json.dump(manifest, f, indent=2)
    except Exception as e:
        print(f"❌ Failed to save manifest: {e}")
        return 1

    # Print summary
    print("=" * 60)
    print("  Session Manifest Created")
    print("=" * 60)
    print()
    print(f"📋 Session ID:    {session_id}")
    print(f"📁 Manifest file: {output_path}")
    print()
    print(f"🔒 Git commit:    {manifest['git_commit'][:8]}...")
    print(f"🌿 Branch:        {manifest['git_branch']}")
    print()

    # Check git state
    if manifest['git_dirty']:
        print("⚠️  WARNING: Uncommitted changes detected!")
        print("   Git working tree is dirty. Consider committing before production runs.")
        print("   Production artifacts should be generated from clean commits.")
        print()

    # Print environment
    env = manifest['environment']
    print("Environment:")
    print(f"  Hostname:       {env['hostname']}")
    print(f"  Python:         {env['python']}")
    print(f"  PyTorch:        {env['torch']}")
    print(f"  Transformers:   {env['transformers']}")
    print(f"  CUDA:           {env['cuda']}")
    print(f"  GPU:            {env['gpu']}")
    print(f"  GPU Memory:     {env['gpu_memory_gb']} GB")
    print()

    # Print planned artifacts
    print(f"Planned Artifacts ({len(planned)}):")
    for artifact in planned:
        print(f"  - {artifact}")
    print()

    print("✅ Session manifest ready!")
    print()
    print("Next steps:")
    print("  1. Run smoke test (if not already done)")
    print("  2. Begin production data generation")
    print("  3. Scripts will auto-update artifacts_generated list")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
