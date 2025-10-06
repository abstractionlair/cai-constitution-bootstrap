#!/usr/bin/env python3
"""
Provenance and metadata helpers for Constitutional AI artifacts.

Provides utilities to capture and persist provenance information in all
generated artifacts (training data, evaluation results, checkpoints).

Key concept: Git commit is the "safety net" - can look up any details. But
capture commonly-queried fields (model, params, seeds) for easy filtering.

Usage:
    from utils.provenance_helper import create_artifact_metadata

    metadata = create_artifact_metadata(
        provenance=loader_provenance,
        script_name=Path(__file__).name,
        artifact_type='training_data',
        seed=42,
        temperature=0.7,
        max_new_tokens=150
    )

    example = {
        'instruction': '...',
        'response': '...',
        'metadata': metadata
    }
"""

import subprocess
import socket
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple


def get_git_sha(short: bool = False) -> str:
    """
    Get current git commit SHA.

    Args:
        short: If True, return short SHA (7 chars). Default False (full 40 chars).

    Returns:
        Git commit SHA string, or "git_not_available" if git not found

    Note:
        Returns "git_not_available" if git command not found or not in a git repository.
        This allows scripts to run in environments without git installed.
    """
    try:
        cmd = ['git', 'rev-parse', '--short' if short else 'HEAD']
        result = subprocess.check_output(
            cmd,
            stderr=subprocess.PIPE,
            text=True
        )
        return result.strip()
    except FileNotFoundError:
        # git command not found
        warnings.warn("git command not found. Unable to capture git provenance.")
        return "git_not_available"
    except subprocess.CalledProcessError as e:
        # Not in a git repository or other git error
        warnings.warn(f"Failed to get git SHA: {e.stderr}")
        return "git_not_available"


def get_git_branch() -> str:
    """
    Get current git branch name.

    Returns:
        Branch name (e.g., 'main', 'feature/foo'), or "git_not_available" if git not found

    Note:
        Returns "git_not_available" if git command not found or not in a git repository.
    """
    try:
        result = subprocess.check_output(
            ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
            stderr=subprocess.PIPE,
            text=True
        )
        return result.strip()
    except FileNotFoundError:
        warnings.warn("git command not found. Unable to capture git branch.")
        return "git_not_available"
    except subprocess.CalledProcessError as e:
        warnings.warn(f"Failed to get git branch: {e.stderr}")
        return "git_not_available"


def check_git_dirty() -> bool:
    """
    Check if there are uncommitted changes in the git repository.

    Returns:
        True if there are uncommitted changes (working tree is dirty)
        False if working tree is clean or git not available

    Note:
        Returns False if git command not found (assumes clean state as safe default).
    """
    try:
        result = subprocess.run(
            ['git', 'status', '--porcelain'],
            capture_output=True,
            check=True,
            text=True
        )
        # If output is non-empty, there are uncommitted changes
        return len(result.stdout.strip()) > 0
    except FileNotFoundError:
        warnings.warn("git command not found. Cannot check for uncommitted changes.")
        return False  # Assume clean if git not available
    except subprocess.CalledProcessError as e:
        warnings.warn(f"Failed to check git status: {e.stderr}")
        return False  # Assume clean if error


def create_artifact_metadata(
    provenance: Dict[str, Any],
    script_name: str,
    artifact_type: str,
    **extra
) -> Dict[str, Any]:
    """
    Create standardized metadata for any artifact.

    Combines:
    - Git commit (safety net - can look up anything)
    - Model provenance from CleanModelLoader
    - Script context
    - Any additional parameters (seeds, decoding params, dataset info)

    Args:
        provenance: Provenance dict from CleanModelLoader.load()
                   Must contain: loader_version, model_name, quantization, template_disabled
        script_name: Name of the script generating this artifact (e.g., 'generate_stage1_sft_data.py')
        artifact_type: Type of artifact:
                      - 'training_data': SFT/DPO training examples
                      - 'evaluation': Evaluation results
                      - 'model': Model checkpoint metadata
                      - 'session': Session manifest
        **extra: Any additional metadata fields:
                - seed: Random seed used
                - temperature: Decoding temperature
                - max_new_tokens: Max generation length
                - do_sample: Whether sampling was used
                - models: Dict of model paths (for eval)
                - dataset: Dict of dataset info (for eval)
                - ... (any other relevant fields)

    Returns:
        Dict with comprehensive metadata including:
        - git_commit: Current git SHA (full 40 chars)
        - timestamp: ISO-8601 timestamp when artifact created
        - loader_version: Git SHA of CleanModelLoader at time of load
        - model_name: HuggingFace model name
        - quantization: Quantization type (e.g., '4bit', '8bit')
        - template_disabled: Whether chat template was disabled
        - script_name: Script that generated this
        - artifact_type: Type of artifact
        - ... plus all **extra fields

    Example:
        >>> provenance = loader.load(...)
        >>> metadata = create_artifact_metadata(
        ...     provenance=provenance,
        ...     script_name='generate_stage1_sft_data.py',
        ...     artifact_type='training_data',
        ...     seed=42,
        ...     temperature=0.7,
        ...     max_new_tokens=150,
        ...     do_sample=True
        ... )
        >>> print(metadata['git_commit'])  # abc123...
        >>> print(metadata['template_disabled'])  # True
    """
    # Validate provenance has required fields
    required_fields = ['loader_version', 'model_name', 'quantization', 'template_disabled']
    missing = [f for f in required_fields if f not in provenance]
    if missing:
        raise ValueError(
            f"Provenance dict missing required fields: {missing}. "
            f"Did you get provenance from CleanModelLoader.load()?"
        )

    metadata = {
        # Safety net: git commit can be used to look up any details
        'git_commit': get_git_sha(short=False),
        'timestamp': datetime.now().isoformat(),

        # Model provenance (from CleanModelLoader)
        'loader_version': provenance['loader_version'],
        'model_name': provenance['model_name'],
        'quantization': provenance['quantization'],
        'template_disabled': provenance['template_disabled'],

        # Context
        'script_name': script_name,
        'artifact_type': artifact_type
    }

    # Add any extra fields (params, dataset info, etc.)
    metadata.update(extra)

    return metadata


def create_session_manifest(
    planned_artifacts: Optional[List[str]] = None
) -> Tuple[Dict[str, Any], str]:
    """
    Create session-level manifest at start of GPU session.

    Records:
    - Session identifier and start time
    - Git commit, branch, and dirty state
    - Environment (Python, PyTorch, CUDA, GPU)
    - Planned artifacts for this session

    Args:
        planned_artifacts: Optional list of artifacts planned for this session
                          Example: ["sft_training_data_*.jsonl (15-20k examples)",
                                   "checkpoints/stage1_sft_*",
                                   "evaluation_*.json (N=1000)"]

    Returns:
        (manifest_dict, session_id) where:
        - manifest_dict: Complete session manifest
        - session_id: Timestamp-based session identifier (YYYYMMDD_HHMMSS)

    Note:
        Caller should add transformers version to manifest['environment']['transformers']
        after import (can't import here due to potential dependency issues).

    Example:
        >>> manifest, session_id = create_session_manifest(
        ...     planned_artifacts=["sft_training_data_*.jsonl"]
        ... )
        >>> import transformers
        >>> manifest['environment']['transformers'] = transformers.__version__
        >>>
        >>> import json
        >>> with open(f'artifacts/session_manifest_{session_id}.json', 'w') as f:
        ...     json.dump(manifest, f, indent=2)
    """
    import torch

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    manifest = {
        'session_id': timestamp,
        'session_start': datetime.now().isoformat(),
        'git_commit': get_git_sha(short=False),
        'git_branch': get_git_branch(),
        'git_dirty': check_git_dirty(),
        'environment': {
            'hostname': socket.gethostname(),
            'python': sys.version.split()[0],
            'torch': torch.__version__,
            'transformers': None,  # Caller should fill this
            'cuda': torch.version.cuda if torch.cuda.is_available() else None,
            'gpu': torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
            'gpu_memory_gb': (
                round(torch.cuda.get_device_properties(0).total_memory / 1e9, 1)
                if torch.cuda.is_available() else None
            )
        },
        'planned_artifacts': planned_artifacts or [],
        'artifacts_generated': []
    }

    return manifest, timestamp


if __name__ == "__main__":
    # Quick test/demo
    print("provenance_helper.py - Provenance tracking for Constitutional AI")
    print()

    # Test git functions
    try:
        sha = get_git_sha()
        sha_short = get_git_sha(short=True)
        branch = get_git_branch()
        dirty = check_git_dirty()

        print("Git Information:")
        print(f"  Full SHA:   {sha}")
        print(f"  Short SHA:  {sha_short}")
        print(f"  Branch:     {branch}")
        print(f"  Dirty:      {dirty}")
        print()
    except RuntimeError as e:
        print(f"Git error: {e}")
        print()

    # Test metadata creation (mock provenance)
    mock_provenance = {
        'loader_version': sha_short if 'sha_short' in locals() else 'abc123',
        'model_name': 'Qwen/Qwen2.5-32B',
        'quantization': '4bit',
        'template_disabled': True
    }

    try:
        metadata = create_artifact_metadata(
            provenance=mock_provenance,
            script_name='test_script.py',
            artifact_type='training_data',
            seed=42,
            temperature=0.7,
            max_new_tokens=150,
            do_sample=True
        )

        print("Sample Artifact Metadata:")
        for key, value in metadata.items():
            print(f"  {key}: {value}")
        print()
    except Exception as e:
        print(f"Metadata creation error: {e}")
        print()

    # Test session manifest
    try:
        manifest, session_id = create_session_manifest(
            planned_artifacts=[
                "sft_training_data_*.jsonl (15-20k examples)",
                "evaluation_*.json (N=1000)"
            ]
        )

        print(f"Session Manifest (ID: {session_id}):")
        print(f"  Session start: {manifest['session_start']}")
        print(f"  Git commit:    {manifest['git_commit'][:8]}...")
        print(f"  Branch:        {manifest['git_branch']}")
        print(f"  Dirty:         {manifest['git_dirty']}")
        print(f"  Hostname:      {manifest['environment']['hostname']}")
        print(f"  Python:        {manifest['environment']['python']}")
        print(f"  PyTorch:       {manifest['environment']['torch']}")
        print(f"  GPU:           {manifest['environment']['gpu']}")
        print()
    except Exception as e:
        print(f"Session manifest error: {e}")
        print()

    print("All tests complete. Use this module in scripts to track provenance.")
