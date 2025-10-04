# P2: Strengthen Loss Masking Robustness in SFT Training
**Assigned To**: claude_code
Source: Gemini Review 20250912_165500
Priority: MEDIUM (P2)
Estimated Time: 20 minutes

## Issue Description
The `SFTDataCollator` in `train_stage1_sft.py` determines masking boundaries by re-tokenizing the prompt separately. This can be fragile if tokenization boundaries shift when the prompt is part of the full text.

## Location
File: `scripts/train_stage1_sft.py`
Class: `SFTDataCollator`
Method: `__call__()` around lines 100-130

## Current Approach (Fragile)
```python
# Tokenize full sequence
full_encoding = self.tokenizer(full_text, ...)

# Tokenize just the prompt to find boundary  
prompt_encoding = self.tokenizer(prompt, ...)

# Mask based on prompt length
labels = input_ids.copy()
prompt_length = len(prompt_encoding['input_ids'])
for i in range(min(prompt_length, len(labels))):
    labels[i] = -100
```

## Suggested Fix (Robust)
```python
# Tokenize full sequence
full_encoding = self.tokenizer(full_text, ...)
input_ids = full_encoding['input_ids']

# Find response separator token sequence
separator = "\nResponse:"
separator_tokens = self.tokenizer(separator, add_special_tokens=False)['input_ids']

# Search for separator in full token sequence
mask_until = self.find_token_sequence(input_ids, separator_tokens)
if mask_until is not None:
    mask_until += len(separator_tokens)  # Include separator in mask
else:
    # Fallback to old method
    mask_until = len(prompt_encoding['input_ids'])

# Apply masking
labels = input_ids.copy()  
for i in range(min(mask_until, len(labels))):
    labels[i] = -100
```

## Helper Method Needed
```python
def find_token_sequence(self, tokens: List[int], pattern: List[int]) -> Optional[int]:
    """Find start index of pattern within tokens"""
    for i in range(len(tokens) - len(pattern) + 1):
        if tokens[i:i+len(pattern)] == pattern:
            return i
    return None
```

## Success Criteria
- [ ] Loss masking based on actual token sequence search
- [ ] Handles tokenization boundary edge cases
- [ ] Fallback to original method if separator not found
- [ ] Helper method for token sequence matching
- [ ] Validation that masking is applied correctly

## Impact
**MEDIUM** - Improves robustness of loss masking, reducing risk of training on instruction tokens due to tokenization edge cases.