#!/usr/bin/env python3
"""
Data validation utilities for pipeline robustness
Validates data formats between pipeline steps to catch errors early
"""

import json
import logging
from typing import List, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)


def validate_sft_data(data: List[Dict]) -> None:
    """Validate SFT training data format"""
    if not data:
        raise ValueError("SFT data is empty")
    
    required_keys = ['instruction', 'response', 'formatted_text', 'instruction_type']
    
    for i, example in enumerate(data):
        # Check required keys
        for key in required_keys:
            if key not in example:
                raise ValueError(f"Missing key '{key}' in SFT example {i}")
        
        # Check that values are strings
        for key in required_keys:
            if not isinstance(example[key], str):
                raise ValueError(f"Key '{key}' must be string in SFT example {i}")
        
        # Check format structure
        formatted_text = example['formatted_text']
        
        if not formatted_text.startswith('Instruction:'):
            raise ValueError(f"Invalid format in SFT example {i}: missing 'Instruction:' prefix")
            
        if 'Response:' not in formatted_text:
            raise ValueError(f"Invalid format in SFT example {i}: missing 'Response:' section")
            
        if not formatted_text.endswith('END'):
            raise ValueError(f"Invalid format in SFT example {i}: missing 'END' suffix")
        
        # Check instruction type is valid
        valid_types = ['qa', 'completion', 'generation', 'response']
        if example['instruction_type'] not in valid_types:
            raise ValueError(f"Invalid instruction_type '{example['instruction_type']}' in SFT example {i}")
    
    logger.info(f"✅ SFT data validation passed: {len(data)} examples")


def validate_preference_pairs(pairs: List[Dict]) -> None:
    """Validate preference pair format - flexible for both DPO format and original format"""
    if not pairs:
        raise ValueError("Preference pairs data is empty")
    
    # Check first pair to determine format
    first_pair = pairs[0]
    has_prompt = 'prompt' in first_pair
    has_instruction = 'instruction' in first_pair
    
    if has_prompt:
        # DPO format: prompt, chosen, rejected, instruction
        required_keys = ['prompt', 'chosen', 'rejected', 'instruction']
        instruction_key = 'prompt'
        instruction_prefix = 'Instruction:'
    elif has_instruction:
        # Original format: instruction, chosen, rejected  
        required_keys = ['instruction', 'chosen', 'rejected']
        instruction_key = 'instruction'
        instruction_prefix = None  # No prefix requirement for original format
    else:
        raise ValueError("Preference pairs must have either 'prompt' or 'instruction' key")
    
    for i, pair in enumerate(pairs):
        # Check required keys
        for key in required_keys:
            if key not in pair:
                raise ValueError(f"Missing key '{key}' in preference pair {i}")
        
        # Check that values are strings for core keys
        core_keys = ['chosen', 'rejected', instruction_key]
        for key in core_keys:
            if not isinstance(pair[key], str):
                raise ValueError(f"Key '{key}' must be string in preference pair {i}")
        
        # Check that chosen and rejected are different
        if pair['chosen'] == pair['rejected']:
            raise ValueError(f"Identical chosen/rejected in preference pair {i}")
        
        # Check instruction format if required
        if instruction_prefix and not pair[instruction_key].startswith(instruction_prefix):
            raise ValueError(f"Invalid {instruction_key} format in preference pair {i}: missing '{instruction_prefix}' prefix")
        
        # Check that chosen and rejected are not empty
        if len(pair['chosen'].strip()) < 3:
            raise ValueError(f"Chosen response too short in preference pair {i}")
        
        if len(pair['rejected'].strip()) < 3:
            raise ValueError(f"Rejected response too short in preference pair {i}")
    
    format_type = "DPO format" if has_prompt else "original format"
    logger.info(f"✅ Preference pairs validation passed: {len(pairs)} pairs ({format_type})")


def validate_negative_examples(negatives: List[Dict]) -> None:
    """Validate negative examples format"""
    if not negatives:
        raise ValueError("Negative examples data is empty")
    
    required_keys = ['instruction', 'negative_response', 'negative_type']
    valid_negative_types = ['unwarranted_refusal', 'format_violation', 'incorrect_factual', 'off_topic', 'verbose_vague']
    
    for i, example in enumerate(negatives):
        # Check required keys
        for key in required_keys:
            if key not in example:
                raise ValueError(f"Missing key '{key}' in negative example {i}")
        
        # Check negative type is valid
        if example['negative_type'] not in valid_negative_types:
            raise ValueError(f"Invalid negative_type '{example['negative_type']}' in negative example {i}")
        
        # Check that response is not empty
        if len(example['negative_response'].strip()) < 3:
            raise ValueError(f"Negative response too short in example {i}")
    
    logger.info(f"✅ Negative examples validation passed: {len(negatives)} examples")


def validate_test_instructions(instructions: List[Dict]) -> None:
    """Validate test instructions format"""
    if not instructions:
        raise ValueError("Test instructions data is empty")
    
    required_keys = ['instruction', 'expected_type', 'id']
    
    for i, example in enumerate(instructions):
        # Check required keys
        for key in required_keys:
            if key not in example:
                raise ValueError(f"Missing key '{key}' in test instruction {i}")
        
        # Check instruction is not empty
        if len(example['instruction'].strip()) < 5:
            raise ValueError(f"Instruction too short in test example {i}")
        
        # Check ID is unique (basic check)
        if not example['id']:
            raise ValueError(f"Missing ID in test instruction {i}")
    
    # Check for duplicate IDs
    ids = [inst['id'] for inst in instructions]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate IDs found in test instructions")
    
    logger.info(f"✅ Test instructions validation passed: {len(instructions)} instructions")


def validate_model_checkpoint(checkpoint_path: Path) -> None:
    """Validate model checkpoint directory exists and has required files"""
    if not checkpoint_path.exists():
        raise FileNotFoundError(f"Checkpoint directory not found: {checkpoint_path}")
    
    if not checkpoint_path.is_dir():
        raise ValueError(f"Checkpoint path is not a directory: {checkpoint_path}")
    
    # Check for common required files
    required_files = ['adapter_config.json', 'adapter_model.safetensors']
    missing_files = []
    
    for file_name in required_files:
        if not (checkpoint_path / file_name).exists():
            missing_files.append(file_name)
    
    if missing_files:
        raise FileNotFoundError(f"Missing required checkpoint files in {checkpoint_path}: {missing_files}")
    
    logger.info(f"✅ Model checkpoint validation passed: {checkpoint_path}")


def validate_jsonl_file(file_path: Path, validator_func, description: str = "JSONL file") -> Any:
    """Validate a JSONL file by loading and validating its contents"""
    if not file_path.exists():
        raise FileNotFoundError(f"{description} not found: {file_path}")
    
    logger.info(f"🔍 Validating {description}: {file_path}")
    
    try:
        data = []
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if line:  # Skip empty lines
                    try:
                        data.append(json.loads(line))
                    except json.JSONDecodeError as e:
                        raise ValueError(f"Invalid JSON on line {line_num} in {file_path}: {e}")
        
        # Run specific validation
        validator_func(data)
        
        return data
        
    except Exception as e:
        logger.error(f"❌ Validation failed for {description}: {e}")
        raise


def load_and_validate_sft_data(data_dir: Path = None) -> List[Dict]:
    """Load and validate SFT training data"""
    if data_dir is None:
        from pathlib import Path
        import os
        data_dir = Path(os.getenv('CAI_BASE_DIR', '/workspace/runs/stage1_20250911_131105/code')) / 'artifacts'
    
    # Find most recent SFT data file
    pattern = "sft_training_data_*.jsonl"
    files = sorted(data_dir.glob(pattern), reverse=True)
    
    if not files:
        raise FileNotFoundError(f"No SFT training data found matching {pattern} in {data_dir}")
    
    return validate_jsonl_file(files[0], validate_sft_data, "SFT training data")


def load_and_validate_preference_pairs(data_dir: Path = None) -> List[Dict]:
    """Load and validate preference pairs"""
    if data_dir is None:
        from pathlib import Path
        import os
        data_dir = Path(os.getenv('CAI_BASE_DIR', '/workspace/runs/stage1_20250911_131105/code')) / 'artifacts'
    
    # Find most recent preference pairs file
    pattern = "preference_pairs_improved_*.jsonl"
    files = sorted(data_dir.glob(pattern), reverse=True)
    
    if not files:
        raise FileNotFoundError(f"No preference pairs found matching {pattern} in {data_dir}")
    
    return validate_jsonl_file(files[0], validate_preference_pairs, "preference pairs")


def load_and_validate_negatives(data_dir: Path = None) -> List[Dict]:
    """Load and validate negative examples"""
    if data_dir is None:
        from pathlib import Path
        import os
        data_dir = Path(os.getenv('CAI_BASE_DIR', '/workspace/runs/stage1_20250911_131105/code')) / 'artifacts'
    
    # Find most recent negatives file
    pattern = "diverse_negatives_*.jsonl"
    files = sorted(data_dir.glob(pattern), reverse=True)
    
    if not files:
        raise FileNotFoundError(f"No negative examples found matching {pattern} in {data_dir}")
    
    return validate_jsonl_file(files[0], validate_negative_examples, "negative examples")


def load_and_validate_test_instructions(data_dir: Path = None) -> List[Dict]:
    """Load and validate test instructions"""
    if data_dir is None:
        from pathlib import Path
        import os
        data_dir = Path(os.getenv('CAI_BASE_DIR', '/workspace/runs/stage1_20250911_131105/code')) / 'artifacts'
    
    # Find test instructions file
    pattern = "test_instructions_*.jsonl"
    files = sorted(data_dir.glob(pattern), reverse=True)
    
    if not files:
        raise FileNotFoundError(f"No test instructions found matching {pattern} in {data_dir}")
    
    return validate_jsonl_file(files[0], validate_test_instructions, "test instructions")