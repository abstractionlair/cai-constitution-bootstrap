# P0: Remove Instruction-Style Templates

**Priority**: P0 (Critical - Current templates assume instruction-tuning)
**Estimated Time**: 0.5 hours
**Created**: 2024-12-28 14:45

## Problem
The current templates in `data_formatter.py` include instruction-style formats that won't work with a base model (e.g., "Human: {instruction}\nAssistant:"). These need to be replaced with completion-friendly formats.

## Context
- Templates like "Human: X\nAssistant:" assume the model understands dialogue roles
- Base models don't understand these special tokens/formats
- Need pure completion-style templates

## Required Changes

### 1. Remove Instruction-Style Templates
In `scripts/utils/data_formatter.py`, update `InstructionTemplates` class:

**REMOVE these templates:**
```python
# These assume instruction-tuning:
"Instruction: {instruction}\nResponse:",
"Human: {instruction}\nAssistant:", 
"Task: {instruction}\nOutput:",
"Please {instruction}",
```

**REPLACE with completion-style templates:**
```python
COMPLETION_STYLE_TEMPLATES = [
    "When asked '{instruction}', the answer is:",
    "Question: {instruction}. Answer:",
    "The response to '{instruction}' would be:",
    "Given the request '{instruction}', one would respond:",
    "{instruction}. The appropriate response is:",
]
```

### 2. Update QA Templates
**OLD:**
```python
QA_TEMPLATES = [
    "Answer this question: {question}",  # Too instruction-like
    "Question: {question}\nAnswer:",     # OK but needs context
    "Q: {question}\nA:",                 # OK but needs context
]
```

**NEW:**
```python
QA_COMPLETION_TEMPLATES = [
    "The answer to '{question}' is:",
    "When someone asks '{question}', the correct answer is:",
    "Q: {question} A:",  # Keep this one, it's completion-style
    "{question} The answer is:",
]
```

### 3. Update Generation Templates
**OLD:**
```python
GENERATION_TEMPLATES = [
    "Write {content_type} about {topic}",  # Too instruction-like
    "Generate {content_type} about {topic}",  # Too instruction-like
]
```

**NEW:**
```python
GENERATION_COMPLETION_TEMPLATES = [
    "Here is {content_type} about {topic}:",
    "A {content_type} about {topic} would be:",
    "An example of {content_type} about {topic}:",
    "{content_type} about {topic}:",
]
```

### 4. Update Response Templates
**OLD:**
```python
RESPONSE_TEMPLATES = [
    "Respond to this: {input}",  # Too instruction-like
    "Reply to: {input}",          # Too instruction-like
]
```

**NEW:**
```python
RESPONSE_COMPLETION_TEMPLATES = [
    "When someone says '{input}', an appropriate response would be:",
    "Person A: {input}\nPerson B:",
    "Statement: {input}\nResponse:",
    "After hearing '{input}', one might say:",
]
```

## Files to Modify
- `scripts/utils/data_formatter.py`

## Success Criteria
- [ ] All instruction-style templates removed
- [ ] All templates work as pure text completion
- [ ] No templates assume role understanding (Human/Assistant)
- [ ] No templates use imperative commands
- [ ] Templates guide completion naturally

## Testing
1. Generate sample with each template
2. Verify base model can complete them naturally
3. Check that completions are appropriate responses
4. No template should confuse the base model

## Notes
- This is a quick but critical fix
- Base models complete text, they don't follow commands
- Templates should feel like natural text completion
- Avoid any format that implies the model understands its role
