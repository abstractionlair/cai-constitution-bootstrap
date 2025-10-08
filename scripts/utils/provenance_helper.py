#!/usr/bin/env python3
"""
Provenance Helper - Create standardized metadata for all artifacts.

Ensures every dataset, checkpoint, and result has complete provenance:
- Git commit SHA, branch, dirty status
- Environment info (Python, torch, transformers, CUDA/ROCm, GPU)
- Timestamps
- Script name and artifact type
- Generation parameters

Usage:
    from utils.provenance_helper import create_artifact_metadata, create_session_manifest

    # Add to every generated example
    metadata = create_artifact_metadata(
        artifact_type="sft_example",
        script_name="generate_pilot_data.py",
        model_name="Qwen/Qwen2.5-32B",
        loader_provenance=loader_prov,
        generation_params={
            "temperature": 0.5,
            "max_new_tokens": 80,
            "seed": 42
        }
    )

    # Create session manifest
    manifest = create_session_manifest(
        session_id="data_gen_pilot_20251007",
        planned_artifacts=["pilot_data.jsonl", "qc_summary.json"]
    )
"""

import os
import sys
import subprocess
import socket
import torch
import transformers
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)


def get_git_info(repo_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Get git repository information.

    Args:
        repo_path: Path to repository root (default: script's parent dir)

    Returns:
        Dict with commit, branch, dirty status
    """
    if repo_path is None:
        repo_path = Path(__file__).parent.parent.parent

    try:
        # Get commit SHA
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_path,
            text=True,
            stderr=subprocess.DEVNULL
        ).strip()

        # Get branch
        branch = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=repo_path,
            text=True,
            stderr=subprocess.DEVNULL
        ).strip()

        # Check if dirty
        status = subprocess.check_output(
            ["git", "status", "--porcelain"],
            cwd=repo_path,
            text=True,
            stderr=subprocess.DEVNULL
        ).strip()
        dirty = bool(status)

        return {
            "git_commit": commit,
            "git_branch": branch,
            "git_dirty": dirty
        }
    except Exception as e:
        logger.warning(f"Could not get git info: {e}")
        return {
            "git_commit": "unknown",
            "git_branch": "unknown",
            "git_dirty": False
        }


def get_environment_info() -> Dict[str, Any]:
    """
    Get environment information.

    Returns:
        Dict with Python, torch, transformers, CUDA/ROCm, GPU info
    """
    env_info = {
        "hostname": socket.gethostname(),
        "python_version": sys.version.split()[0],
        "torch_version": torch.__version__,
        "transformers_version": transformers.__version__,
    }

    # CUDA or ROCm
    if torch.cuda.is_available():
        env_info["cuda_available"] = True
        env_info["cuda_version"] = torch.version.cuda
        env_info["gpu_count"] = torch.cuda.device_count()

        # Get GPU info
        if torch.cuda.device_count() > 0:
            env_info["gpu_name"] = torch.cuda.get_device_name(0)
            props = torch.cuda.get_device_properties(0)
            env_info["gpu_memory_gb"] = props.total_memory / (1024**3)
    else:
        env_info["cuda_available"] = False

    # Check for ROCm
    if hasattr(torch.version, 'hip') and torch.version.hip is not None:
        env_info["rocm_version"] = torch.version.hip

    return env_info


def create_artifact_metadata(
    artifact_type: str,
    script_name: str,
    model_name: str,
    loader_provenance: Dict[str, Any],
    generation_params: Optional[Dict[str, Any]] = None,
    additional_metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create standardized metadata for an artifact.

    Args:
        artifact_type: Type of artifact (e.g., "sft_example", "preference_pair")
        script_name: Name of generating script
        model_name: Model name
        loader_provenance: Provenance from CleanModelLoader
        generation_params: Generation parameters (temp, max_tokens, seed, etc.)
        additional_metadata: Any additional metadata

    Returns:
        Complete metadata dict
    """
    metadata = {
        "artifact_type": artifact_type,
        "script_name": script_name,
        "timestamp": datetime.utcnow().isoformat(),
        "model_name": model_name,
        **get_git_info(),
        **loader_provenance
    }

    if generation_params:
        metadata["generation_params"] = generation_params

    if additional_metadata:
        metadata.update(additional_metadata)

    return metadata


def create_session_manifest(
    session_id: str,
    planned_artifacts: List[str],
    gpu_hours_estimate: Optional[float] = None,
    notes: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create session manifest for a generation/training session.

    Args:
        session_id: Unique session identifier
        planned_artifacts: List of artifacts to be generated
        gpu_hours_estimate: Estimated GPU hours
        notes: Optional notes about session

    Returns:
        Session manifest dict
    """
    manifest = {
        "session_id": session_id,
        "session_start": datetime.utcnow().isoformat(),
        **get_git_info(),
        "environment": get_environment_info(),
        "planned_artifacts": planned_artifacts,
        "artifacts_generated": [],  # Will be populated during session
        "gpu_hours_estimate": gpu_hours_estimate
    }

    if notes:
        manifest["notes"] = notes

    return manifest


def update_session_manifest(
    manifest: Dict[str, Any],
    artifact_path: str,
    artifact_type: str,
    success: bool,
    error: Optional[str] = None
) -> Dict[str, Any]:
    """
    Update session manifest with generated artifact.

    Args:
        manifest: Existing session manifest
        artifact_path: Path to generated artifact
        artifact_type: Type of artifact
        success: Whether generation succeeded
        error: Error message if failed

    Returns:
        Updated manifest
    """
    artifact_entry = {
        "path": artifact_path,
        "type": artifact_type,
        "timestamp": datetime.utcnow().isoformat(),
        "success": success
    }

    if error:
        artifact_entry["error"] = error

    manifest["artifacts_generated"].append(artifact_entry)

    return manifest


def create_qc_summary(
    counts: Dict[str, int],
    acceptance: Dict[str, int],
    token_stats: Dict[str, float],
    margins: Dict[str, Any],
    thresholds: Dict[str, Any],
    thresholds_passed: bool,
    failed_reasons: List[str]
) -> Dict[str, Any]:
    """
    Create QC summary for data generation.

    Args:
        counts: Generation counts (generated, kept, delimiter_found, etc.)
        acceptance: Acceptance counts (instructions_good, pairs_good, etc.)
        token_stats: Token statistics (median, mean, p95)
        margins: Margin statistics for critics
        thresholds: Threshold values used
        thresholds_passed: Overall pass/fail
        failed_reasons: List of failed threshold checks

    Returns:
        QC summary dict
    """
    return {
        "timestamp": datetime.utcnow().isoformat(),
        **get_git_info(),
        "counts": counts,
        "acceptance": acceptance,
        "token_stats": token_stats,
        "margins": margins,
        "thresholds": thresholds,
        "thresholds_passed": thresholds_passed,
        "failed_reasons": failed_reasons
    }


if __name__ == "__main__":
    # Test provenance helper
    print("Testing Provenance Helper...")
    print("=" * 60)

    # Test git info
    git_info = get_git_info()
    print("\nGit Info:")
    print(f"  Commit: {git_info['git_commit'][:8]}")
    print(f"  Branch: {git_info['git_branch']}")
    print(f"  Dirty: {git_info['git_dirty']}")

    # Test environment info
    env_info = get_environment_info()
    print("\nEnvironment Info:")
    print(f"  Python: {env_info['python_version']}")
    print(f"  Torch: {env_info['torch_version']}")
    print(f"  CUDA: {env_info.get('cuda_available', False)}")
    if env_info.get('cuda_available'):
        print(f"  GPU: {env_info.get('gpu_name', 'Unknown')}")

    # Test metadata creation
    metadata = create_artifact_metadata(
        artifact_type="test_example",
        script_name="test.py",
        model_name="Qwen/Qwen2.5-32B",
        loader_provenance={
            "loader_version": git_info['git_commit'],
            "quantization": "4bit-nf4",
            "template_disabled": True
        },
        generation_params={
            "temperature": 0.5,
            "max_new_tokens": 80,
            "seed": 42
        }
    )

    print("\nMetadata Sample:")
    print(f"  Artifact Type: {metadata['artifact_type']}")
    print(f"  Timestamp: {metadata['timestamp']}")
    print(f"  Model: {metadata['model_name']}")

    print("\n" + "=" * 60)
    print("✅ Provenance helper working correctly")
