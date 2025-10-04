# P2: Add Data Validation Checks Across Pipeline
**Assigned To**: claude_code
Source: Gemini Review 20250912_165500  
Priority: MEDIUM (P2)
Estimated Time: 30 minutes

## Issue Description
Pipeline scripts assume output from previous steps is correctly formatted. Adding validation checks would make the pipeline more robust to errors and provide better debugging information.

## Location
All pipeline scripts need validation at the beginning:
- `scripts/train_stage1_sft.py`
- `scripts/generate_diverse_negatives.py` 
- `scripts/create_preference_pairs_improved.py`
- `scripts/train_stage1_dpo_improved.py`
- `scripts/evaluate_stage1_comprehensive.py`

## Implementation Plan
Create validation utilities and add checks to each script:

```python
# New file: scripts/utils/data_validation.py
def validate_sft_data(data: List[Dict]) -> None:
    """Validate SFT training data format"""
    required_keys = ['instruction', 'response', 'formatted_text', 'instruction_type']
    
    for i, example in enumerate(data):
        # Check required keys
        for key in required_keys:
            if key not in example:
                raise ValueError(f"Missing key '{key}' in example {i}")
        
        # Check format structure
        if not example['formatted_text'].startswith('Instruction:'):
            raise ValueError(f"Invalid format in example {i}: missing 'Instruction:' prefix")
            
        if 'Response:' not in example['formatted_text']:
            raise ValueError(f"Invalid format in example {i}: missing 'Response:' section")
            
        if not example['formatted_text'].endswith('END'):
            raise ValueError(f"Invalid format in example {i}: missing 'END' suffix")

def validate_preference_pairs(pairs: List[Dict]) -> None:
    """Validate preference pair format"""
    required_keys = ['prompt', 'chosen', 'rejected', 'instruction']
    
    for i, pair in enumerate(pairs):
        for key in required_keys:
            if key not in pair:
                raise ValueError(f"Missing key '{key}' in pair {i}")
        
        # Check that chosen and rejected are different
        if pair['chosen'] == pair['rejected']:
            raise ValueError(f"Identical chosen/rejected in pair {i}")
```

## Add to Each Script
```python
# At start of main processing functions:
def load_and_validate_sft_data():
    data = load_sft_examples()
    validate_sft_data(data)  # New validation
    return data

def load_and_validate_preference_pairs():
    pairs = load_preference_pairs()
    validate_preference_pairs(pairs)  # New validation  
    return pairs
```

## Validation Checks Needed
1. **SFT Data**: Required keys, format structure, END tokens
2. **Preference Pairs**: Required keys, chosen≠rejected, valid prompts
3. **Negatives**: Required keys, valid negative types
4. **Test Instructions**: Required keys, no overlap with training
5. **Model Checkpoints**: Directory exists, required files present

## Success Criteria
- [ ] `scripts/utils/data_validation.py` created
- [ ] Validation functions for each data type
- [ ] All pipeline scripts include validation calls
- [ ] Clear error messages for validation failures
- [ ] Early failure prevents wasted computation

## Impact
**MEDIUM** - Prevents pipeline failures due to malformed data, provides better debugging, increases robustness for automated execution.