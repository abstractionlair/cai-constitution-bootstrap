# Contamination Guard Spec (Clean Base-Model Loading)

Objective
- Guarantee that all base-model work is free of chat-template contamination and unintended special-token injection.

Required Utility
- CleanModelLoader (canonical). Responsibilities:
  - Load tokenizer and set tokenizer.chat_template=None; if present, default_chat_template=None.
  - Ensure add_special_tokens=False during tokenization.
  - Token-ID check: verify no Qwen chat template token IDs in any input position.
  - Delta check: assert len(tokenize(prompt, add_special_tokens=True)) == len(..., False) for sentinel prompts; any delta → abort.
  - Sentinel prompts: run a small suite to confirm base behavior (fails instruction-following sentinels; succeeds at simple completions).
  - Provenance: return loader_version (git SHA), model_name, quantization, template_disabled=True, add_special_tokens=False, sentinel_tests_passed=True.

Forbidden Patterns (CI Grep)
- Any script in active code calling AutoTokenizer/AUTOModel directly for base model without going through CleanModelLoader.
- Any manual setting of chat_template=None outside the utility.
- Any duplicate implementations of next-token A/B logprob scoring (must use instruction_critic).

Logging & Manifests
- Every run logs contamination checks and sentinel outcomes to artifacts and includes them in session manifests.

