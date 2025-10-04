# Task: Add Provenance Tracking to Data Generation

**Priority**: P1 (HIGH - Should fix before deployment)
**Created**: 2025-10-04
**Assigned To**: claude_code
**Status**: Pending
**From Review**: reviews/responses/20251004_dry_policy_and_migration_codex.md

---

## Problem

Generated SFT data lacks provenance metadata. Cannot audit or reproduce datasets without knowing:
- Which model generated it
- Which loader/pattern was used
- Script version (git SHA)
- Seeds used
- Tokenizer settings

**Codex finding** (HIGH #2):
> "JSONL records lack explicit provenance fields (model id, loader pattern/version, script SHA, seeds, tokenizer settings). Hard to audit or reproduce datasets; training and evaluation comparability weakens."

---

## Impact

- **Reproducibility**: Cannot regenerate exact dataset
- **Auditability**: Cannot verify contamination-free generation
- **Comparability**: Cannot determine if datasets are comparable
- **Publication**: Insufficient documentation for methods section

---

## Current State

**File**: `scripts/generate_stage1_sft_data.py` (line 281)

**Current JSONL format**:
```json
{
  "instruction": "...",
  "response": "...",
  "type": "qa"
}
```

**Missing**:
- model_name
- loader_version
- script_sha
- seed
- template_disabled flag
- tokenizer settings
- generation timestamp

---

## Solution

### 1. Add Per-Record Provenance Fields

**New JSONL format**:
```json
{
  "instruction": "...",
  "response": "...",
  "type": "qa",
  "provenance": {
    "model_name": "Qwen/Qwen2.5-32B",
    "loader_version": "abc123def",
    "script_sha": "xyz789abc",
    "seed": 42,
    "template_disabled": true,
    "add_special_tokens": false,
    "generated_with": "clean_model_loader",
    "timestamp": "2025-10-04T10:30:00Z",
    "generation_params": {
      "temperature": 0.7,
      "max_new_tokens": 150,
      "top_p": 0.9
    }
  }
}
```

### 2. Separate Placeholder vs Generated

**Problem**: Placeholders mixed with generated examples if model fails

**Solution**: Separate files
```
artifacts/sft_data_20251004_123456_generated.jsonl  # Real examples
artifacts/sft_data_20251004_123456_placeholder.jsonl  # Failed generations (if any)
```

**Add CLI flag**: `--allow-placeholders` (default False)

### 3. Add Dataset Manifest

**File**: `artifacts/sft_data_20251004_123456_manifest.json`

```json
{
  "dataset_id": "sft_data_20251004_123456",
  "script": "generate_stage1_sft_data.py",
  "script_sha": "xyz789abc",
  "loader_version": "abc123def",
  "model_name": "Qwen/Qwen2.5-32B",
  "generated_count": 5000,
  "placeholder_count": 0,
  "generation_date": "2025-10-04T10:30:00Z",
  "files": {
    "generated": "sft_data_20251004_123456_generated.jsonl",
    "placeholder": null
  },
  "checksums": {
    "generated_sha256": "abc...def"
  },
  "global_params": {
    "seed": 42,
    "template_disabled": true,
    "add_special_tokens": false,
    "temperature_range": [0.6, 0.8],
    "max_new_tokens": 150
  }
}
```

---

## Implementation

**File**: `scripts/generate_stage1_sft_data.py`

**Changes**:

### 1. Get Provenance from Loader

```python
# After loading model
model, tokenizer, provenance = self.loader.load()

# Get script SHA
import subprocess
script_sha = subprocess.check_output(['git', 'rev-parse', 'HEAD']).decode('ascii').strip()
```

### 2. Add Provenance to Each Example

```python
def generate_example(self, instruction, instruction_type):
    # Generate response
    response = self.loader.generate(...)

    # Build example with provenance
    example = {
        "instruction": instruction,
        "response": response,
        "type": instruction_type,
        "provenance": {
            "model_name": self.model_name,
            "loader_version": provenance['loader_version'],
            "script_sha": script_sha,
            "seed": self.seed,
            "template_disabled": True,
            "add_special_tokens": False,
            "generated_with": "clean_model_loader",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "generation_params": {
                "temperature": self.temperature,
                "max_new_tokens": self.max_new_tokens,
                "top_p": self.top_p
            }
        }
    }
    return example
```

### 3. Separate Output Files

```python
# Open two files
generated_file = f"artifacts/sft_data_{timestamp}_generated.jsonl"
placeholder_file = f"artifacts/sft_data_{timestamp}_placeholder.jsonl"

with open(generated_file, 'w') as f_gen, \
     open(placeholder_file, 'w') as f_place:

    for instruction in instructions:
        try:
            example = self.generate_example(instruction, ...)
            f_gen.write(json.dumps(example) + '\n')
        except Exception as e:
            if self.allow_placeholders:
                placeholder = {"instruction": instruction, "error": str(e), ...}
                f_place.write(json.dumps(placeholder) + '\n')
            else:
                raise
```

### 4. Write Manifest

```python
def write_manifest(self, generated_count, placeholder_count, ...):
    manifest = {
        "dataset_id": f"sft_data_{timestamp}",
        "script": "generate_stage1_sft_data.py",
        "script_sha": script_sha,
        "loader_version": provenance['loader_version'],
        "model_name": self.model_name,
        "generated_count": generated_count,
        "placeholder_count": placeholder_count,
        "generation_date": datetime.utcnow().isoformat() + "Z",
        "files": {
            "generated": generated_file,
            "placeholder": placeholder_file if placeholder_count > 0 else None
        },
        "checksums": {
            "generated_sha256": self._compute_sha256(generated_file)
        },
        "global_params": {
            "seed": self.seed,
            "template_disabled": True,
            "add_special_tokens": False,
            "temperature_range": [self.min_temp, self.max_temp],
            "max_new_tokens": self.max_new_tokens
        }
    }

    manifest_file = f"artifacts/sft_data_{timestamp}_manifest.json"
    with open(manifest_file, 'w') as f:
        json.dump(manifest, f, indent=2)
```

---

## Completion Criteria

- [ ] Per-record provenance fields added
- [ ] Separate files for generated vs placeholder
- [ ] --allow-placeholders flag (default False)
- [ ] Dataset manifest created with checksums
- [ ] Git SHA captured and included
- [ ] Timestamp in ISO format with timezone
- [ ] All generation params logged
- [ ] Documentation updated

---

## Backward Compatibility

**Old format** (training scripts may expect):
```json
{"instruction": "...", "response": "...", "type": "qa"}
```

**New format**:
```json
{
  "instruction": "...",
  "response": "...",
  "type": "qa",
  "provenance": {...}
}
```

**Training scripts** can ignore "provenance" field (extra keys don't break JSONL loading).

**Migration**: No changes needed to training scripts (forward compatible).

---

## References

- reviews/responses/20251004_dry_policy_and_migration_codex.md - Codex review (HIGH #2, recommendations)
- scripts/generate_stage1_sft_data.py - Current implementation
