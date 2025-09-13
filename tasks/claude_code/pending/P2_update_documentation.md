# P2: Update Documentation for Completion-Style Approach

**Priority**: P2 (Medium - Important for understanding)
**Estimated Time**: 0.5 hours
**Created**: 2024-12-28 14:50

## Problem
Current documentation and specifications assume instruction-following behavior. Need to update to reflect completion-style bootstrapping approach.

## Context
- Specs talk about "following instructions" but base models don't do that
- Need to document the completion-style approach clearly
- Important for publication and reproducibility

## Required Changes

### 1. Update Stage 1 Specification
In `specs/stage_1_explicit_instructions.md`:
- Change title from "Explicit Instruction Following" to "Bootstrapping Instruction-Response Patterns"
- Update explanation to clarify we're teaching completion patterns, not instruction following
- Add section on completion-style prompting
- Include examples of all completion prompts

### 2. Create Completion Prompting Guide
Create `specs/completion_prompting_guide.md`:
```markdown
# Completion-Style Prompting for Base Models

## Why Completion Style?
- Base models are trained to complete text, not follow instructions
- No special tokens or role understanding
- Must frame everything as natural text completion

## Prompting Patterns

### Generating Instructions
```
Here are examples of instructions:
- [example 1]
- [example 2]
- [example 3]

Another instruction would be:
```

### Generating Responses
```
When asked '[instruction]', the response is:
```

### Generating Critiques
```
Instruction: '[instruction]'
Response: '[response]'
This response [complete with critique]
```

### Generating Improvements
```
Original: '[response]'
Issues: '[critique]'
Improved version:
```

## Key Principles
1. Never use imperative commands
2. Always provide few-shot examples
3. Frame as natural text completion
4. Include context in the prompt
5. Avoid role-based formatting
```

### 3. Update README
In main README or project documentation:
- Add section explaining base model vs instruction-tuned
- Clarify that we're bootstrapping from pure completion
- Explain why this is more interesting/challenging
- Note that this is true self-bootstrapping

### 4. Update PERSISTENT_STATE.md
Add note about completion-style prompting requirement:
```markdown
## Critical Implementation Detail
We are using a BASE model (Qwen-2.5-32B base), not instruction-tuned.
ALL prompting must be completion-style:
- No imperative commands
- No role-based formatting  
- Frame everything as text completion
- Use few-shot examples

This is TRUE bootstrapping from a base model.
```

## Files to Create/Modify
- Modify: `specs/stage_1_explicit_instructions.md`
- Create: `specs/completion_prompting_guide.md`
- Modify: `README.md` or main documentation
- Modify: `PERSISTENT_STATE.md`

## Success Criteria
- [ ] Documentation clearly explains completion-style approach
- [ ] No references to "instruction following" for base model
- [ ] Examples provided for all prompt types
- [ ] Rationale for approach is clear
- [ ] Reproducibility instructions updated

## Notes
- This documentation is critical for the publication
- Must be clear about what makes this true bootstrapping
- Helps future implementers avoid the same mistakes
- Important for academic validity of the approach
