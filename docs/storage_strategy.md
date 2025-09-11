# RunPod Storage Strategy

## Network Volume Setup (REQUIRED)
Create a 50GB network volume BEFORE starting any serious work.
This persists across pod terminations and is your safety net.

## Directory Layout

```
/workspace/                    # Network Volume (PERSISTENT)
├── MaximalCAI/               # Clone repo here
│   ├── scripts/              # Implementation code
│   ├── data/
│   │   ├── raw/             # Generated examples
│   │   ├── filtered/        # After safety filtering
│   │   └── final/           # DPO-ready pairs
│   ├── checkpoints/
│   │   ├── mvp_100/         # First milestone
│   │   ├── scale_5k/        # Second milestone
│   │   └── final_10k/       # Final model
│   └── results/
│       ├── metrics.json     # Evaluation scores
│       └── samples/         # Example outputs
├── models/                   # Downloaded base models
│   └── Qwen2.5-32B/         # Cache to avoid re-download
└── logs/                     # Session logs, costs

/tmp/                         # Container Disk (TEMPORARY)
├── cache/                   # Hugging Face cache (regenerable)
└── working/                 # Intermediate processing
```

## Critical Data Priority

### MUST SAVE (High Priority):
1. **Generated preference pairs** (`data/final/*.jsonl`)
2. **Trained checkpoints** (`checkpoints/*/`)
3. **Evaluation results** (`results/`)
4. **Custom code** (`scripts/`)
5. **Logs for publication** (`logs/`)

### NICE TO SAVE (Medium Priority):
1. **Raw generations** (`data/raw/`)
2. **Base model cache** (`models/`)
3. **Intermediate data** (`data/filtered/`)

### CAN REGENERATE (Low Priority):
1. **HuggingFace cache** (`/tmp/cache/`)
2. **Temporary files** (`/tmp/working/`)
3. **System packages** (reinstall via script)

## Backup Commands

### Before Stopping Pod (Quick Backup):
```bash
# Already on network volume - just verify
ls -la /workspace/MaximalCAI/data/final/
ls -la /workspace/MaximalCAI/checkpoints/
```

### Before Terminating Pod (Full Backup):
```bash
# Create tarball of critical data
cd /workspace
tar -czf cai_backup_$(date +%Y%m%d).tar.gz \
    MaximalCAI/data/final \
    MaximalCAI/checkpoints \
    MaximalCAI/results

# Also download locally if paranoid
scp -P [PORT] root@[HOST]:/workspace/cai_backup*.tar.gz ./
```

### Quick Restore on New Pod:
```bash
# Network volume auto-mounts, just verify
ls /workspace/MaximalCAI/
# Everything should be there!
```

## Cost Optimization

### Network Volume Costs:
- 50GB = $5/month
- Keep for entire project
- Share across multiple experiments
- Much cheaper than losing work!

### Container Disk:
- 100GB included with pod
- Use for temporary/regenerable files
- Don't store critical data here

## Development Workflow

### Session Start:
1. Create/Resume pod WITH network volume attached
2. Verify mount: `df -h /workspace`
3. Pull latest code: `cd /workspace/MaximalCAI && git pull`
4. Continue from last checkpoint

### During Development:
- Save progress frequently to `/workspace`
- Use `/tmp` for large temporary files
- Checkpoint every 30 minutes for long runs

### Session End:
1. Ensure all results are in `/workspace`
2. Commit code changes
3. Stop (not terminate) pod if continuing soon
4. Terminate pod if taking a break >1 day

## Emergency Recovery

If you accidentally terminate without saving:
- Network volume = safe
- Container disk = gone
- Check RunPod's support - sometimes they can recover recently terminated pods

## Setup Script Addition

Add to setup_environment.sh:
```bash
# Ensure we're on network volume
if [ ! -d "/workspace" ]; then
    echo "ERROR: Network volume not mounted!"
    echo "Please attach volume and restart"
    exit 1
fi

# Clone repo to network volume if needed
if [ ! -d "/workspace/MaximalCAI" ]; then
    cd /workspace
    git clone https://github.com/abstractionlair/cai-constitution-bootstrap MaximalCAI
fi

# Create necessary directories
cd /workspace/MaximalCAI
mkdir -p data/{raw,filtered,final}
mkdir -p checkpoints results logs
mkdir -p /tmp/{cache,working}

echo "✅ Storage structure ready"
echo "📁 Persistent data in: /workspace/MaximalCAI"
echo "📁 Temporary data in: /tmp"
```
