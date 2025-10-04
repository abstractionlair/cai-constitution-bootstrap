# Task: Fix Contamination Verification in CleanModelLoader

**Priority**: P1 (HIGH - Should fix before deployment)
**Created**: 2025-10-04
**Assigned To**: claude_code
**Status**: Pending
**From Review**: reviews/responses/20251004_dry_policy_and_migration_codex.md

---

## Problem

Current contamination verification in CleanModelLoader:
- Only checks first 10 tokens (not full input)
- Uses generic string markers (false positives possible)
- Doesn't check outputs
- Doesn't use token IDs

**Codex finding** (HIGH #1):
> "The check inspects only the first ~10 input tokens and flags generic strings like system/user/assistant which can legitimately occur in prompts. It does not verify outputs, and does not assert template-token IDs explicitly. False alarms or missed contamination if markers appear later."

---

## Impact

- **Weak assurance**: Contamination could slip through
- **False positives**: Generic words trigger false alarms
- **Limited coverage**: Only first 10 tokens checked

---

## Current Implementation

**File**: `scripts/utils/clean_model_loader.py`
**Lines**: 221, 229

```python
# Current (inadequate)
first_10_tokens = inputs['input_ids'][0][:10].tolist()
token_preview = self.tokenizer.decode(first_10_tokens, ...)
contamination_markers = ['<|im_start|>', '<|im_end|>', 'system', 'user', 'assistant']
if any(marker in token_preview for marker in contamination_markers):
    raise RuntimeError("Chat template contamination detected!")
```

**Problems**:
1. Only first 10 tokens
2. String matching (not token IDs)
3. Generic words like "system", "user", "assistant"
4. No output verification

---

## Solution

### 1. Check All Tokens (Not Just First 10)

```python
# Check full input
all_token_ids = inputs['input_ids'][0].tolist()
token_text = self.tokenizer.decode(all_token_ids, skip_special_tokens=False)
```

### 2. Use Token IDs Instead of Strings

```python
# Qwen-specific special token IDs
QWEN_CHAT_TOKENS = {
    151644,  # <|im_start|>
    151645,  # <|im_end|>
    # Add other known chat template token IDs
}

# Check for token ID presence
if any(tid in all_token_ids for tid in QWEN_CHAT_TOKENS):
    raise RuntimeError(f"Chat template token IDs detected: {set(all_token_ids) & QWEN_CHAT_TOKENS}")
```

### 3. Verify add_special_tokens Difference

**Sentinel test**: Encode same prompt with and without special tokens, compare lengths

```python
def _verify_no_template_injection(self, tokenizer, prompt):
    """Verify that add_special_tokens makes no difference"""
    with_special = tokenizer(prompt, add_special_tokens=True)['input_ids']
    without_special = tokenizer(prompt, add_special_tokens=False)['input_ids']

    if len(with_special) != len(without_special):
        raise RuntimeError(
            f"Template injection detected: add_special_tokens=True adds {len(with_special) - len(without_special)} tokens"
        )
```

### 4. Add Sentinel Prompts

**Test on known problematic prompts** at initialization:

```python
SENTINEL_PROMPTS = [
    "Translate to French: hello",
    "Answer this: What is 2+2?",
    "List three colors",
]

for prompt in SENTINEL_PROMPTS:
    self._verify_no_template_injection(tokenizer, prompt)
```

### 5. Return Provenance Metadata

```python
def load(self):
    """Load model and return provenance info"""
    model, tokenizer = self._load_model()

    # Get git SHA
    import subprocess
    try:
        git_sha = subprocess.check_output(['git', 'rev-parse', 'HEAD']).decode('ascii').strip()
    except:
        git_sha = "unknown"

    # Return provenance
    provenance = {
        'loader_version': git_sha,
        'template_disabled': True,
        'model_name': self.model_name,
        'quantization': self.load_in_4bit and '4bit' or (self.load_in_8bit and '8bit' or '16bit'),
    }

    return model, tokenizer, provenance
```

---

## Implementation

**File**: `scripts/utils/clean_model_loader.py`

**Changes needed**:

1. **Lines 221-229**: Replace string-based check with token-ID check
2. **Add method**: `_verify_no_template_injection()`
3. **Add method**: `_run_sentinel_tests()`
4. **Modify load()**: Return provenance metadata
5. **Update tokenize_clean()**: Check all tokens, use token IDs
6. **Update generate()**: Check outputs too (optional)

**Backward compatibility**: Keep existing API, add optional provenance return

---

## Testing

**Sentinel prompts** should pass (no contamination):
```python
loader = CleanModelLoader("Qwen/Qwen2.5-32B")
model, tokenizer, prov = loader.load()

# Should work
loader.tokenize_clean(tokenizer, "Translate to French: hello")
loader.tokenize_clean(tokenizer, "What is the capital of France?")

# Should raise if contaminated
# (should NOT happen with proper implementation)
```

**Verify token IDs** are Qwen-specific:
```python
# Check actual Qwen chat token IDs
tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-32B")
print(tokenizer.special_tokens_map)
print(tokenizer.added_tokens_encoder)
```

---

## Completion Criteria

- [ ] Check all tokens (not just first 10)
- [ ] Use token IDs instead of string matching
- [ ] Add sentinel prompt tests at initialization
- [ ] Verify add_special_tokens difference
- [ ] Return provenance metadata from load()
- [ ] Remove generic markers ("system", "user", "assistant")
- [ ] Test with known-clean prompts
- [ ] Update documentation in CleanModelLoader docstring

---

## References

- reviews/responses/20251004_dry_policy_and_migration_codex.md - Codex review (HIGH #1, recommendations)
- scripts/utils/clean_model_loader.py - Current implementation
- docs/BASE_MODEL_TRUTH.md - Contamination documentation
