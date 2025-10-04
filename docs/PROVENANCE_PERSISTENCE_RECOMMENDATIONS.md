# Provenance Persistence Recommendations

**Created**: 2025-10-04
**Status**: Design recommendations (not yet implemented)
**Priority**: HIGH (from Codex review)
**Note**: This is a design/recommendations document. Consider moving to a design queue once we have organizational standards for such documents.

---

## Core Policy: Git Commit Hash as Safety Net

**Key decision**: Always deploy code from git and include commit hash in all artifacts.

**Git commit is a backup**, not a replacement for capturing useful metadata:
- Commit hash ensures we CAN look up anything if needed
- But looking up details in git history is difficult and slow
- **Capture anything we're likely to want to query, filter, or understand**

**Balance**:
- Don't serialize everything (that's what git is for)
- DO capture what you'll want to see without digging through code
- Think: "What will I want to filter/search/compare by?"

**Required minimum**:
```python
{
    'git_commit': get_git_sha(),                  # Safety net - can look up anything
    'timestamp': datetime.now().isoformat(),      # When generated
    'artifact_type': 'training_data' | 'evaluation' | 'model'
}
```

**But also capture** anything likely to be useful (see examples below).

---

## CleanModelLoader Provenance

CleanModelLoader returns provenance metadata:
```python
provenance = {
    'loader_version': git_sha,           # Git SHA of loader code
    'template_disabled': True,           # Chat template disabled
    'model_name': "Qwen/Qwen2.5-32B",   # Base model
    'quantization': "nf4" or "fp16",    # Quantization type
    'sentinel_tests_passed': True,      # Contamination checks passed
    'add_special_tokens': False         # Token handling
}
```

**Current state**: Provenance is captured but not persisted to outputs.

**Impact**: Cannot trace which loader version/configuration generated each dataset record or evaluation result.

---

## Recommended Implementation

### 1. Data Generation (JSONL records)

**File**: `scripts/generate_stage1_sft_data.py`

**Current** (line 357-363):
```python
example = {
    **inst_data,
    'response': response,
    'formatted_text': formatted_text,
    'prompt': self.create_completion_prompt(...),
    'completion': f" {response}\nEND"
}
```

**Recommended**:
```python
example = {
    **inst_data,
    'response': response,
    'formatted_text': formatted_text,
    'prompt': self.create_completion_prompt(...),
    'completion': f" {response}\nEND",
    'metadata': {
        # Safety net
        'git_commit': get_git_sha(),                      # REQUIRED: Can look up anything
        'timestamp': datetime.now().isoformat(),          # REQUIRED: When generated

        # Model provenance (will want to filter/compare by these)
        'loader_version': self.provenance['loader_version'],
        'model_name': self.provenance['model_name'],      # "Qwen/Qwen2.5-32B"
        'quantization': self.provenance['quantization'],  # "nf4", "fp16", etc.
        'template_disabled': True,                        # Contamination check

        # Generation params (will want to know these without code lookup)
        'seed': self.seed,                                # Reproducibility
        'temperature': 0.7,                               # Sampling params
        'max_new_tokens': 150,
        'do_sample': True,

        # Context
        'script_name': Path(__file__).name,
        'artifact_type': 'training_data'
    }
}
```

**What to capture** (questions we'll want to answer without git):
- Which model version generated this?
- Was contamination prevention applied?
- What sampling parameters were used?
- Can I reproduce this with the same seed?
- Which script generated this?

**Git commit answers**: What was the code/environment/dependencies at generation time?

### 2. Evaluation Reports (JSON outputs)

**Files**: All `evaluate_*.py` scripts

**Current**: Most don't save provenance

**Recommended**:
```python
evaluation_report = {
    'summary': {
        'base_accuracy': 0.85,
        'sft_accuracy': 0.92,
        # ... existing metrics
    },
    'metadata': {
        # Safety net
        'git_commit': get_git_sha(),                     # REQUIRED: Can look up anything
        'timestamp': datetime.now().isoformat(),         # REQUIRED: When run

        # Model provenance (will want to compare evaluations)
        'loader_version': provenance['loader_version'],
        'model_name': provenance['model_name'],
        'quantization': provenance['quantization'],
        'template_disabled': True,

        # Models evaluated (key for comparisons)
        'models': {
            'base': 'Qwen/Qwen2.5-32B',
            'sft': str(SFT_CHECKPOINT),
            'dpo': str(DPO_CHECKPOINT) if evaluated else None
        },

        # Decoding params (will want to know without code lookup)
        'temperature': 0.7,
        'do_sample': True,
        'max_new_tokens': 150,
        'eval_seed': 42,

        # Dataset (critical for understanding results)
        'dataset': {
            'name': 'held_out_test_set',
            'size': 12,
            'source': 'data/test_instructions.json',
            'version_sha': dataset_git_sha  # If dataset is versioned
        },

        # Context
        'script_name': Path(__file__).name,
        'artifact_type': 'evaluation'
    },
    'results': [
        # ... existing per-example results
    ]
}
```

**What to capture** (questions we'll want to answer without git):
- Which models were compared?
- What were the decoding parameters?
- What dataset was used and how large?
- Was contamination prevention applied?
- Can I compare this to other evaluations?

**Git commit answers**: What was the exact evaluation code/logic?

### 3. Session-Level Manifest

**Recommended**: Manifest logged at session start

**File**: `artifacts/session_manifest_{timestamp}.json`

**Content**:
```python
{
    # Session info
    'session_id': timestamp,
    'session_start': datetime.now().isoformat(),
    'git_commit': get_git_sha(),
    'git_branch': get_git_branch(),
    'git_dirty': check_if_uncommitted_changes(),  # Warn if not clean

    # Environment (useful for debugging)
    'environment': {
        'hostname': socket.gethostname(),
        'python': sys.version,
        'torch': torch.__version__,
        'transformers': transformers.__version__,
        'cuda': torch.version.cuda if torch.cuda.is_available() else None,
        'gpu': torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        'gpu_memory_gb': torch.cuda.get_device_properties(0).total_memory / 1e9 if torch.cuda.is_available() else None
    },

    # Expected work (for planning/tracking)
    'planned_artifacts': [
        'sft_training_data_*.jsonl (200 examples)',
        'sft_model checkpoint',
        'evaluation_comprehensive_*.json'
    ],

    # Can update as session progresses
    'artifacts_generated': []
}
```

**Benefits**:
- Environment snapshot for debugging
- Track what was planned vs completed
- Detect uncommitted changes (should warn!)

**Update as session progresses**:
```python
# When artifact created
manifest['artifacts_generated'].append({
    'file': artifact_path,
    'type': 'training_data',
    'timestamp': datetime.now().isoformat()
})
```

---

## Implementation Priority

### P0 (Before GPU deployment):
1. ✅ CleanModelLoader returns provenance (DONE)
2. ⏳ Session manifest generation
   - Create at session start
   - Update as artifacts generated
   - Reference from individual artifacts

### P1 (Before production data generation):
3. ⏳ Add provenance to SFT training data
   - `generate_stage1_sft_data.py` per-record metadata
   - Include script SHA, generation params

### P2 (Before production evaluations):
4. ⏳ Add provenance to evaluation reports
   - All `evaluate_*.py` scripts
   - Top-level metadata in JSON outputs

---

## Helper Utility

**Recommended**: Create `utils/provenance_helper.py`

```python
import subprocess
import socket
import sys
from datetime import datetime
from pathlib import Path

def get_git_sha():
    """Get current git SHA (full, not short)"""
    return subprocess.check_output(['git', 'rev-parse', 'HEAD']).decode().strip()

def get_git_branch():
    """Get current git branch"""
    return subprocess.check_output(['git', 'rev-parse', '--abbrev-ref', 'HEAD']).decode().strip()

def check_git_dirty():
    """Check if there are uncommitted changes"""
    result = subprocess.run(['git', 'status', '--porcelain'], capture_output=True)
    return len(result.stdout) > 0

def create_artifact_metadata(provenance, script_name, artifact_type, **extra):
    """Create standardized metadata for any artifact

    Args:
        provenance: Provenance dict from CleanModelLoader.load()
        script_name: Name of the script generating this artifact
        artifact_type: 'training_data', 'evaluation', 'model', etc.
        **extra: Any additional metadata to include (params, dataset info, etc.)

    Returns:
        Dict with comprehensive metadata
    """
    metadata = {
        # Safety net
        'git_commit': get_git_sha(),
        'timestamp': datetime.now().isoformat(),

        # Model provenance
        'loader_version': provenance['loader_version'],
        'model_name': provenance['model_name'],
        'quantization': provenance['quantization'],
        'template_disabled': provenance['template_disabled'],

        # Context
        'script_name': script_name,
        'artifact_type': artifact_type
    }

    # Add any extra fields
    metadata.update(extra)
    return metadata

def create_session_manifest(planned_artifacts=None):
    """Create session-level manifest

    Args:
        planned_artifacts: Optional list of artifacts planned for this session

    Returns:
        Dict with session metadata
    """
    import torch

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    manifest = {
        'session_id': timestamp,
        'session_start': datetime.now().isoformat(),
        'git_commit': get_git_sha(),
        'git_branch': get_git_branch(),
        'git_dirty': check_git_dirty(),
        'environment': {
            'hostname': socket.gethostname(),
            'python': sys.version,
            'torch': torch.__version__,
            'transformers': None,  # Fill in if needed
            'cuda': torch.version.cuda if torch.cuda.is_available() else None,
            'gpu': torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
            'gpu_memory_gb': torch.cuda.get_device_properties(0).total_memory / 1e9 if torch.cuda.is_available() else None
        },
        'planned_artifacts': planned_artifacts or [],
        'artifacts_generated': []
    }

    return manifest, timestamp
```

**Usage**:
```python
# In data generation
example['metadata'] = create_artifact_metadata(
    provenance=self.provenance,
    script_name=Path(__file__).name,
    artifact_type='training_data',
    seed=self.seed,
    temperature=0.7,
    max_new_tokens=150
)

# In evaluation
report['metadata'] = create_artifact_metadata(
    provenance=provenance,
    script_name=Path(__file__).name,
    artifact_type='evaluation',
    models={'base': 'Qwen/Qwen2.5-32B', 'sft': str(SFT_CHECKPOINT)},
    dataset={'name': 'held_out_test', 'size': len(test_examples)},
    temperature=0.7,
    eval_seed=42
)

# At session start
manifest, session_id = create_session_manifest(
    planned_artifacts=[
        'sft_training_data_*.jsonl (200 examples)',
        'sft_model checkpoint',
        'evaluation_*.json'
    ]
)
with open(f'artifacts/session_manifest_{session_id}.json', 'w') as f:
    json.dump(manifest, f, indent=2)
```

---

## Migration Impact

**Result Comparability**:
- Pre-migration results (Sept 2025) are not referenced in any docs
- No plan to use them for comparison
- All production results will be post-migration with provenance

**No action needed**: Old artifacts exist but aren't part of any analysis

---

## Verification

**After implementation**:
```bash
# Check data generation includes git_commit
jq '.metadata.git_commit' artifacts/sft_training_data_*.jsonl | head -1

# Check evaluation reports include git_commit
jq '.metadata.git_commit' artifacts/evaluation_*.json | head -1

# Verify commit is valid
git cat-file -t $(jq -r '.metadata.git_commit' artifacts/evaluation_*.json | head -1)
# Should output: commit
```

---

## References

- **Codex Review**: `reviews/responses/20251004_complete_migration_codex.md` (HIGH #3)
- **CleanModelLoader**: `scripts/utils/clean_model_loader.py:216-225`
- **Data Generation**: `scripts/generate_stage1_sft_data.py:339-365`
- **Evaluation**: All `scripts/evaluate_*.py` scripts

---

## Status

- ✅ Design complete (git commit as safety net, capture what we'll query/filter by)
- ⏳ Helper utility pending (`utils/provenance_helper.py`)
- ⏳ Data generation metadata pending
- ⏳ Evaluation report metadata pending

**Key principles**:
- Always deploy from git → commit hash as safety net
- Capture anything we'll want to query/filter/compare without digging through git
- Think: "What questions will I want to answer about this artifact?"

**Comprehensive metadata**:
- Git commit (safety net)
- Model provenance (loader version, quantization, contamination status)
- Generation/eval parameters (seed, temperature, etc.)
- Dataset info (name, size, source)
- Context (script name, artifact type)

**Next steps**:
1. Create `utils/provenance_helper.py`
2. Update `generate_stage1_sft_data.py` to add comprehensive metadata
3. Update evaluation scripts to add comprehensive metadata
4. Add session manifest creation to RunPod workflow
