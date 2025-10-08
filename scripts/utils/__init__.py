"""
Canonical utilities for Stage 1 data generation and training.

All scripts must use these utilities. No duplicate implementations allowed (DRY principle).

Core utilities:
- CleanModelLoader: Contamination-free base model loading
- CompletionStylePrompts: Canonical prompt builders
- InstructionCritic: Single-token A/B critique via logprobs
- ProvenanceHelper: Standardized metadata for artifacts
"""

from .clean_model_loader import CleanModelLoader, load_clean_base_model
from .completion_prompts import (
    CompletionStylePrompts,
    create_response_prompt,
    create_instruction_prompt,
    create_critic_prompt
)
from .instruction_critic import InstructionCritic, create_critic
from .provenance_helper import (
    create_artifact_metadata,
    create_session_manifest,
    update_session_manifest,
    create_qc_summary,
    get_git_info,
    get_environment_info
)

__all__ = [
    # Model loading
    'CleanModelLoader',
    'load_clean_base_model',

    # Prompts
    'CompletionStylePrompts',
    'create_response_prompt',
    'create_instruction_prompt',
    'create_critic_prompt',

    # Critics
    'InstructionCritic',
    'create_critic',

    # Provenance
    'create_artifact_metadata',
    'create_session_manifest',
    'update_session_manifest',
    'create_qc_summary',
    'get_git_info',
    'get_environment_info',
]
