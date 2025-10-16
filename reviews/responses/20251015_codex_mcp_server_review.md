⚠️ Summary
- Implementation is close, but the Codex subprocess currently has no guardrails against hanging, which risks blocking Claude sessions when the CLI stalls.

⚠️ HIGH
- codex-review/src/index.ts:147 — `callCodex` never enforces a timeout or cancellation path. If `codex exec` stalls (network retry loop, new CLI prompt, or API throttling), the MCP handler waits forever, wedging the calling Claude session. Add an `AbortController`/timer that kills the child after a configurable deadline and surfaces a clear timeout error.

💡 Suggestions
- codex-review/src/index.ts:85 — Perform runtime validation (e.g., zod or JSON schema) on `request.params.arguments`; today a malformed request would quietly coerce to `'undefined'` and be forwarded to Codex.
- codex-review/src/index.ts:148-155 — Consider removing the literal quotes in `model_reasoning_effort="${reasoning_effort}"`; most CLIs expect `-c model_reasoning_effort=high`, so carrying quotes may cause future parsing issues.
- codex-review/src/index.ts:154-155 — For very large prompts, the OS argv limit (~128 KB) becomes a real risk. If you expect long review packs, fall back to piping the prompt on stdin or via a temp file.
- codex-review/src/index.ts:92-138 — Log `stderr` (maybe as metadata) even on success so operators can spot soft failures, and consider allowing a model allowlist / MaxReasoning guard to prevent accidental costly models.

Answers
- Q1: Spawning `codex exec` is reasonable for parity with existing workflows, but if you need finer-grained control (streaming, better error surfaces, larger prompts) migrate to the SDK once the tool stabilizes.
- Q2: Loading `OPENAI_API_KEY` from env and only inheriting it to the child is standard; just ensure the CLI binary is trusted and keep avoiding logs of the key.
- Q3: Aside from the timeout gap above, error handling is solid: you collect `stderr` and surface non-zero exits.
- Q4: Biggest TS gap is lack of runtime validation. You could also tighten `reasoning_effort` and `model` to literal unions and expose a config object for future extensions.
- Q5: Caching seems unnecessary (each review is bespoke), but lightweight rate limiting or a per-request cost guard would help keep Codex budget predictable.

Next Steps
- 1. Add the timeout/abort guard around the spawned process, plus a test that simulates a never-ending child.  
- 2. Layer in argument validation and, optionally, switch to stdin/temp-file input before shipping.
