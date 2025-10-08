# Future Enhancements Backlog

**Purpose**: Track potential improvements for future sessions
**Last Updated**: 2025-10-07

---

## High Priority

### 1. Best-of-N Response Generation

**Status**: Backlog
**Priority**: High (for data quality and DPO preparation)
**Estimated Effort**: 2-3 hours

**Description**:
Instead of generating 1 response per instruction, generate N responses (e.g., N=3-5) and pick the best based on pair critic margins.

**Benefits**:
- Higher data yield: 77% → ~95% with 3 attempts
- Better quality: Pick highest-margin response
- DPO preparation: Rejected responses = hard negatives
- Amortizes expensive instruction generation

**Implementation**:
```python
def generate_best_of_n(instruction, N=3):
    candidates = [generate_response(instruction) for _ in range(N)]
    critiques = [critic.critique_pair(instruction, c) for c in candidates]

    # Filter to good + confident
    good_candidates = [(c, crit) for c, crit in zip(candidates, critiques)
                       if crit.is_good and crit.confident]

    if good_candidates:
        # Pick best (highest margin)
        best = max(good_candidates, key=lambda x: x[1].margin)
        return best[0], best[1], [c for c in candidates if c != best[0]]  # best, critique, rejects

    return None, None, candidates  # All failed
```

**Cost Impact**:
- 3x response generation time (still cheap vs instruction generation)
- ~12 hours GPU instead of 6-7 hours
- Yields ~6k examples instead of ~4k with same instruction base

**When to Implement**:
- After current scale completes and SFT trains
- If 4k examples insufficient for good SFT performance
- When preparing for DPO (need preference pairs anyway)

**Files to Modify**:
- `scripts/generate_stage1_pilot_data.py` (add `--best-of-n N` parameter)
- `scripts/generate_stage1_scale_data.py` (passes through to pilot script)
- Update data schema to include rejected responses

---

### 2. Configurable Critique Rubrics

**Status**: Backlog
**Priority**: Medium
**Estimated Effort**: 1-2 hours

**Description**:
Make critic rubrics configurable instead of hardcoded.

**Benefits**:
- Tune strictness for different use cases
- Different rubrics for different instruction types
- A/B test different rubric formulations
- Could improve acceptance rates

**Implementation**:
```python
class CompletionStylePrompts:
    @classmethod
    def create_instruction_critic_prompt(
        cls,
        instruction: str,
        rubric_good: str = "clear, specific, achievable, safe",
        rubric_bad: str = "vague, impossible, unsafe, nonsense"
    ) -> str:
        prompt = f"""Evaluate this instruction for quality.

A = GOOD: {rubric_good}
B = BAD: {rubric_bad}

If uncertain, choose B (conservative).

INSTRUCTION:
{instruction}

Output exactly one letter on the next line: A or B
Label:"""
        return prompt
```

**Use Cases**:
- Stricter rubrics for safety-critical instructions
- Looser rubrics for creative tasks
- Type-specific rubrics (factual vs creative vs explanation)

**Files to Modify**:
- `scripts/utils/completion_prompts.py`
- Add command-line args to pilot/scale scripts

---

## Medium Priority

### 3. Parallel Shard Generation

**Status**: Backlog
**Priority**: Medium (optimization)
**Estimated Effort**: 1-2 hours

**Description**:
Generate shards in parallel on multi-GPU setup or across multiple pods.

**Benefits**:
- 10 shards × 1.5 hours = 15 hours sequential
- With 5 parallel workers: ~3 hours
- Significant speedup for large-scale generation

**Implementation**:
```python
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor

def run_parallel(self, total_count: int):
    with ThreadPoolExecutor(max_workers=num_gpus) as executor:
        futures = [
            executor.submit(self.generate_shard, shard_id, examples_per_shard, params)
            for shard_id in range(self.num_shards)
        ]
        shard_dirs = [f.result() for f in futures]
```

**Requirements**:
- Multi-GPU pod OR
- Orchestration across multiple single-GPU pods

**When to Implement**:
- If generating >50k examples
- If time is more valuable than GPU cost
- For Stage 2+ with larger datasets

---

### 4. Response Cleaning Audit/Improvements

**Status**: Backlog
**Priority**: Medium
**Estimated Effort**: 1 hour

**Description**:
Codex recommended auditing cleaning heuristics to ensure not over-trimming.

**Tasks**:
1. Log raw vs cleaned responses for 100 random examples
2. Manually inspect cases where cleaning made significant changes
3. Verify double-newline trimming is appropriate
4. Consider more sophisticated cleaning (preserve paragraph breaks)

**Files to Modify**:
- `scripts/utils/completion_prompts.py` (clean_response method)
- Add logging mode for audit

---

### 5. Enriched Few-Shot Examples

**Status**: Backlog
**Priority**: Medium (if acceptance remains low)
**Estimated Effort**: 1-2 hours

**Description**:
Add more diverse few-shot examples to instruction generation prompts.

**Current**: 15 seed instructions, random sample of 10
**Proposed**: 30-50 diverse instructions covering more types

**Benefits**:
- Could improve instruction acceptance (currently 65-70%)
- More diverse instruction distribution
- Better quality instructions

**Implementation**:
- Expand `INSTRUCTION_EXAMPLES` in `completion_prompts.py`
- Add type labels (factual, creative, explanation, etc.)
- Sample balanced across types

---

## Low Priority

### 6. Cache Loaded Model Between Runs

**Status**: Backlog
**Priority**: Low (optimization)
**Estimated Effort**: 1 hour

**Description**:
Keep model in memory for multiple generation runs instead of reloading each time.

**Benefits**:
- Save ~5 minutes per run (17 checkpoint shards)
- Useful for rapid iteration/testing

**Tradeoff**:
- Keeps GPU memory allocated
- Not needed for long single runs

---

### 7. Progressive QC Reporting

**Status**: Backlog
**Priority**: Low (nice-to-have)
**Estimated Effort**: 30 minutes

**Description**:
Report QC metrics progressively during generation, not just at end.

**Benefits**:
- Early detection of issues
- Can abort if metrics degrade
- Better visibility during long runs

**Implementation**:
- Checkpoint QC every 100 examples
- Log running metrics
- Optional: Early abort if thresholds fail

---

### 8. Resumable Scale Generation

**Status**: Backlog
**Priority**: Low (not needed if pods stable)
**Estimated Effort**: 1 hour

**Description**:
Make scale script check for completed shards and skip them on restart.

**Benefits**:
- Can stop/restart pod without losing progress
- Recover from partial failures
- More flexible for budget management

**Implementation**:
```python
def generate_shard(self, shard_id, ...):
    shard_dir = self.shards_dir / f"shard_{shard_id:02d}"

    # Check if already exists
    if (shard_dir / "pilot_data.jsonl").exists():
        logger.info(f"⏭️  Shard {shard_id} already exists, skipping")
        return shard_dir

    # Otherwise generate...
```

---

## Implementation Notes

### Before Implementing Any Enhancement

1. Check if it's needed (is current approach insufficient?)
2. Estimate cost/benefit
3. Request Codex review if methodology impact
4. Test on small pilot first
5. Document in IMPLEMENTATION_REGISTRY after completing

### Priority Guidelines

- **High**: Implement if needed for Stage 1 completion
- **Medium**: Implement if improves quality significantly
- **Low**: Implement only if time/budget available

---

**Last Updated**: 2025-10-07T23:30 UTC
**Next Review**: After Stage 1 SFT training completes
