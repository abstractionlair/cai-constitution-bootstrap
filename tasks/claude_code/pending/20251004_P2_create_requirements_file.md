# Task: Create Requirements File for Automated Dependency Installation

**Priority**: P2 (Quality of Life)
**Created**: 2025-10-04
**Assigned To**: claude_code
**Estimated Time**: 30 minutes
**Triggered By**: Manual pip install during smoke test setup

---

## Problem

Currently installing dependencies manually with:
```bash
pip install torch transformers accelerate bitsandbytes peft scipy numpy
```

This is error-prone and doesn't capture exact versions for reproducibility.

---

## Requirements

### 1. Create requirements.txt

**File**: `requirements.txt` (root of repo)

**Should include**:
```
# Core ML frameworks
torch>=2.1.0
transformers>=4.35.0
accelerate>=0.24.0

# Quantization and efficient training
bitsandbytes>=0.41.0
peft>=0.6.0

# HuggingFace utilities
hf-transfer>=0.1.0  # Fast downloads from HF Hub

# Scientific computing
numpy>=1.24.0
scipy>=1.11.0

# Data handling
datasets>=2.14.0

# Utilities
tqdm>=4.66.0

# Optional: for statistical analysis
statsmodels>=0.14.0  # For verification of stats functions
```

**Notes**:
- Use `>=` for flexibility (not `==` which is too rigid)
- Include comments for clarity
- Group by purpose
- List in rough order of importance

---

### 2. Create requirements-dev.txt

**File**: `requirements-dev.txt`

**For development/testing**:
```
# Include base requirements
-r requirements.txt

# Testing
pytest>=7.4.0
pytest-cov>=4.1.0

# Code quality
black>=23.0.0
flake8>=6.1.0
isort>=5.12.0

# Documentation
sphinx>=7.2.0  # If we add docs later
```

---

### 3. Update Setup Documentation

**Files to update**:
- `docs/RUNPOD_H100_SESSION.md`
- `docs/DEPLOYMENT_CHECKLIST.md` (if exists)
- `docs/TECHNICAL_SETUP.md`

**Change**:
```bash
# OLD
pip install torch transformers accelerate bitsandbytes peft scipy numpy

# NEW
pip install -r requirements.txt
```

---

### 4. Add Installation Verification Script (Optional)

**File**: `scripts/verify_environment.py`

```python
#!/usr/bin/env python3
"""Verify all required dependencies are installed with correct versions."""

import sys

def check_imports():
    """Check all critical imports work."""
    try:
        import torch
        import transformers
        import bitsandbytes
        import peft
        import scipy
        import numpy
        print("✅ All imports successful")
        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False

def check_versions():
    """Check versions meet minimum requirements."""
    import torch
    import transformers

    print(f"PyTorch: {torch.__version__}")
    print(f"Transformers: {transformers.__version__}")

    # Check CUDA
    if torch.cuda.is_available():
        print(f"✅ CUDA available: {torch.version.cuda}")
        print(f"   GPU: {torch.cuda.get_device_name(0)}")
    else:
        print("⚠️  CUDA not available")

    return True

def main():
    print("Verifying environment...")
    print("-" * 40)

    if not check_imports():
        return 1

    print()
    check_versions()
    print("-" * 40)
    print("✅ Environment verification complete")
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

Usage:
```bash
python3 scripts/verify_environment.py
```

---

### 5. Add to .gitignore (if not present)

```
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
env/

# pip
pip-log.txt
pip-delete-this-directory.txt
```

---

## Implementation Steps

1. Create `requirements.txt` in repo root
2. Test locally: `pip install -r requirements.txt`
3. Create `requirements-dev.txt` (optional)
4. Create `scripts/verify_environment.py` (optional)
5. Update documentation (RUNPOD_H100_SESSION.md, etc.)
6. Update .gitignore if needed
7. Test on RunPod during next session
8. Commit with message about reproducible dependency management

---

## Success Criteria

- [ ] `requirements.txt` created with all dependencies
- [ ] Can install with: `pip install -r requirements.txt`
- [ ] Documentation updated to use requirements file
- [ ] Optional: `verify_environment.py` script created
- [ ] Optional: `requirements-dev.txt` for development
- [ ] Tested on clean environment

---

## Testing

### Local test:
```bash
# Create clean venv
python3 -m venv test_env
source test_env/bin/activate

# Install from requirements
pip install -r requirements.txt

# Verify
python3 scripts/verify_environment.py

# Cleanup
deactivate
rm -rf test_env
```

### RunPod test (next session):
```bash
cd /workspace/MaximalCAI
pip install -r requirements.txt
python3 scripts/verify_environment.py
```

---

## Benefits

- **Reproducibility**: Pin versions, ensure same environment
- **Convenience**: Single command vs many pip installs
- **Documentation**: Clear list of what's needed
- **Onboarding**: Easier for new contributors/sessions
- **CI/CD ready**: Can use in automated testing later

---

## Notes

- This is P2 (nice to have, not blocking)
- Can do after smoke test completes
- Makes future sessions faster to setup
- Helps with reproducibility (part of provenance)
- Consider adding to session manifest: installed package versions

---

## Related

- Provenance tracking includes environment versions
- Session manifest should log package versions
- Requirements file makes this easier to capture
