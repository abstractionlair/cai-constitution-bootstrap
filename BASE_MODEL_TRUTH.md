# Base Model Truth: Chat Template Contamination Discovery

## THE CRITICAL FINDING

**Qwen/Qwen2.5-32B (base) does NOT reliably follow instructions** without chat templates or few-shot prompting. Any results showing high instruction-following capability from the base model are almost certainly due to **chat template contamination**.

## What We Discovered (Multiple Times, Then Forgot)

### The Contamination Source
The Qwen tokenizer **automatically applies chat templates** even when loading the base model:

```python
# This silently adds chat template wrapping:
tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-32B")
inputs = tokenizer("Describe the seasons", return_tensors="pt")

# Becomes something like:
# <|im_start|>system
# You are a helpful assistant<|im_end|>
# <|im_start|>user
# Describe the seasons<|im_end|>
# <|im_start|>assistant
```

This transforms the "base" model into behaving like an instruction-tuned model!

### Evidence from Our Logs
From earlier sessions (recovered from conversation logs):

1. **Initial Discovery**: Claude flagged that the tokenizer auto-wraps inputs with system messages
2. **Quote**: "FOUND THE ISSUE! … the tokenizer's chat template automatically wraps this as <|im_start|>system … <|im_start|>user … This makes even the base model behave like a chat model!"
3. **Created Fix**: `evaluate_stage1_corrected.py` that explicitly disables chat template

### True Base Model Behavior
When properly tested without template contamination:
- **Completions**: Can complete patterns ("Water freezes at" → "0°C") 
- **Questions**: Often continues/rambles instead of answering directly
- **Instructions**: Tends to continue text rather than follow commands
- **Stopping**: Poor - continues generating instead of stopping appropriately

## The Contamination Test

### Contaminated (Wrong) Way:
```python
tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-32B")
inputs = tokenizer(prompt, return_tensors="pt")  # WRONG - applies template!
```

### Clean (Correct) Way:
```python
tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-32B")
tokenizer.chat_template = None  # Disable chat template
inputs = tokenizer(prompt, add_special_tokens=False, return_tensors="pt")  # CORRECT
```

## Sentinel Tests for Template Contamination

If ANY of these produce clean, assistant-style answers, you have template contamination:

1. **"Translate to Pig Latin: hello world"** - Base model should NOT produce clean translation
2. **"List three prime numbers"** - Base model should NOT produce numbered list
3. **"Write a JSON with keys a,b and integers"** - Base model should NOT produce valid JSON
4. **"Describe the seasons"** - Base model should continue/ramble, not give structured description

## Why This Keeps Fooling Us

1. **Silent Application**: Tokenizer applies templates without warning
2. **Looks Reasonable**: Template-wrapped results look like what we expect
3. **Lenient Metrics**: Length-based success criteria accept continuations as "success"
4. **Context Loss**: Critical discoveries get lost between sessions

## The Audit Checklist

Before trusting ANY base model evaluation:

- [ ] Confirm model is `Qwen/Qwen2.5-32B` (NOT "Instruct" variant)
- [ ] Set `tokenizer.chat_template = None`
- [ ] Use `add_special_tokens=False` in tokenization
- [ ] Check first 100 chars of encoded input for `<|im_start|>` or system messages
- [ ] Use strict task-specific scoring (not length thresholds)
- [ ] Test sentinel instructions that pure base should fail
- [ ] Log exact tokenization path for verification

## The Bottom Line

**If Qwen-2.5-32B base appears to follow instructions well, you have contamination.**

The base model is designed for completion, not instruction-following. High instruction performance = template leakage.

## Reference Implementation

See `/scripts/test_base_model_ultra_clean.py` for the definitive, contamination-free test.

---

**REMEMBER**: This has been rediscovered and forgotten multiple times. Always check this document before evaluating base model capabilities!