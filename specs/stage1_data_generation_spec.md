# Stage 1 Data Generation Spec (Model-Generated + Logprob-Filtered)

Objective
- Produce ~15,000 high-quality instruction-following SFT examples using base-model completion prompts, single-token A/B critics with logprob margins, and layered QC.

Scope
- Instruction generation via completion-style prompting (no chat template).
- Response generation via completion-style "Instruction: …\nResponse:" prompts.
- Two critics: instruction quality; instruction+response pair quality. Both are single-token A/B with logprob margins.
- QC gating and manifests; no training unless QC passes.

Environment
- Pod: NVIDIA H100/H200 preferred for verification; /workspace is durable root.
- Env vars (export in session):
  - HOME=/workspace/home
  - XDG_CONFIG_HOME=/workspace/.config
  - HF_HOME=/workspace/.cache/huggingface
  - TRANSFORMERS_CACHE=/workspace/.cache/huggingface/transformers
  - HF_DATASETS_CACHE=/workspace/.cache/huggingface/datasets
  - TORCH_HOME=/workspace/.cache/torch
- Models: Pre-stage Qwen/Qwen2.5-32B snapshot under /workspace/models if possible; loaders should prefer local paths.

Core Utilities (canonical)
- CleanModelLoader: mandatory for all base-model work; enforces chat_template=None, add_special_tokens=False, and token-ID/sentinel checks.
- CompletionStylePrompts: canonical prompt builders for response generation; no ad-hoc prompt strings in scripts.
- instruction_generator: builds few-shot instruction lists and parses completions into candidate instructions.
- instruction_critic: exposes get_token_logprobs, critique_instruction_quality (A/B), critique_instruction_response_pair (A/B).

Prompt Contracts
- Instruction generation: few-shot numbered list of diverse instruction patterns; stop mid-list and let model continue. Output parsed into atomic instructions.
- Response generation: "Instruction: {instruction}\nResponse:" as the prompt; generate up to max_new_tokens with modest temperature; truncate using stop heuristics.
- Critics: append "Label:" and score A vs B by reading next-token logprobs. The decision is based on logprobs, not sampling.
  - A/B semantics (instruction): A=good (clear/specific/achievable/safe), B=bad (vague/impossible/unsafe/nonsense).
  - A/B semantics (pair): A=good (fulfills instruction; correct/format-safe/refuse briefly if unsafe), B=bad otherwise.

QC & Cleaning
- Delimiter: allow optional ‘###END###’ in few-shot examples; after generation, split on ‘###END###’ and keep first segment.
- Heuristics: if delimiter missing, trim at the first of: double-newline; a line starting with Instruction|Q:|A:|Response:; or common “new question” phrases.
- Token limits: count raw and cleaned tokens; treat raw tokens near max_new_tokens as a risk signal.
- Forbidden markers: remove or drop examples whose final response contains the delimiter or evaluator markers.

Pilot Parameters (reference)
- Instruction generation: generate 1.5–2.0× the target count to allow filtering; temperature≈0.7; top_p≈0.9; repetition_penalty≈1.1.
- Response generation: max_new_tokens≈80; temperature≈0.3–0.5; top_p≈0.9.
- Critics: confidence_threshold (logprob margin) = 1.0 (tunable). Only accept items with is_good and confident.

QC Thresholds (must pass to scale)
- Runaway after cleaning < 5% (responses containing extra new prompts/questions after cleanup).
- Token-limit hits < 10% (raw generation length close to/maxing out budget).
- No delimiter leakage in final responses (0 occurrences of ‘###END###’ in kept outputs).
- Median tokens of final responses < 40 (inspect distribution too).
- Critic acceptance rates reasonable: instruction acceptance and pair acceptance both ≥ 50% of generated (tunable after pilot).
- Contamination sentinels: all pass (base model exhibits expected failures on instruction-following sentinels and no template tokens detected).

Outputs
- JSONL with per-example records:
  - instruction, response
  - prompt, completion (optional for audit)
  - critic verdicts: instruction_critique, pair_critique (with logp_a, logp_b, margin, confident)
  - provenance metadata (see DATA_SCHEMAS_AND_PROVENANCE.md)
- QC summary JSON with metrics listed above and distributions (token counts, margins).
- Session manifest JSON (see DATA_SCHEMAS_AND_PROVENANCE.md) with environment, SHAs, loader_version, budgets.

Acceptance Tests
- A) Pilot run (100–200 examples) emits dataset.jsonl, qc_summary.json, and session_manifest.json.
- B) QC summary satisfies all thresholds above.
- C) Spot-check 10 random examples to verify instruction fidelity and trimming.
- D) Contamination guards logged and sentinel tests pass.

Scale Procedure
- Once pilot passes: shard generation across available GPUs by seed/instruction index; produce shard manifests; merge shards and recompute QC over the union. Keep originals for audit.

Notes
- This spec intentionally excludes preference pairs (DPO) to keep Stage 1 focused. If enabling DPO next, see stage1_dpo_pairs_spec (to be authored).

