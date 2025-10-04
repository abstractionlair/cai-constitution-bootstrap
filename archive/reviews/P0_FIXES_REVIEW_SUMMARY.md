# P0 Fixes Review Summary
Date: 2024-12-28 16:00
Reviews Analyzed: Gemini and Codex responses to 20241228_153500_p0_fixes

## Overall Status
- **Gemini**: ✅ All fixes approved, ready to deploy
- **Codex**: ⚠️ Critical issues remain, DO NOT DEPLOY yet

## Critical Issues That Block Deployment

### 1. Template/Key Mismatch Bug [FATAL]
**Problem**: Template placeholders don't match the keys used in formatting
- `GENERATION_TEMPLATES` uses `{content_type}` and `{topic}`
- But code formats with `prompt=...`
- This will cause `KeyError` at runtime and crash

**Fix Required**:
```python
# In data_formatter.py, fix generate_generation_instructions:
formatted_instruction = template.format(
    content_type=content_type,  # NOT prompt=
    topic=topic
)

# Similar fix for generate_response_instructions:
formatted_instruction = template.format(
    input=input_text  # NOT scenario=
)
```

### 2. Cross-Run Data Leakage [CRITICAL]
**Problem**: Evaluation set is generated fresh each time without checking against training data
- Current assertions only check within a single run
- Eval generator uses different seed, can overlap with training

**Fix Required**:
1. Save training instructions to `data/stage1/train_instructions.jsonl`
2. Load and filter against them when creating eval set
3. Create persistent `eval_instructions.jsonl` that's guaranteed disjoint
4. Add overlap verification report

### 3. Evaluation Prompt Mismatch [HIGH]
**Problem**: Evaluation sends raw instructions to base model
- Base model expects completion-style prompts
- This unfairly penalizes the base model in comparisons

**Fix Required**:
```python
# In evaluate_stage1.py, wrap base model prompts:
if model_type == "base":
    prompt = completion_prompts.create_response_prompt(instruction)
else:
    prompt = instruction  # Trained model can handle raw instructions
```

## What's Working Well

### Gemini Confirmed:
1. ✅ Completion-style prompting correctly implemented
2. ✅ Few-shot examples properly structured
3. ✅ Within-run data leakage prevention working
4. ✅ 8-bit precision standardized across pipeline
5. ✅ RunPod compatibility maintained

## Additional Issues (Non-Blocking but Important)

### Medium Priority:
1. **Few-Shot Coverage**: Examples are too simple/trivial
   - Add diverse, challenging examples
   - Include negative cases (wrong answers)
   - Cover all instruction types better

2. **Constitution Tracking**: Only using first principle
   - Sample from all principles
   - Track which principle was used
   - Report distribution of principle usage

3. **Pool Sizes**: Still too small (24 QA, etc.)
   - Increase to at least 100 per type
   - For robust claims, need 600-800 total eval items

### Statistical Improvements Needed:
1. Use McNemar's test for paired comparisons
2. Report confidence intervals (Wilson for proportions)
3. Add effect sizes (Cohen's h)
4. Bootstrap confidence intervals for differences
5. Control for multiple comparisons (Benjamini-Hochberg)

## Immediate Action Items

### P0 - Must Fix Before Any Run:
1. **Fix template placeholder bug** (15 min)
2. **Fix cross-run data leakage** (1 hour)
3. **Fix evaluation prompting** (30 min)

### P1 - Should Fix Soon:
1. Improve few-shot examples (1 hour)
2. Add constitution tracking (30 min)
3. Expand data pools (1 hour)

### P2 - For Publication Quality:
1. Add statistical tests (2 hours)
2. Create ablation studies (2 hours)
3. Add reproducibility tracking (1 hour)

## Deployment Decision
**DO NOT DEPLOY CURRENT CODE**

The template bug will cause immediate crashes. The data leakage and evaluation issues invalidate any results. These must be fixed first.

## Estimated Time to Fix Critical Issues
- Template bug: 15 minutes
- Data leakage: 1 hour
- Evaluation prompting: 30 minutes
- **Total: ~2 hours**

## Next Steps
1. Fix the three critical issues
2. Test with small sample (10 examples) to verify no crashes
3. Run full pipeline with fixes
4. Monitor for 95% success gate
5. Address medium priority issues for publication quality
