# Review Response: Data Generation Delimiter Fix

**Reviewer**: codex
**Date**: 2025-10-04
**Request**: 20251004_data_generation_delimiter_fix.md

## Summary
⚠️ Issues Found (approve with safeguards)

- Root cause diagnosis is sound: the few-shot format induces a multi-QA continuation pattern. A distinct delimiter plus post-processing is a reasonable fix, but add runtime stop controls, QC checks, and a short pilot to avoid wasting GPU on bad data. Also confirm no chat-template contamination via sentinel tests.

## Issues Found

### 🚨 CRITICAL
1. Single-guard solution risks residual runaway and contamination of the full dataset
   - Description: Relying only on a textual delimiter and split() is brittle. Some generations will omit or echo the delimiter or continue past it.
   - Impact: Silent inclusion of multi-QA chains in SFT data; training harmed; dollars wasted.
   - Recommendation: Layered guards (see Recommendations): generation stop criteria, strict post-processing, and QC metrics with auto-reject/regen for bad samples before scaling.

### ⚠️ HIGH
1. Generation API does not enforce stopping on delimiter
   - Description: Current `loader.generate` lacks `stop_strings`/stopping criteria support; callers only post-process.
   - Impact: More tokens generated than needed; higher chance of spillover and token-limit truncation; costlier sampling.
   - Recommendation: For now, keep split() but reduce `max_new_tokens` and temperature for data gen, and add a regex-based hard cutoff heuristic. Long-term, add a stopping-criteria hook in the loader.

2. Prompt still teaches “continue pattern” unless target section makes “one response then stop” obvious
   - Description: Even with `###END###` in examples, the target block should bias a single completion strongly.
   - Impact: Residual continuation especially at higher temperatures.
   - Recommendation: Add an explicit “Response:” cue right before generation and ensure examples end with delimiter immediately after the response line to strengthen the boundary.

3. Missing QC acceptance/reject policy prior to scaling to 15k
   - Description: The testing plan mentions manual inspection; needs automatic metrics and thresholds in the pilot to decide pass/fail.
   - Impact: Risk of subjective pass; small issues scale into systemic noise.
   - Recommendation: Define automated counters (see below) and set cutoffs; auto-regenerate failed items up to K attempts.

### 💡 SUGGESTIONS
1. Delimiter choice
   - `###END###` is serviceable. Alternatives: `<<<END>>>` or a rare token sequence. Using EOS is unreliable for base completions. Keep `###END###` but scan for false positives (very unlikely).
2. Token budget
   - Lower `max_new_tokens` to 64–80 for Stage 1 responses; most should be <50 tokens. Fewer tokens reduce continuation risk and cost.
3. Temperature/top-p
   - Use `temperature=0.3–0.5`, `top_p=0.9`, keep `repetition_penalty≈1.1`. Higher temps increase chaining.
4. Heuristic post-processing
   - After `split('###END###')[0]`, trim at the first of: double newline, a line starting with `Instruction`, `Q:`, `A:`, or `Response:`. Discard if >2 such markers appear.
5. QC metrics (pilot of 50–200 items)
   - % with delimiter present in raw output (target >80%).
   - % runaways after cleaning (target <5%).
   - % hitting token limit (target <10%).
   - Median/mean token count (target median <40).
   - Count of forbidden markers (`Instruction`, `Q:`, `###END###`) in final responses (target 0).
6. Sentinel contamination check
   - Run loader sentinel tests pre-gen; add 3–5 sentinel prompts in the pilot and assert failures consistent with clean base model. If any sentinel suggests instruct behavior, abort.
7. Few-shot structure
   - Ensure each example is exactly: `Instruction\nResponse\n###END###\n\n`. For target, end the prompt with `TargetInstruction\nResponse:` to nudge a single completion then split at delimiter.
8. Logging and provenance
   - Log whether delimiter was found, tokens generated, and reasons for any rejection. Save per-record provenance and per-batch QC summary.

## Recommendations
1. Approve the fix with layered controls:
   - Keep `###END###` + split() cleanup.
   - Reduce `max_new_tokens` to 64–80 for data gen; lower temperature to 0.3–0.5.
   - Add heuristic cutoff at markers (`Instruction`, `Q:`, `A:`, `Response:`) if delimiter missing.
   - Reject/regen items failing QC; cap retries (e.g., 2) then drop.
2. Run a 100–200 sample pilot on pod
   - Compute QC metrics automatically; only proceed to 15k if all thresholds are met (as in the request + metrics above).
3. Confirm root cause vs contamination
   - Run sentinel contamination tests and include a couple of clearly instruction-only prompts to verify expected “fail to follow” behavior.
4. Future improvement (non-blocking)
   - Add stop-string support to `CleanModelLoader.generate` via `StoppingCriteria` for `###END###`. This will cut tokens early and reduce risk/cost.

## Overall Assessment
- Direction is correct and likely to fix the runaway pattern. With the added safeguards (short pilot, lower token/temperature, stricter cleanup and QC, and sentinel checks), this is acceptable to proceed. Do not launch 15k generation until the pilot meets quantitative thresholds.

