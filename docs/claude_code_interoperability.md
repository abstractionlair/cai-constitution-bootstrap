# Claude Code Local ↔ Pod Interoperability

## Problem Statement

We need Claude Code to work seamlessly between local Mac and RunPod GPU instances, enabling:
- Direct control on GPU pod for training/inference operations
- Session continuity across environments  
- Artifact sharing and synchronization
- Cost-effective development (local planning, pod execution)

## Architecture Overview

```
Local Mac                    RunPod Pod
---------                    ----------
Claude Code ←→ Session Sync ←→ Claude Code
     ↓              ↓              ↓
 Git Repo      File Transfer   Git Repo
     ↓              ↓              ↓
Artifacts ←←←← SCP/Transfer ←←← Artifacts
```

## Session Storage Structure

### Local Claude Storage
```
~/.claude/
├── projects/
│   └── -Users-scottmcguire-MaximalCAI/
│       ├── 16c4d4d4-8522-44d1-bdb2-1e7544e5f25c.jsonl  # Current session (2MB)
│       ├── 1a97a531-5319-4f95-8a4c-bb4feaea38b6.jsonl  # Previous sessions
│       └── ...
├── settings.json
└── todos/
```

### Pod Claude Storage (Persistent)
```
/workspace/
├── claude-sessions/           # Persistent across pod restarts
│   ├── projects/
│   │   ├── -Users-scottmcguire-MaximalCAI/         # Local project sessions
│   │   └── -workspace-runs-stage1_*-code/          # Pod project sessions
│   ├── settings/
│   └── todos/
└── runs/
    └── stage1_*/code/         # Current working directory
```

### Pod ~/.claude (Symlinks to Persistent)
```
/root/.claude/
├── projects -> /workspace/claude-sessions/projects
├── settings.json -> /workspace/claude-sessions/settings/
└── todos -> /workspace/claude-sessions/todos/
```

## SSH Connection Strategy

### Hybrid SSH Architecture

**Two SSH endpoints with different capabilities:**

1. **Stable Proxy** (`tupdqnn4ka2obr-6441138e@ssh.runpod.io`)
   - ✅ **Stable**: Never changes across pod restarts
   - ✅ **File transfers**: Works for piped data transfer
   - ❌ **Interactive**: PTY limitations, no interactive commands
   - **Use for**: Session sync, file transfers

2. **Direct SSH** (`root@195.26.233.96 -p 48550`)
   - ✅ **Interactive**: Full terminal, monitoring, Claude execution
   - ❌ **Unstable**: Port changes on pod restart
   - **Use for**: Monitoring, interactive Claude sessions, debugging

### Port Management

**Challenge**: Direct SSH port changes on pod restarts
**Solution**: Environment variable with fallback detection

```bash
# Set current port (update after pod restart)
export RUNPOD_PORT=48550

# Script auto-detects and prompts for updates
./sync_claude.sh will detect failed connections and prompt for new port
```

## File Transfer Methods

### No SCP Dependency

All file transfers use **SSH pipes** to avoid port dependency:

```bash
# Instead of: scp -P $PORT file host:/path
# Use: cat file | ssh host "cat > /path"

# Local → Pod
cat "$local_file" | ssh $STABLE_PROXY "cat > $remote_path"

# Pod → Local  
ssh $STABLE_PROXY "cat $remote_path" > "$local_file"
```

**Benefits:**
- Works through stable proxy (no port changes)
- No SCP/SFTP dependency
- Handles large files (session JSONLs can be 2MB+)

## Session Synchronization Protocol

### Bidirectional Sync

**Push (Local → Pod):**
```bash
./sync_claude.sh push
# Transfers all local sessions to pod persistent storage
# Creates project symlinks for easy access
```

**Pull (Pod → Local):**
```bash
./sync_claude.sh pull  
# Transfers pod sessions back to local storage
# Merges with existing local sessions
```

**Launch (Sync + Execute):**
```bash
./sync_claude.sh launch
# 1. Push current local sessions
# 2. SSH to pod and launch Claude
# 3. Auto-pull on exit
```

### Session Mapping Strategy

**Path Encoding** (Claude Code standard):
- Local: `/Users/scottmcguire/MaximalCAI/` → `-Users-scottmcguire-MaximalCAI`
- Pod: `/workspace/runs/stage1_*/code/` → `-workspace-runs-stage1_*-code`

**Session Continuity Options:**

1. **Shared Sessions** (Recommended)
   - Use local project sessions on pod
   - Same context, same history
   - Seamless transition

2. **Parallel Sessions**
   - Separate local vs pod sessions  
   - Different contexts for different environments
   - Manual merge when needed

3. **Hybrid Approach**
   - Sync before major operations
   - Work independently between syncs
   - Merge at transition points

## Workflow Examples

### Development Workflow

```bash
# Local: Planning and review
claude  # Work on local machine

# Sync to pod for GPU work
./sync_claude.sh push
./sync_claude.sh launch  # Launch Claude on pod

# Pod: Execute training/inference
# (Claude Code running directly on pod)

# Sync results back
./sync_claude.sh pull
```

### Long-Running Training

```bash
# Start training on pod
./sync_claude.sh launch
> Train model for 3 hours...
> Save artifacts to /workspace/

# Later: Check results locally
./sync_claude.sh pull
claude --continue  # Review artifacts locally
```

### Collaborative Development

```bash
# Share session state via git
git add .claude-session-export.json
git commit -m "Session state before training"

# Pod: Import session state
./sync_claude.sh import-from-git
```

## Implementation Details

### sync_claude.sh Script Features

**Commands:**
- `status` - Show local and pod session status
- `check` - Test SSH connections  
- `setup` - Install Claude Code on pod, create persistent storage
- `push` - Sync local sessions to pod
- `pull` - Sync pod sessions to local
- `launch` - Push + launch Claude on pod + pull on exit

**Robust Error Handling:**
- SSH connection failures
- Port changes (prompts for new port)
- Partial transfer recovery
- Session conflict resolution

### Claude Code Installation on Pod

```bash
# Automated installation
curl -fsSL https://console.anthropic.com/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"

# Persistent PATH setup
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
```

### Session Conflict Resolution

**Timestamp-based merge:**
- Local sessions: `filename.jsonl`
- Pod sessions: `filename.jsonl`
- Conflicts: Keep both as `filename.local.jsonl` and `filename.pod.jsonl`

**Manual resolution:**
```bash
./sync_claude.sh resolve
# Interactive menu to choose session versions
```

## Cost Optimization

### When to Use Each Environment

**Local Mac (Free):**
- Planning and architecture  
- Code review and analysis
- Documentation and specs
- Small script development

**RunPod GPU ($1.74/hour):**
- Model training (DPO, LoRA)
- Large-scale inference (32B model)
- GPU-intensive evaluation
- Real-time monitoring of training

### Session Sync Efficiency

**Minimize transfers:**
- Delta sync (only changed sessions)
- Compression for large sessions
- Batch operations

**Storage management:**
- Archive old sessions locally
- Keep only active sessions on pod
- Cleanup on pod shutdown

## Security Considerations

### SSH Key Management

**Single key pair:**
- `~/.ssh/id_ed25519` works for both endpoints
- No key rotation needed
- Secure key storage locally

**Connection validation:**
```bash
# Test both endpoints
ssh -o ConnectTimeout=5 $STABLE_PROXY 'echo stable'
ssh -o ConnectTimeout=5 $DIRECT_SSH -p $PORT 'echo direct'
```

### Session Data Protection

**Session contents:**
- Contains full conversation history
- May include sensitive code/data
- Encrypted in transit (SSH)
- Stored in user-only directories

**Cleanup protocol:**
```bash
# Before pod termination
./sync_claude.sh pull          # Save sessions locally
rm -rf /workspace/claude-sessions/*  # Clean pod storage
```

## Troubleshooting

### Common Issues

**Port changed after pod restart:**
```bash
# Check RunPod UI for new port
export RUNPOD_PORT=NEW_PORT
./sync_claude.sh status  # Should work again
```

**Stable proxy PTY errors:**
```bash
# Expected - use direct SSH for interactive work
ssh -T root@195.26.233.96 -p $RUNPOD_PORT -i ~/.ssh/id_ed25519
```

**Session corruption:**
```bash
# Backup and reset
cp ~/.claude/projects/... ~/.claude/projects.backup/
./sync_claude.sh pull --force  # Overwrite local with pod version
```

**Claude Code not found on pod:**
```bash
./sync_claude.sh setup  # Reinstall Claude Code
# Or manually:
curl -fsSL https://console.anthropic.com/install.sh | sh
```

### Monitoring and Debugging

**Check sync status:**
```bash
./sync_claude.sh status
# Shows: local sessions, pod status, sync state
```

**Monitor transfers:**
```bash
# Large session files (2MB+) may take time
# Watch for progress indicators in script output
```

**Validate session integrity:**
```bash
# Sessions are JSONL - should be valid JSON per line
head -1 ~/.claude/projects/*/session.jsonl | jq .
```

## Future Enhancements

### Automation Opportunities

**Auto-sync hooks:**
- Sync before `claude` launch
- Sync after pod operations
- Scheduled sync (cron/launchd)

**Smart conflict resolution:**
- Merge conversations by timestamp
- Detect divergent session branches
- Auto-resolve simple conflicts

**Session compression:**
- Archive old conversations
- Compress large sessions
- Delta-only transfers

### Advanced Features

**Multi-pod support:**
- Different pod types (training vs inference)
- Session routing by project type
- Pod-specific configurations

**Team collaboration:**
- Shared session repositories
- Session branching/merging
- Access control

**Integration with RunPod API:**
- Auto-detect pod restarts
- Update ports automatically
- Cost tracking and limits

## Documentation References

**Claude Code:**
- Session storage: `~/.claude/projects/[encoded-path]/`
- Path encoding: Replace `/` with `-`
- Continue sessions: `claude --continue`

**RunPod:**
- Stable SSH proxy: Always `tupdqnn4ka2obr-6441138e@ssh.runpod.io`
- Direct SSH: Changes on restart, check UI
- Persistent storage: `/workspace/` survives restarts

**Git Integration:**
- Code deployment: Git tags for reproducibility
- Artifact storage: Pod-local, transfer on demand
- Session export: JSON export for version control