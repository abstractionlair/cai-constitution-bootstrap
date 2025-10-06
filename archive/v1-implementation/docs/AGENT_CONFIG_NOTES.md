# Agent Configuration Notes

## Critical File Names for AI Assistants

### Codex CLI
- **MUST be named**: `AGENTS.md`
- **NOT**: `codex.md` or `CODEX.md`
- **Current setup**: Symlink from AGENTS.md → codex.md

### Gemini CLI
- **Reads**: `GEMINI.md` (uppercase works)

### Claude Code
- **Reads**: `CLAUDE.md` (uppercase works)

## If Things Break
If Codex stops reading instructions:
1. Check if AGENTS.md symlink exists
2. If not, recreate: `ln -s codex.md AGENTS.md`
3. Verify with: `ls -la AGENTS.md`

## Review Workflow Paths
All agents should check their review directories:
- Gemini: `/reviews/gemini/pending/`
- Codex: `/reviews/codex/pending/`

Response format:
- Write to: `/reviews/[agent]/responses/[same_filename]`
- Move completed to: `/reviews/[agent]/done/`
