# Codex MCP Server Security & Reliability Review — 2025-10-13

Summary: ⚠️ Blockers remain before we can rely on this change.

## Findings

🚨 CRITICAL — `stdin` write can crash the server when the Codex process exits early (`~/mcp-servers/mcp-servers/codex-review/src/index.ts:178`)
- Switching to stdin is the right mitigation for leaking prompts, but the new code writes immediately to `codex.stdin` without checking that the stream exists or attaching an error handler. If `codex` fails to spawn (ENOENT, permission issues) or terminates before the write completes (e.g., invalid API key causing an instant exit), Node will raise an `EPIPE`/`ERR_STREAM_WRITE_AFTER_END` error on the stream. Because that error is unhandled, the entire MCP server will crash, which is a regression relative to the argv-based flow. Please gate on `if (!codex.stdin)` before writing and attach an `error` listener that rejects the promise instead of letting the process die.

⚠️ HIGH — Timeout only sends `SIGTERM`, so hung children may linger (`~/mcp-servers/mcp-servers/codex-review/src/index.ts:172-175`)
- The timeout now rejects the promise but relies on a single `SIGTERM` to stop `codex`. If the child ignores or traps SIGTERM, it will keep running (consuming resources and holding stdout/stderr pipes) even though we already rejected the request. Consider scheduling a secondary kill (e.g., `setTimeout(() => codex.kill("SIGKILL"), KILL_GRACE_MS)`) so the process is guaranteed to terminate.

## Suggestions

💡 SUGGESTION — Make the timeout configurable
- A five-minute ceiling is a sensible default, but allowing overrides via request argument or environment variable would let us tighten the value for short reviews or relax it if Codex needs more time.

💡 SUGGESTION — Prefer `codex.stdin.end(prompt)` and set `stdin` error handlers
- Using `end(prompt)` handles buffering in one call, and attaching `codex.stdin.on("error", rejectWithContext)` keeps the server resilient to future stream errors.

## Responses to Review Questions

1. Timeout wiring is mostly correct, but the missing `stdin` guards introduce a new crash vector; please address that alongside a SIGKILL fallback so hung children cannot linger.
2. Keep 5 minutes as the default, but expose it for configuration (env var or tool argument) so sessions with tighter SLAs can shorten it.
3. Aside from the crash noted above, no race conditions—the promise resolves/rejects at most once as written.
4. Send SIGTERM first but add an automatic SIGKILL escalation (e.g., after 5 seconds) to guarantee teardown.
5. Main additional issue is the unhandled stdin error path; also consider the configurability and SIGKILL escalation noted above.
