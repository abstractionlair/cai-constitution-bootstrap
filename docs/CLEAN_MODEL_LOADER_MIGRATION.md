# Clean Model Loader Migration Guide

**Created**: 2025-10-04
**Purpose**: Migrate to centralized, safe base model loading

---

## The Problem

We've been manually disabling chat templates in each script:

```python
# In every script:
tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-32B")
tokenizer.chat_template = None  # Easy to forget!
if hasattr(tokenizer, 'default_chat_template'):
    tokenizer.default_chat_template = None
inputs = tokenizer(prompt, add_special_tokens=False, ...)  # Also easy to forget!
```

**Risks**:
- ❌ Forgetting to disable `chat_template` → contamination
- ❌ Forgetting `add_special_tokens=False` → contamination
- ❌ Forgetting to check `default_chat_template` → contamination
- ❌ Code duplication across 10+ scripts
- ❌ No centralized verification

**What happened**: We reimplemented contamination prevention in every script and still archived 3 scripts for contamination issues!

---

## The Solution

**New**: `scripts/utils/clean_model_loader.py`

Provides `CleanModelLoader` class that:
- ✅ Automatically disables both chat templates
- ✅ Automatically uses `add_special_tokens=False`
- ✅ Verifies no contamination markers in tokens
- ✅ Logs all safety checks
- ✅ Single source of truth
- ✅ Can't forget steps

---

## Usage

### Simple (Function-based)

```python
from utils.clean_model_loader import load_clean_base_model

# Load model (guaranteed clean)
model, tokenizer = load_clean_base_model()

# Generate (need to use CleanModelLoader for this)
```

### Advanced (Class-based)

```python
from utils.clean_model_loader import CleanModelLoader

# Initialize loader
loader = CleanModelLoader("Qwen/Qwen2.5-32B", load_in_4bit=True)

# Load model
model, tokenizer = loader.load()

# Tokenize cleanly (built-in)
inputs = loader.tokenize_clean(tokenizer, "Your prompt")

# Generate cleanly (built-in)
response = loader.generate(
    model,
    tokenizer,
    "Your prompt",
    max_new_tokens=128,
    temperature=0.7
)
```

---

## When to Use

### Use `clean_model_loader.py` for:
- ✅ Base model evaluation
- ✅ Base model data generation
- ✅ Verification tests
- ✅ Any scenario where contamination would invalidate results

### Use `model_loader.py` (Unsloth) for:
- ✅ Training (SFT, DPO)
- ✅ When you need FastLanguageModel
- ✅ When you need LoRA preparation

---

## Migration Status

### Scripts Already Using Clean Loading

These scripts manually implement clean loading (should migrate to use `CleanModelLoader`):

1. ✅ `test_base_model_ultra_clean.py` - Lines 49, 128
2. ✅ `evaluate_instruction_following.py` - Lines 194, 221
3. ✅ `generate_stage1_sft_data.py` - Lines 130, 273

**Migration**: Optional but recommended for consistency

### Scripts That Need Clean Loading

These scripts currently lack contamination prevention:

1. ❌ `baseline_assessment.py` - May use `model_loader.py` (unsafe)
2. ❌ `generate_diverse_negatives.py` - Check if uses base model
3. ❌ Any evaluation scripts not listed above

**Migration**: Required before use

---

## Migration Steps

### For Existing Scripts

**Before**:
```python
from transformers import AutoTokenizer, AutoModelForCausalLM

# Load tokenizer
tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-32B")

# CRITICAL: Disable chat template
tokenizer.chat_template = None
if hasattr(tokenizer, 'default_chat_template'):
    tokenizer.default_chat_template = None

# Load model
model = AutoModelForCausalLM.from_pretrained(...)

# Tokenize
inputs = tokenizer(prompt, add_special_tokens=False, ...)

# Generate
outputs = model.generate(**inputs, ...)
response = tokenizer.decode(outputs[0][input_len:], skip_special_tokens=True)
```

**After**:
```python
from utils.clean_model_loader import CleanModelLoader

# Load with safety guarantees
loader = CleanModelLoader("Qwen/Qwen2.5-32B")
model, tokenizer = loader.load()

# Generate cleanly (all safety built-in)
response = loader.generate(model, tokenizer, prompt, max_new_tokens=128)
```

**Benefits**:
- Fewer lines of code
- Can't forget safety steps
- Verified contamination-free
- Centralized updates

---

## Verification

The loader automatically verifies:

1. **Template disabled**: Checks `chat_template` and `default_chat_template` are None
2. **Token verification**: Checks for contamination markers in tokenized output
3. **Logging**: All safety checks logged for audit trail

If contamination detected:
```python
RuntimeError: Chat template contamination detected!
```

---

## Future Scripts

**Template for new base model scripts**:

```python
#!/usr/bin/env python3
"""
My New Script
"""

from utils.clean_model_loader import CleanModelLoader

def main():
    # Initialize clean loader
    loader = CleanModelLoader("Qwen/Qwen2.5-32B")

    # Load model (guaranteed safe)
    model, tokenizer = loader.load()

    # Your logic here
    prompts = ["test1", "test2"]

    for prompt in prompts:
        response = loader.generate(model, tokenizer, prompt)
        print(f"Prompt: {prompt}")
        print(f"Response: {response}")

    # Cleanup
    del model, tokenizer
    torch.cuda.empty_cache()

if __name__ == "__main__":
    main()
```

---

## Testing

Test the loader:
```bash
python scripts/utils/clean_model_loader.py
```

Should show:
- ✅ Clean model loading
- ✅ No contamination detected
- ✅ Test generations (should NOT follow instructions cleanly)

---

## Documentation

See:
- `/docs/BASE_MODEL_TRUTH.md` - Why contamination matters
- `/docs/IMPLEMENTATION_REGISTRY.md` - When to use which loader
- `/scripts/utils/clean_model_loader.py` - Source code with full docstrings

---

## Questions?

**Q: Should I migrate existing working scripts?**
A: Optional but recommended. Existing scripts with manual clean loading work fine, but centralizing makes future maintenance easier.

**Q: What if I need Unsloth features?**
A: Use `model_loader.py` for training. Use `clean_model_loader.py` only for evaluation/generation.

**Q: Can I use this for instruction-tuned models?**
A: Yes, but it's designed for base models. For instruct models, disabling templates isn't necessary (they're already tuned).

**Q: What if I need custom quantization?**
A: `CleanModelLoader.__init__()` accepts all quantization options (4bit, 8bit, none).

---

**Bottom line**: Use `CleanModelLoader` for base model work. It's safer, simpler, and prevents the contamination issues that plagued our earlier scripts.
