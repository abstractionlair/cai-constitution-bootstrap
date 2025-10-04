# Provenance Persistence Recommendations

**Created**: 2025-10-04
**Status**: Design recommendations (not yet implemented)
**Priority**: HIGH (from Codex review)
**Note**: This is a design/recommendations document. Consider moving to a design queue once we have organizational standards for such documents.

---

## Core Policy: Git Commit Hash as Source of Truth

**Key decision**: Always deploy code from git and include commit hash in all artifacts.

**Why this simplifies everything**:
- Commit hash lets us look up exact code, dependencies, and configuration
- Don't need to capture every parameter - just enough to identify the run
- Reproducibility comes from git history, not trying to serialize everything

**Minimum required metadata**:
```python
{
    'git_commit': get_git_sha(),        # Full SHA, not short
    'timestamp': datetime.now().isoformat(),
    'artifact_type': 'training_data' | 'evaluation' | 'model'
}
```

Everything else can be derived from the commit if needed.

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

**Recommended** (minimal):
```python
example = {
    **inst_data,
    'response': response,
    'formatted_text': formatted_text,
    'prompt': self.create_completion_prompt(...),
    'completion': f" {response}\nEND",
    'metadata': {
        'git_commit': get_git_sha(),            # REQUIRED: Full commit SHA
        'timestamp': datetime.now().isoformat(), # REQUIRED: When generated
        'loader_version': self.provenance['loader_version']  # Redundant but useful
    }
}
```

**Benefits**:
- Commit hash = source of truth (can look up all generation params in code)
- Timestamp = when it was generated
- Loader version = quick check without git checkout

**Optional additions** (if useful for filtering/searching):
- `seed`, `temperature`, `max_new_tokens` (but these should be in code at that commit)

### 2. Evaluation Reports (JSON outputs)

**Files**: All `evaluate_*.py` scripts

**Current**: Most don't save provenance

**Recommended** (minimal top-level metadata):
```python
evaluation_report = {
    'summary': {
        'base_accuracy': 0.85,
        'sft_accuracy': 0.92,
        # ... existing metrics
    },
    'metadata': {
        'git_commit': get_git_sha(),                     # REQUIRED: Full SHA
        'timestamp': datetime.now().isoformat(),         # REQUIRED: When run
        'loader_version': provenance['loader_version'],  # From loader.load()
        'dataset_name': 'held_out_test_set',            # What was evaluated
        'dataset_size': 12                               # N
    },
    'results': [
        # ... existing per-example results
    ]
}
```

**Benefits**:
- Commit hash = source of truth for eval script, decoding params, etc.
- Loader version = quick contamination check
- Dataset info = what was tested

**Note**: Don't need to serialize decoding params - they're in the script at that commit

### 3. Session-Level Manifest (Optional)

**Recommended**: Simple manifest logged at session start

**File**: `artifacts/session_manifest_{timestamp}.json`

**Content** (minimal):
```python
{
    'session_start': datetime.now().isoformat(),
    'git_commit': get_git_sha(),                    # Full SHA
    'git_branch': get_git_branch(),
    'environment': {
        'python': sys.version.split()[0],
        'torch': torch.__version__,
        'transformers': transformers.__version__,
        'cuda': torch.version.cuda if torch.cuda.is_available() else None
    },
    'artifacts': []  # Can append as generated, or just use for reference
}
```

**Benefits**:
- Quick environment check
- Session-level git commit for reference

**Note**: This is optional since every artifact has its own git_commit. Mainly useful for debugging environment issues.

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
from datetime import datetime
from pathlib import Path

def get_git_sha():
    """Get current git SHA (full, not short)"""
    return subprocess.check_output(['git', 'rev-parse', 'HEAD']).decode().strip()

def get_git_branch():
    """Get current git branch"""
    return subprocess.check_output(['git', 'rev-parse', '--abbrev-ref', 'HEAD']).decode().strip()

def create_artifact_metadata(provenance=None, **extra):
    """Create minimal standardized metadata for any artifact

    Args:
        provenance: Optional provenance dict from CleanModelLoader.load()
        **extra: Any additional metadata to include

    Returns:
        Dict with git_commit, timestamp, and optional loader_version
    """
    metadata = {
        'git_commit': get_git_sha(),
        'timestamp': datetime.now().isoformat()
    }

    if provenance:
        metadata['loader_version'] = provenance['loader_version']

    metadata.update(extra)
    return metadata
```

**Usage**:
```python
# In data generation
example['metadata'] = create_artifact_metadata(
    provenance=self.provenance,
    artifact_type='training_data'
)

# In evaluation
report['metadata'] = create_artifact_metadata(
    provenance=provenance,
    dataset_name='held_out_test',
    dataset_size=len(test_examples)
)
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

- ✅ Design complete (simplified based on "git commit as source of truth" policy)
- ⏳ Helper utility pending (`utils/provenance_helper.py`)
- ⏳ Data generation metadata pending
- ⏳ Evaluation report metadata pending

**Key simplification**:
- Always deploy from git → commit hash is sufficient provenance
- Everything else can be looked up from the commit
- Minimal metadata: `git_commit`, `timestamp`, `loader_version`

**Next steps**:
1. Create `utils/provenance_helper.py`
2. Update `generate_stage1_sft_data.py` to add metadata
3. Update evaluation scripts to add metadata
