#!/usr/bin/env python3
"""
Log all environment versions for reproducibility.
Run this at the start of each RunPod session to capture full environment state.
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

def get_git_sha():
    """Get current git SHA"""
    try:
        sha = subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'],
            stderr=subprocess.DEVNULL
        ).decode('ascii').strip()
        return sha
    except:
        return "unknown"

def get_git_branch():
    """Get current git branch"""
    try:
        branch = subprocess.check_output(
            ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
            stderr=subprocess.DEVNULL
        ).decode('ascii').strip()
        return branch
    except:
        return "unknown"

def get_cuda_version():
    """Get CUDA version from nvcc"""
    try:
        output = subprocess.check_output(['nvcc', '--version']).decode()
        for line in output.split('\n'):
            if 'release' in line.lower():
                version = line.split('release')[1].split(',')[0].strip()
                return version
    except:
        return "unknown"

def get_gpu_name():
    """Get GPU name from nvidia-smi"""
    try:
        output = subprocess.check_output(
            ['nvidia-smi', '--query-gpu=name', '--format=csv,noheader'],
            stderr=subprocess.DEVNULL
        ).decode()
        return output.strip().split('\n')[0]
    except:
        return "unknown"

def get_gpu_memory():
    """Get GPU memory from nvidia-smi"""
    try:
        output = subprocess.check_output(
            ['nvidia-smi', '--query-gpu=memory.total', '--format=csv,noheader,nounits'],
            stderr=subprocess.DEVNULL
        ).decode()
        memory_mb = int(output.strip().split('\n')[0])
        memory_gb = memory_mb / 1024
        return f"{memory_gb:.1f} GB"
    except:
        return "unknown"

def main():
    """Log all versions and environment info"""
    print("📋 Logging session environment versions...")
    print("")

    # Import after checking Python version
    try:
        import torch
    except ImportError:
        print("⚠️  PyTorch not installed")
        torch = None

    try:
        import transformers
    except ImportError:
        print("⚠️  Transformers not installed")
        transformers = None

    try:
        import bitsandbytes
    except ImportError:
        print("⚠️  BitsAndBytes not installed")
        bitsandbytes = None

    # Build versions dict
    versions = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "git_sha": get_git_sha(),
        "git_branch": get_git_branch(),
        "python_version": sys.version.split()[0],
        "pytorch": torch.__version__ if torch else "not installed",
        "transformers": transformers.__version__ if transformers else "not installed",
        "bitsandbytes": bitsandbytes.__version__ if bitsandbytes else "not installed",
        "cuda_version": get_cuda_version(),
        "gpu_name": get_gpu_name(),
        "gpu_memory": get_gpu_memory(),
    }

    # Get pip freeze
    try:
        pip_freeze = subprocess.check_output(['pip', 'freeze']).decode().split('\n')
        versions["pip_freeze"] = [line for line in pip_freeze if line.strip()]
    except:
        versions["pip_freeze"] = []

    # Save to artifacts
    output_dir = Path("artifacts")
    output_dir.mkdir(exist_ok=True)

    output_file = output_dir / "session_versions.json"

    with open(output_file, 'w') as f:
        json.dump(versions, f, indent=2)

    print(f"✅ Versions logged to {output_file}")
    print("")
    print("Key versions:")
    print(f"  Git SHA:      {versions['git_sha'][:12]}")
    print(f"  Git Branch:   {versions['git_branch']}")
    print(f"  Python:       {versions['python_version']}")
    print(f"  PyTorch:      {versions['pytorch']}")
    print(f"  Transformers: {versions['transformers']}")
    print(f"  BitsAndBytes: {versions['bitsandbytes']}")
    print(f"  CUDA:         {versions['cuda_version']}")
    print(f"  GPU:          {versions['gpu_name']}")
    print(f"  GPU Memory:   {versions['gpu_memory']}")
    print("")
    print("✅ Session environment captured for reproducibility")

if __name__ == "__main__":
    main()
