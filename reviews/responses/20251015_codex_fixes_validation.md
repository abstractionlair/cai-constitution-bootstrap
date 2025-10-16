🚨 CRITICAL – Writing directly to `codex.stdin` without guarding for `null` or attaching an `error` listener will crash the MCP server if the child exits early (e.g., bad API key, spawn failure). See `/Users/scottmcguire/mcp-servers/mcp-servers/codex-review/src/index.ts:178`. Please detect a missing stdin pipe and convert stream errors (`EPIPE`, `ERR_STREAM_WRITE_AFTER_END`) into a rejected promise instead of letting the process die.

⚠️ HIGH – The timeout currently issues only `SIGTERM` (`/Users/scottmcguire/mcp-servers/mcp-servers/codex-review/src/index.ts:172-175`). If Codex ignores that signal, the process can linger even though the promise was rejected. Add a short grace timer that escalates to `SIGKILL` so the child is guaranteed to terminate.

💡 Suggestion – Keep the 5-minute ceiling as the default but allow overrides (env var or tool argument) so callers can tighten or relax it as needed. Also consider using `codex.stdin.end(prompt)` plus an attached `stdin` error handler for cleaner buffering and resilience.

Summary: Fix the stdin crash path and add a SIGKILL fallback before treating these patches as safe. Full write-up is in `reviews/responses/20251013_codex_mcp_security_reliability_codex.md`. Natural next steps: 1) add the stdin guard/error handling and SIGKILL escalation, 2) expose an optional timeout override, 3) rerun the smoke tests you listed.
