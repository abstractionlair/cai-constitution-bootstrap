# P0: Fix Template Placeholder Mismatch Bug

**Priority**: P0 (FATAL - Will crash at runtime)
**Estimated Time**: 15 minutes
**Created**: 2024-12-28 16:05
**Source**: Codex Review 20241228_153500_p0_fixes.md

## Problem
Template placeholders don't match the keys used in string formatting, causing KeyError crashes.

## Specific Issues

### In `generate_generation_instructions`:
```python
# WRONG - Current code:
template = random.choice(self.templates.GENERATION_TEMPLATES)
formatted_instruction = template.format(prompt=prompt)  # BUG: No 'prompt' in template

# Templates use {content_type} and {topic}, not {prompt}
```

### In `generate_response_instructions`:
```python
# WRONG - Current code:
template = random.choice(self.templates.RESPONSE_TEMPLATES)  
formatted_instruction = template.format(scenario=scenario)  # BUG: No 'scenario' in template

# Templates use {input}, not {scenario}
```

## Required Fix

### 1. Fix `generate_generation_instructions` in `data_formatter.py`:
```python
def generate_generation_instructions(self, count: int = 250) -> List[Dict[str, Any]]:
    # ... existing code ...
    for i in range(count):
        content_type = random.choice(content_types)
        topic = random.choice(topics)
        template = random.choice(self.templates.GENERATION_TEMPLATES)
        
        # FIX: Use correct placeholder names
        formatted_instruction = template.format(
            content_type=content_type,
            topic=topic
        )
        # ... rest of code ...
```

### 2. Fix `generate_response_instructions` in `data_formatter.py`:
```python
def generate_response_instructions(self, count: int = 250) -> List[Dict[str, Any]]:
    # ... existing code ...
    for i, input_text in enumerate(selected_inputs):
        template = random.choice(self.templates.RESPONSE_TEMPLATES)
        
        # FIX: Use correct placeholder name
        formatted_instruction = template.format(input=input_text)
        # ... rest of code ...
```

## Testing
1. Run a quick test to generate 5 instructions of each type
2. Verify no KeyError exceptions
3. Check that formatted instructions look correct

## Files to Modify
- `scripts/utils/data_formatter.py`

## Success Criteria
- [ ] No KeyError when generating instructions
- [ ] All instruction types generate successfully
- [ ] Formatted instructions contain the expected content
