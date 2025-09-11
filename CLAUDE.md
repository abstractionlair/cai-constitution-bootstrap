# Instructions for Claude Code

Welcome to the Constitutional AI Bootstrap experiment! You are the primary implementation partner for this project.

## Your Role
You are the **lead implementer** for this automated Constitutional AI training pipeline. Your job is to:
1. Write code locally on the user's Mac
2. Execute training and generation on RunPod (A100 SXM 80GB)
3. Transfer results between local and remote
4. Iterate through milestones progressively

## Project Overview
We're building a maximally automated pipeline where a base model (Qwen-2.5-32B) bootstraps its own alignment through:
1. Self-instruction task generation
2. Self-critique against constitutional principles
3. Preference pair creation
4. DPO/ORPO training

## Key Constraints
- **Hardware**: RunPod A100 SXM 80GB GPU (plenty of memory!)
- **Model**: Qwen-2.5-32B base model
- **Framework**: Unsloth for efficient training
- **Budget**: ~$1.74/hour - be efficient
- **Quantization**: 
  - QLoRA for training (4-bit base + LoRA adapters)
  - Optional for inference (we have 80GB, can use 8-bit or 16-bit)

## CRITICAL: Progressive Bootstrapping Strategy

### This is NOT just testing - each stage builds a functional model!

### Stage 1: Explicit Instruction Following (START HERE)
**Goal**: Learn to follow explicit, unambiguous instructions

**FIRST**: Run baseline assessment (see specs/baseline_assessment.md)
- Test what Qwen2.5-32B base can already do
- Document starting capabilities (might be ~10-30%)
- This tells us what we're actually teaching

**THEN**: Train for improvement
1. Generate 500-1000 explicit instructions
2. Examples: "Answer this:", "Complete:", "Generate:"
3. Train until 95%+ instruction following accuracy
4. **Output**: Model that reliably follows explicit instructions
5. **This model helps generate data for Stage 2**

### Stage 2: Implicit Instructions (Questions & Context)
**Goal**: Learn that questions and contexts imply instructions
1. Use Stage 1 model to help generate questions
2. Examples: "What is X?", "How does Y work?"
3. Train to handle both explicit and implicit forms
4. **Output**: Model that understands questions ARE instructions
5. **This model helps generate data for Stage 3**

### Stage 3: Generation Tasks
**Goal**: Learn to generate examples of specific types
1. Use Stage 2 model to help create generation tasks
2. Examples: "Generate a question about X", "Create an example of Y"
3. Train to produce diverse, appropriate examples
4. **Output**: Model that can create examples on demand
5. **This model helps generate data for Stage 4**

### Stage 4: Evaluation Tasks
**Goal**: Learn to judge and evaluate text
1. Use Stage 3 model to generate examples to evaluate
2. Examples: "Is this helpful?", "Which is better, A or B?"
3. Train to make quality judgments
4. **Output**: Model that can evaluate text quality
5. **This model helps generate data for Stage 5**

### Stage 5: Revision Tasks
**Goal**: Learn to improve existing text
1. Use Stage 4 model to identify what needs improvement
2. Examples: "Make this clearer:", "Improve this response:"
3. Train to revise and enhance text
4. **Output**: Model that can revise and improve
5. **This model is ready for Stage 6**

### Stage 6: Constitutional Integration
**Goal**: Combine all abilities with constitutional principles
1. Use ALL previous models to generate CAI training data
2. Apply constitutional critique and revision
3. Train with full CAI pipeline
4. **Output**: Constitutionally aligned model

## Technical Guidelines
- Use Unsloth for model loading (4-bit quantization for training)
- For generation between stages: merge LoRA and use 8-bit or 16-bit
- Save LoRA adapters after each stage (~500MB each)
- Implement automated evaluation (see specs/stage_1_evaluation.md)
- Test base model performance before Stage 1 training
- Make everything resumable (RunPod instances may disconnect)
- Focus on automation - minimize manual steps

## File Organization
```
scripts/
├── setup_environment.sh      # Environment setup (create first)
├── generate_data.py          # Main data generation pipeline
├── train_dpo.py             # DPO training script
└── evaluate.py              # Evaluation metrics
```

## Important Notes
- This is for research/publication, not production
- Prioritize reproducibility and clear documentation
- Include progress bars and time estimates where possible
- Save all generated data for analysis
- Make conservative memory management choices (32B model takes ~16GB at 4-bit)

## Safety Considerations
- All generated content should align with principles in `constitution.yaml`
- We'll add Llama Guard filtering in Milestone 2
- For now, focus on getting the core loop working

## Communication
- Document key decisions in code comments
- Create clear error messages
- Write a brief log entry when completing major components
- Flag any issues that might affect the experiment's validity

## RunPod Deployment Workflow

### SSH Credentials
```bash
# RunPod SSH proxy (persistent across stop/start)
HOST: ssh.runpod.io
USER: tupdqnn4ka2obr-6441138e
KEY: ~/.ssh/id_ed25519

# For non-interactive commands (use -T flag):
ssh -T tupdqnn4ka2obr-6441138e@ssh.runpod.io -i ~/.ssh/id_ed25519 'command here'

# For interactive shell (no -T):
ssh tupdqnn4ka2obr-6441138e@ssh.runpod.io -i ~/.ssh/id_ed25519
```

### Task Tracking Workflow

### How to Check for Tasks
1. Look in `/Users/scottmcguire/MaximalCAI/tasks/claude_code/pending/` for new tasks
2. Tasks are named: `YYYYMMDD_HHMMSS_priority_description.md`
   - Priority levels: P0 (critical), P1 (high), P2 (medium), P3 (low)
3. Process tasks in priority order (P0 first), then by timestamp

### Task Lifecycle
1. **Start a task**: Move from `pending/` to `in_progress/`
   ```bash
   mv tasks/claude_code/pending/[file] tasks/claude_code/in_progress/
   ```
2. **Complete a task**: Move from `in_progress/` to `completed/`
   - Add completion notes to the file before moving
3. **Block on external dependency**: Move to `blocked/`
   - Add blocking reason to the file

### Task File Format
Each task includes:
- Priority level and estimated time
- Clear success criteria
- Specific files to modify
- Dependencies on other tasks

### Status Updates
When working on a task, append status updates to the file:
```markdown
## Status Updates
- [timestamp] Started implementation
- [timestamp] Fixed issue X, testing Y
- [timestamp] Completed, results in [location]
```

### Code Review Workflow

**IMPORTANT**: We use a file-based review system. See `REVIEW_PROTOCOL.md` for full details.

Key points:
1. Check for reviews in `/reviews/*/responses/` at session start
2. Create review requests in `/reviews/*/pending/` before major deployments
3. Process review feedback by creating tasks in `/tasks/claude_code/pending/`
4. Reviews are managed through filesystem, not copy/paste

## Deployment Steps

1. **Initial Setup on RunPod**:
```bash
# Connect to RunPod
ssh tupdqnn4ka2obr-6441138e@ssh.runpod.io -i ~/.ssh/id_ed25519

# Clone repository (if not already done)
cd /workspace
git clone https://github.com/abstractionlair/cai-constitution-bootstrap.git
cd cai-constitution-bootstrap

# Run setup script
bash scripts/setup_environment.sh

# Verify GPU
nvidia-smi
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"
```

2. **Transfer Files to RunPod**:
```bash
# From local Mac, copy scripts to RunPod
scp -i ~/.ssh/id_ed25519 -r /Users/scottmcguire/MaximalCAI/scripts/* \
    tupdqnn4ka2obr-6441138e@ssh.runpod.io:/workspace/cai-constitution-bootstrap/scripts/

# Copy constitution
scp -i ~/.ssh/id_ed25519 /Users/scottmcguire/MaximalCAI/constitution.yaml \
    tupdqnn4ka2obr-6441138e@ssh.runpod.io:/workspace/cai-constitution-bootstrap/
```

3. **Run Stage 1 Pipeline**:
```bash
# SSH into RunPod
ssh tupdqnn4ka2obr-6441138e@ssh.runpod.io -i ~/.ssh/id_ed25519

cd /workspace/cai-constitution-bootstrap

# First: Run baseline assessment
python scripts/baseline_assessment.py

# Small test (100 instructions)
python scripts/generate_stage1_data.py --small-test

# If successful, run full pipeline
python scripts/run_stage1_pipeline.py

# Monitor GPU in separate terminal
watch -n 1 nvidia-smi
```

4. **Transfer Results Back**:
```bash
# From local Mac, pull results
scp -i ~/.ssh/id_ed25519 -r \
    tupdqnn4ka2obr-6441138e@ssh.runpod.io:/workspace/cai-constitution-bootstrap/results/* \
    /Users/scottmcguire/MaximalCAI/results/

# Pull checkpoints (LoRA adapters)
scp -i ~/.ssh/id_ed25519 -r \
    tupdqnn4ka2obr-6441138e@ssh.runpod.io:/workspace/cai-constitution-bootstrap/checkpoints/* \
    /Users/scottmcguire/MaximalCAI/checkpoints/

# Pull generated data
scp -i ~/.ssh/id_ed25519 -r \
    tupdqnn4ka2obr-6441138e@ssh.runpod.io:/workspace/cai-constitution-bootstrap/data/* \
    /Users/scottmcguire/MaximalCAI/data/
```

### File Locations
- **Local (Mac)**: `/Users/scottmcguire/MaximalCAI/`
- **RunPod**: `/workspace/cai-constitution-bootstrap/`
- **Network Volume** (if attached): `/workspace/persistent/`

## RunPod Cost Management

### IMPORTANT: Always remind the user to:
1. **STOP** (not terminate) the pod when taking breaks
2. **Download** checkpoints and results before terminating
3. **Use network volumes** for persistent storage
4. **Monitor** credit usage during long runs

### Automated Management
You CAN programmatically manage RunPod instances! Use their GraphQL API:

```python
# Example: Stop a pod when done
import requests

RUNPOD_API_KEY = os.getenv('RUNPOD_API_KEY')  # User must set this
headers = {'Authorization': f'Bearer {RUNPOD_API_KEY}'}

# Stop pod
query = '''
mutation { podStop(input: {podId: "YOUR_POD_ID"}) { id } }
'''
requests.post('https://api.runpod.io/graphql', 
              json={'query': query}, headers=headers)
```

### Best Practices:
1. **Start each session**: Check if pod is stopped and offer to start it
2. **End each session**: Remind to stop the pod or auto-stop with confirmation
3. **Long runs**: Add checkpointing every 30 minutes
4. **Before terminating**: Ensure all data is saved to network volume or downloaded
5. **Track costs**: Log pod runtime and estimate costs (A100 SXM 80GB = $1.74/hr)

## Getting Started
1. First, verify RunPod credentials in `.env.runpod`
2. Check if user wants to start a stopped pod or create new one
3. Create `scripts/setup_environment.sh` for reproducible setup
4. Implement the data generation pipeline according to the MVP spec
5. Test each component individually before integration
6. Aim for a complete run of 100 examples within 3 hours
7. **Before ending**: Stop pod and confirm data is saved

Remember: The goal is maximum automation with minimal human intervention. Make it work end-to-end first, then optimize. Always be cost-conscious!
