# Prompts & Labels Spec (Canonical Contracts)

Purpose
- Define canonical prompt formats for generation and single-token A/B critics to ensure consistency across scripts and phases.

Response Generation Prompt
- Template: "Instruction: {instruction}\nResponse:"
- Decoding (default): max_new_tokens≈80, temperature=0.3–0.5, top_p=0.9, repetition_penalty≈1.1, do_sample=True.
- Stop/trim rules: split on ‘###END###’ if present; otherwise trim at first of double-newline, or a line beginning with Instruction|Q:|A:|Response:, or common “new question” starters; final strip().

Instruction Generation Prompt (completion-style)
- Few-shot numbered list of diverse instruction types; end mid-list and let model continue (no chat template). Parse numbered lines into atomic instructions and filter invalid/meta lines.

Critic Prompt (Instruction Quality)
- Header: brief rubric; A=good, B=bad; conservative rule: if uncertain choose B.
- Body:
  INSTRUCTION:\n{instruction}\n\nOutput exactly one letter on the next line: A or B\nLabel:
- Decision: compute logprobs for next token on ‘A’ and ‘B’ variants (with and without leading space), pick higher logprob; margin = |logpA - logpB|; confident if margin ≥ threshold.

Critic Prompt (Instruction+Response Pair)
- Similar structure with rubric for format/accuracy/refusal correctness; include RESPONSE (first paragraph only) to keep token budget small.

Single-Token Contract
- Decisions are made by reading next-token logprobs, not by sampling. Scripts must not attempt to “generate” the label; they must score A vs B.

Contamination Rules
- Base-model always in completion mode; no chat templates; add_special_tokens=False. Verification via token-ID checks and add_special_tokens delta.

