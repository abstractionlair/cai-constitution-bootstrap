# Task: Add Migration Gates to RunPod Session Plan

**Priority**: P1 (HIGH - Prevents accidental use of non-migrated scripts)
**Created**: 2025-10-04
**Assigned To**: claude_code
**Status**: Pending
**From Review**: reviews/responses/20251004_dry_policy_and_migration_codex.md

---

## Problem

RunPod session plan references migrated scripts but has no explicit precondition checking migration status before phases execute.

**Codex finding** (HIGH #3):
> "Phases reference migrated scripts, but there is no explicit precondition 'all base-model-touching scripts migrated OR equivalence validated.' Risk of accidentally running non-migrated scripts on GPU."

---

## Impact

- **Risk**: Accidentally running non-migrated scripts on GPU ($1.74/hour wasted)
- **Methodology**: Results from non-migrated scripts compromise uniformity
- **Safety**: No gate to prevent usage before migration complete

---

## Current State

**File**: `docs/RUNPOD_SESSION_PLAN.md` (line 50+)

**Phases reference scripts** but no gates:
- Phase 2: Baseline evaluation (uses evaluate_instruction_following.py)
- Phase 3: SFT data generation (uses generate_stage1_sft_data.py)
- Phase 5: Post-SFT evaluation

**No explicit check**: "Are all scripts in this phase migrated?"

---

## Solution

### 1. Add Pre-Session Gate

**At start of session** (before Phase 1):

```markdown
## Pre-Session Gate: Migration Status Check

**Before starting ANY phase that uses base model**:

```bash
# Verify all scripts are migrated
./scripts/verify_migration_complete.sh
```

**Required**: All scripts listed below MUST be migrated to CleanModelLoader:
- ✅ evaluate_instruction_following.py
- ✅ generate_stage1_sft_data.py
- ✅ evaluate_sft_model.py
- ✅ evaluate_final.py
- ✅ create_preference_pairs_improved.py

**If any script NOT migrated**:
- STOP - Do not proceed to GPU work
- Migrate remaining scripts first
- OR run A/B equivalence validation and version-stamp all outputs

**Verification command**:
```bash
# Should return 0 results (except clean_model_loader.py itself)
grep -rn "chat_template = None" scripts/*.py | grep -v clean_model_loader.py | grep -v archived/
```

**If verification fails**: Migration incomplete, BLOCK session start.
```

### 2. Add Phase-Level Gates

**For each phase that touches base model**:

#### Phase 2: Baseline Evaluation

```markdown
### Phase 2: Baseline Evaluation

**Gate**: Verify evaluate_instruction_following.py is migrated
```bash
grep -q "from utils.clean_model_loader import CleanModelLoader" scripts/evaluate_instruction_following.py && echo "✅ MIGRATED" || echo "❌ NOT MIGRATED - STOP"
```

**If NOT migrated**: STOP, do not run this phase.
```

#### Phase 3: SFT Data Generation

```markdown
### Phase 3: SFT Data Generation

**Gate**: Verify generate_stage1_sft_data.py is migrated
```bash
grep -q "from utils.clean_model_loader import CleanModelLoader" scripts/generate_stage1_sft_data.py && echo "✅ MIGRATED" || echo "❌ NOT MIGRATED - STOP"
```

**If NOT migrated**: STOP, do not run this phase.
```

### 3. Add Sentinel Contamination Check

**After model loads** (in each phase):

```markdown
**Sentinel Check**: Verify no contamination

```bash
# Run quick contamination test
python3 scripts/test_clean_base_model.py
```

**Expected**: Base model shows poor instruction following (~10-30% success)

**If contamination detected** (>70% success on base model):
- ❌ CRITICAL: Chat template may be active
- STOP session immediately
- Investigate contamination
- Fix before continuing
```

### 4. Add Early-Stop Condition

```markdown
## Early-Stop Conditions

**Stop session immediately if**:
1. Sentinel contamination check fails (base model >70% instruction following)
2. A/B discrepancy >2% (if using mixed patterns)
3. Migration verification fails mid-session
4. Memory errors (OOM) - switch to sequential scripts

**Recovery**:
- Save all artifacts
- Document what phase failed
- Create incident report
- Fix issue before resuming
```

### 5. Add Version Logger Step

**Phase 0: Environment Setup**

```markdown
### Phase 0: Environment Setup

**Step 1**: Log all versions for reproducibility

```bash
python3 scripts/log_session_versions.py
```

**Creates**: `artifacts/session_versions.json`

**Contents**:
```json
{
  "timestamp": "2025-10-04T12:00:00Z",
  "git_sha": "abc123def",
  "python_version": "3.10.12",
  "pip_freeze": [...],
  "pytorch": "2.1.0",
  "transformers": "4.36.0",
  "bitsandbytes": "0.41.0",
  "cuda_version": "12.1",
  "gpu_name": "NVIDIA A100-SXM4-80GB"
}
```
```

---

## Implementation

### File 1: Create Verification Script

**New file**: `scripts/verify_migration_complete.sh`

```bash
#!/bin/bash
# Verify CleanModelLoader migration is complete

set -e

echo "=== CleanModelLoader Migration Verification ==="
echo ""

# Check for manual chat_template patterns
echo "Checking for manual chat_template disabling..."
manual_count=$(grep -rn "chat_template = None" scripts/*.py | grep -v clean_model_loader.py | grep -v archived/ | wc -l)

if [ "$manual_count" -gt 0 ]; then
    echo "❌ FAILED: Found $manual_count instances of manual chat_template disabling"
    echo ""
    echo "Manual patterns found:"
    grep -rn "chat_template = None" scripts/*.py | grep -v clean_model_loader.py | grep -v archived/
    exit 1
fi

echo "✅ No manual chat_template patterns found"
echo ""

# Check for manual add_special_tokens=False
echo "Checking for manual tokenization..."
manual_tok=$(grep -rn "add_special_tokens=False" scripts/*.py | grep -v clean_model_loader.py | grep -v archived/ | wc -l)

if [ "$manual_tok" -gt 0 ]; then
    echo "❌ FAILED: Found $manual_tok instances of manual add_special_tokens=False"
    exit 1
fi

echo "✅ No manual tokenization patterns found"
echo ""

echo "=== Migration verification PASSED ==="
echo "All scripts use CleanModelLoader"
exit 0
```

### File 2: Create Version Logger

**New file**: `scripts/log_session_versions.py`

```python
#!/usr/bin/env python3
"""Log all environment versions for reproducibility"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

def get_git_sha():
    try:
        return subprocess.check_output(['git', 'rev-parse', 'HEAD']).decode().strip()
    except:
        return "unknown"

def get_cuda_version():
    try:
        output = subprocess.check_output(['nvcc', '--version']).decode()
        # Parse CUDA version from output
        for line in output.split('\n'):
            if 'release' in line.lower():
                return line.split('release')[1].split(',')[0].strip()
    except:
        return "unknown"

def get_gpu_name():
    try:
        output = subprocess.check_output(['nvidia-smi', '--query-gpu=name', '--format=csv,noheader']).decode()
        return output.strip().split('\n')[0]
    except:
        return "unknown"

def main():
    import torch
    import transformers
    import bitsandbytes

    versions = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "git_sha": get_git_sha(),
        "python_version": sys.version.split()[0],
        "pytorch": torch.__version__,
        "transformers": transformers.__version__,
        "bitsandbytes": bitsandbytes.__version__,
        "cuda_version": get_cuda_version(),
        "gpu_name": get_gpu_name(),
        "pip_freeze": subprocess.check_output(['pip', 'freeze']).decode().split('\n')
    }

    output_file = Path("artifacts/session_versions.json")
    output_file.parent.mkdir(exist_ok=True)

    with open(output_file, 'w') as f:
        json.dump(versions, f, indent=2)

    print(f"✅ Versions logged to {output_file}")
    print(f"   Git SHA: {versions['git_sha']}")
    print(f"   PyTorch: {versions['pytorch']}")
    print(f"   Transformers: {versions['transformers']}")
    print(f"   GPU: {versions['gpu_name']}")

if __name__ == "__main__":
    main()
```

### File 3: Update RunPod Session Plan

**File**: `docs/RUNPOD_SESSION_PLAN.md`

**Add sections**:
1. Pre-Session Gate (before Phase 1)
2. Phase 0: Environment Setup (version logging)
3. Per-phase gates (Phase 2, 3, 5, 8)
4. Early-stop conditions section

---

## Completion Criteria

- [ ] scripts/verify_migration_complete.sh created
- [ ] scripts/log_session_versions.py created
- [ ] Pre-session gate added to RunPod plan
- [ ] Phase-level gates added to RunPod plan
- [ ] Sentinel contamination checks added
- [ ] Early-stop conditions documented
- [ ] Version logging added as Phase 0
- [ ] All scripts executable (chmod +x)

---

## References

- reviews/responses/20251004_dry_policy_and_migration_codex.md - Codex review (HIGH #3, recommendations)
- docs/RUNPOD_SESSION_PLAN.md - Session plan to update
