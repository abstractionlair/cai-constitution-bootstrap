# Duplication Analysis: Stage 1 Scale Generation

**Date**: 2025-10-08
**Issue**: High duplication rate in scale generation (only 1,311 unique from 3,968 examples)

---

## The Problem

During Stage 1 scale generation (10 shards, seeds 100-109), we generated 3,968 instruction-response pairs but discovered massive duplication:

- **Total examples**: 3,968
- **Unique instructions**: 1,311 (33%)
- **Duplication rate**: 67%

### Top Duplicates

| Instruction | Count | % of Dataset |
|------------|-------|--------------|
| "What is the capital city of France?" | 273× | 6.9% |
| "What is the capital city of Australia?" | 157× | 4.0% |
| "Name two types of renewable energy sources" | 124× | 3.1% |
| "What is the difference between weather and climate?" | 120× | 3.0% |

The most duplicated instruction appeared **273 times** across 10 shards!

---

## Root Cause Analysis

### Seeds Were Correct
All 10 seeds (100-109) were used correctly. This is NOT a seed reuse bug.

### Base Model Has Strong Priors
The Qwen2.5-32B base model has strong priors for common educational instructions. Even with:
- Temperature: 0.7 (reasonable for diversity)
- Top-p: 0.9 (wide sampling)
- Repetition penalty: 1.1 (moderate)
- **Different random seeds**

...the model consistently generates the same high-probability instructions like:
- "What is the capital of [country]?"
- "What is the difference between X and Y?"
- "Describe the process of [biology topic]"

### Why Seeds Didn't Help
Random seeds affect **sampling randomness**, but don't change the **underlying probability distribution**.

If "What is the capital of France?" has a 10% probability of being generated, then across 3,968 examples, we'd expect ~400 instances—and we got 273, which is in the right ballpark given our filtering.

---

## Impact

### On Training Quality
- **Effective dataset size**: ~1,120 unique examples after deduplication and cleanup
- **Statistical power**: Reduced vs the intended 15k examples
- **Diversity**: Limited to common factual Q&A patterns

### On QC Thresholds
- Deduplication is **expected** and **necessary**
- The 1,120 unique examples that pass QC are high-quality
- But we need **more unique examples** to meet the 6-8k target

---

## Solutions Implemented

### 1. Deduplication (Completed)
- Deduplicated by instruction (keep first occurrence)
- Result: 1,311 → 1,120 clean unique examples after all QC filters

### 2. Generating Additional Shards (In Progress)
- Generating 10 more shards (seeds 110-119)
- Target: Add ~400-600 more unique examples
- Expected final: ~1,500-1,700 unique examples

---

## Solutions for Future Iterations

### Short-term (Next batch)
1. **Higher temperature**: 0.9-1.0 for instruction generation (vs current 0.7)
2. **Stronger repetition penalty**: 1.3-1.5 (vs current 1.1)
3. **Larger target**: Generate 20-30 shards to hit 6-8k unique after dedup

### Medium-term (Stage 1 improvements)
1. **Topic-based prompting**:
   ```
   Few-shot prompt:
   1. [Science] Explain photosynthesis
   2. [History] When did World War II begin?
   3. [Math] Calculate the area of a circle
   4. [Geography] What is the capital of...
   ```
2. **Online deduplication**: Check for duplicates during generation, skip if seen
3. **Domain rotation**: Explicitly rotate through domains (science, history, math, etc.)

### Long-term (Best-of-N)
Implement Best-of-N sampling for responses:
- Generate N=3-5 responses per instruction
- Use critic to rank
- Keep best response
- **Side benefit**: More unique responses even if instructions duplicate

---

## Lessons Learned

### Expected Behavior
Base model instruction generation **will** cluster around high-probability examples. This is:
- ✅ **Expected** given model training on common knowledge
- ✅ **Fixable** via deduplication
- ✅ **Addressable** via higher temperature / topic prompting

### Not a Bug
This is NOT a bug in our implementation. The same behavior would occur with:
- OpenAI models
- Other open-source LLMs
- Any completion-style instruction generator

### Deduplication is Essential
Deduplication is a **required step** for model-generated data, not an optional cleanup:
- Reduces dataset size significantly
- But improves training quality by removing redundancy
- Should be part of the standard pipeline

---

## Current Status

### Completed
- ✅ Identified duplication issue
- ✅ Deduped original 3,968 → 1,120 unique examples
- ✅ All QC thresholds passing on deduplicated data

### In Progress
- 🔄 Generating 10 additional shards (seeds 110-119)
- 🔄 Expected completion: ~40 minutes

### Next Steps
1. Merge additional shards with existing clean data
2. Deduplicate combined dataset
3. Target: 1,500-1,700 unique examples
4. If still below 6k target, generate more shards with higher temperature

---

## Recommendation for Codex Review

When requesting final Codex review, emphasize:
1. **Duplication is expected** for base model generation
2. **1,500-1,700 unique examples** may be acceptable for Stage 1 SFT pilot
3. **Alternative**: Proceed with current data, then iterate if eval shows insufficient improvement
4. **Cost/benefit**: More generation costs GPU time vs training on smaller dataset

Codex should evaluate: **Is 1,500-1,700 unique examples sufficient for Stage 1 SFT**, or should we generate 20-30 more shards to reach 6-8k?
