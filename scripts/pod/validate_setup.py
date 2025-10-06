#!/usr/bin/env python3
"""
Validate pod environment setup for CAI Bootstrap project.

Checks:
- Environment variables (HOME, HF_*, TORCH_HOME, etc.)
- Python packages (torch, transformers, unsloth, etc.)
- GPU availability
- Directory structure
- Git configuration
- Node.js and codex CLI

Usage:
    source /workspace/pod_env.sh
    source /workspace/venv/bin/activate
    python scripts/pod/validate_setup.py
"""

import os
import sys
import subprocess
from pathlib import Path


def check_env_vars():
    """Check required environment variables."""
    print("=" * 60)
    print("Checking Environment Variables")
    print("=" * 60)

    required_vars = {
        "HOME": "/workspace/home",
        "HF_HOME": "/workspace/.cache/huggingface",
        "TRANSFORMERS_CACHE": "/workspace/.cache/huggingface/transformers",
        "HF_DATASETS_CACHE": "/workspace/.cache/huggingface/datasets",
        "TORCH_HOME": "/workspace/.cache/torch",
        "XDG_CONFIG_HOME": "/workspace/.config",
    }

    all_ok = True
    for var, expected_prefix in required_vars.items():
        actual = os.environ.get(var)
        if actual and actual.startswith(expected_prefix):
            print(f"✓ {var}={actual}")
        else:
            print(f"✗ {var}={actual} (expected: {expected_prefix})")
            all_ok = False

    return all_ok


def check_directories():
    """Check required directory structure."""
    print("\n" + "=" * 60)
    print("Checking Directory Structure")
    print("=" * 60)

    required_dirs = [
        "/workspace/home",
        "/workspace/.config",
        "/workspace/.cache/huggingface/datasets",
        "/workspace/.cache/huggingface/transformers",
        "/workspace/.cache/torch",
        "/workspace/models",
        "/workspace/artifacts",
        "/workspace/data",
        "/workspace/logs",
        "/workspace/results",
        "/workspace/checkpoints",
        "/workspace/venv",
        "/workspace/cai-constitution-bootstrap",
    ]

    all_ok = True
    for dir_path in required_dirs:
        if Path(dir_path).exists():
            print(f"✓ {dir_path}")
        else:
            print(f"✗ {dir_path} (missing)")
            all_ok = False

    return all_ok


def check_python_packages():
    """Check required Python packages."""
    print("\n" + "=" * 60)
    print("Checking Python Packages")
    print("=" * 60)

    required_packages = [
        "torch",
        "transformers",
        "accelerate",
        "bitsandbytes",
        "peft",
        "datasets",
        "numpy",
        "scipy",
        "tqdm",
    ]

    all_ok = True
    for package in required_packages:
        try:
            __import__(package)
            if package == "torch":
                import torch
                print(f"✓ {package} (version: {torch.__version__})")
            elif package == "transformers":
                import transformers
                print(f"✓ {package} (version: {transformers.__version__})")
            else:
                print(f"✓ {package}")
        except ImportError:
            print(f"✗ {package} (not installed)")
            all_ok = False

    return all_ok


def check_gpu():
    """Check GPU availability."""
    print("\n" + "=" * 60)
    print("Checking GPU")
    print("=" * 60)

    try:
        import torch
        if torch.cuda.is_available():
            gpu_count = torch.cuda.device_count()
            gpu_name = torch.cuda.get_device_name(0)
            gpu_memory = torch.cuda.get_device_properties(0).total_memory / 1e9
            print(f"✓ GPU available: {gpu_name}")
            print(f"  - Device count: {gpu_count}")
            print(f"  - Memory: {gpu_memory:.1f} GB")
            print(f"  - CUDA version: {torch.version.cuda}")
            return True
        else:
            print("✗ No GPU available")
            return False
    except Exception as e:
        print(f"✗ Error checking GPU: {e}")
        return False


def check_git():
    """Check git configuration."""
    print("\n" + "=" * 60)
    print("Checking Git Configuration")
    print("=" * 60)

    try:
        # Check git user
        name = subprocess.check_output(
            ["git", "config", "--global", "user.name"],
            text=True,
            stderr=subprocess.DEVNULL
        ).strip()
        email = subprocess.check_output(
            ["git", "config", "--global", "user.email"],
            text=True,
            stderr=subprocess.DEVNULL
        ).strip()
        print(f"✓ Git user: {name} <{email}>")

        # Check if in repo
        repo_root = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"],
            text=True,
            stderr=subprocess.DEVNULL
        ).strip()
        print(f"✓ Git repo: {repo_root}")

        return True
    except subprocess.CalledProcessError:
        print("✗ Git not configured properly")
        return False


def check_nodejs():
    """Check Node.js and codex installation."""
    print("\n" + "=" * 60)
    print("Checking Node.js and Codex")
    print("=" * 60)

    all_ok = True

    try:
        node_version = subprocess.check_output(
            ["node", "--version"],
            text=True,
            stderr=subprocess.DEVNULL
        ).strip()
        print(f"✓ Node.js: {node_version}")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("✗ Node.js not found")
        all_ok = False

    try:
        npm_version = subprocess.check_output(
            ["npm", "--version"],
            text=True,
            stderr=subprocess.DEVNULL
        ).strip()
        print(f"✓ npm: {npm_version}")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("✗ npm not found")
        all_ok = False

    try:
        codex_version = subprocess.check_output(
            ["codex", "--version"],
            text=True,
            stderr=subprocess.DEVNULL
        ).strip()
        print(f"✓ codex: {codex_version}")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("✗ codex not found")
        all_ok = False

    return all_ok


def main():
    """Run all validation checks."""
    print("\n")
    print("=" * 60)
    print("Pod Environment Validation")
    print("=" * 60)
    print()

    checks = [
        ("Environment Variables", check_env_vars),
        ("Directory Structure", check_directories),
        ("Python Packages", check_python_packages),
        ("GPU", check_gpu),
        ("Git", check_git),
        ("Node.js/Codex", check_nodejs),
    ]

    results = {}
    for name, check_func in checks:
        try:
            results[name] = check_func()
        except Exception as e:
            print(f"\n✗ {name} check failed with error: {e}")
            results[name] = False

    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)

    all_passed = True
    for name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {name}")
        if not passed:
            all_passed = False

    print()
    if all_passed:
        print("✓ All checks passed! Environment is ready.")
        return 0
    else:
        print("✗ Some checks failed. Please fix the issues above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
