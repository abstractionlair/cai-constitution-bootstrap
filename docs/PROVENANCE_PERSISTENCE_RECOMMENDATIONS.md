# Provenance Persistence Recommendations

**Created**: 2025-10-04
**Status**: Design recommendations (not yet implemented)
**Priority**: HIGH (from Codex review)

---

## Overview

CleanModelLoader now returns provenance metadata:
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
        'provenance': self.provenance,
        'script_version': self._get_git_sha(),  # Script git SHA
        'generation_params': {
            'seed': self.seed,
            'temperature': 0.7,
            'max_new_tokens': 150
        },
        'timestamp': datetime.now().isoformat()
    }
}
```

**Benefits**:
- Per-record traceability
- Can identify which records came from which loader version
- Can regenerate with exact same configuration

### 2. Evaluation Reports (JSON outputs)

**Files**: All `evaluate_*.py` scripts

**Current**: Most don't save provenance

**Recommended** (top-level metadata):
```python
evaluation_report = {
    'summary': {
        'base_accuracy': 0.85,
        'sft_accuracy': 0.92,
        # ... existing metrics
    },
    'metadata': {
        'provenance': provenance,           # From loader.load()
        'script_version': get_git_sha(),    # Script SHA
        'eval_seed': 42,
        'timestamp': datetime.now().isoformat(),
        'decoding_params': {
            'temperature': 0.7,
            'do_sample': True,
            'max_new_tokens': 150
        },
        'dataset': {
            'name': 'held_out_test_set',
            'size': 12,
            'version': test_set_sha  # If applicable
        }
    },
    'results': [
        # ... existing per-example results
    ]
}
```

**Benefits**:
- Can verify evaluation configuration
- Compare evaluations with same/different loaders
- Track methodology changes over time

### 3. Session-Level Manifest

**Recommended**: Create manifest at start of GPU session

**File**: `artifacts/session_manifest_{timestamp}.json`

**Content**:
```python
{
    'session_id': timestamp,
    'environment': {
        'python_version': sys.version,
        'torch_version': torch.__version__,
        'transformers_version': transformers.__version__,
        'gpu': torch.cuda.get_device_name(0),
        'git_sha': get_git_sha()
    },
    'loader_config': {
        'provenance': provenance,
        'model_name': "Qwen/Qwen2.5-32B",
        'quantization': "nf4"
    },
    'artifacts_generated': [
        {
            'file': 'sft_training_data_20251004.jsonl',
            'type': 'training_data',
            'count': 200,
            'timestamp': '...'
        },
        # ... other artifacts
    ]
}
```

**Benefits**:
- Single source of truth for session configuration
- Can reference from multiple artifacts
- Simplifies artifact tracking

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
def get_git_sha(short=False):
    """Get current git SHA"""
    import subprocess
    sha = subprocess.check_output(['git', 'rev-parse', 'HEAD']).decode().strip()
    return sha[:8] if short else sha

def create_artifact_metadata(provenance, script_path, **kwargs):
    """Create standardized metadata for any artifact"""
    return {
        'provenance': provenance,
        'script_version': get_git_sha(),
        'script_name': Path(script_path).name,
        'timestamp': datetime.now().isoformat(),
        **kwargs
    }

def create_session_manifest(provenance, session_dir):
    """Create session-level manifest"""
    # ... implementation
```

---

## Migration Impact

**Result Comparability**:
- Pre-migration results (before CleanModelLoader) not comparable
- Post-migration results with different loader versions need careful comparison
- Provenance tracking enables identifying comparable results

**Recommendation**: Create `docs/METHODOLOGY_CHANGE_NOTICE.md` documenting:
- Migration cutover date (2025-10-04)
- Pre/post migration differences
- Result comparability policy

---

## Verification

**After implementation**:
```bash
# Check data generation includes provenance
jq '.metadata.provenance' artifacts/sft_training_data_*.jsonl | head -1

# Check evaluation reports include provenance
jq '.metadata.provenance' artifacts/evaluation_*.json | head -1

# Check session manifest exists
ls artifacts/session_manifest_*.json
```

---

## References

- **Codex Review**: `reviews/responses/20251004_complete_migration_codex.md` (HIGH #3)
- **CleanModelLoader**: `scripts/utils/clean_model_loader.py:216-225`
- **Data Generation**: `scripts/generate_stage1_sft_data.py:339-365`
- **Evaluation**: All `scripts/evaluate_*.py` scripts

---

## Status

- ✅ Design complete
- ⏳ Implementation pending
- ⏳ Helper utility pending
- ⏳ Methodology change notice pending

**Next steps**: Implement session manifest generation, then migrate data generation and evaluation scripts.
