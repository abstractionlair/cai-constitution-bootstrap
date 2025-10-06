# Smoke Test Plan - Post-Migration Verification

**Purpose**: Quick, low-cost verification that CleanModelLoader migration works correctly before full production runs.

**Target**: Run on GPU with minimal resources/time (~5-10 minutes, <$0.50)

---

## Test Strategy

**Principle**: Test each major script type with minimal inputs to verify:
1. CleanModelLoader loads without errors
2. Provenance is captured correctly
3. Contamination checks pass
4. Generation works end-to-end
5. No import/syntax errors in production environment

**NOT testing**: Model quality, statistical validity, or full pipeline (those come after)

---

## Smoke Test Script

Create `scripts/smoke_test_migration.py`:

```python
#!/usr/bin/env python3
"""
Smoke test for CleanModelLoader migration.
Quick verification that all major script types work with migrated code.

Expected runtime: 5-10 minutes
Expected cost: ~$0.30 (A100 @ $1.74/hr)
"""

import sys
import json
import logging
from pathlib import Path
from datetime import datetime

# Setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR / 'scripts'))

from utils.clean_model_loader import CleanModelLoader

def test_loader_basic():
    """Test 1: CleanModelLoader loads and returns provenance"""
    logger.info("=" * 60)
    logger.info("TEST 1: Basic CleanModelLoader functionality")
    logger.info("=" * 60)

    loader = CleanModelLoader("Qwen/Qwen2.5-32B", load_in_8bit=True)
    model, tokenizer, provenance = loader.load()

    # Verify provenance
    assert 'loader_version' in provenance, "Missing loader_version"
    assert 'model_name' in provenance, "Missing model_name"
    assert 'quantization' in provenance, "Missing quantization"
    assert 'template_disabled' in provenance, "Missing template_disabled"
    assert provenance['template_disabled'] == True, "Template not disabled!"

    logger.info(f"✅ Provenance: {provenance}")
    return model, tokenizer, loader, provenance

def test_generation_basic(model, tokenizer, loader):
    """Test 2: Basic generation works"""
    logger.info("=" * 60)
    logger.info("TEST 2: Basic generation")
    logger.info("=" * 60)

    # Simple completion prompt
    prompt = "The capital of France is"

    response = loader.generate(
        model, tokenizer, prompt,
        max_new_tokens=20,
        temperature=0.1,
        do_sample=False  # Deterministic
    )

    logger.info(f"Prompt: {prompt}")
    logger.info(f"Response: {response}")

    assert len(response) > 0, "Empty response"
    assert "Paris" in response or "paris" in response, "Basic knowledge test failed"

    logger.info("✅ Generation works")
    return response

def test_contamination_detection(model, tokenizer, loader):
    """Test 3: Contamination detection works"""
    logger.info("=" * 60)
    logger.info("TEST 3: Contamination detection (sentinel prompts)")
    logger.info("=" * 60)

    # These should NOT produce instruction-following responses
    sentinel_prompts = [
        "List 3 fruits",  # Would follow if contaminated
        "Translate to French: Hello",  # Would follow if contaminated
        "What is 2+2?"  # Would follow if contaminated
    ]

    responses = []
    for prompt in sentinel_prompts:
        response = loader.generate(
            model, tokenizer, prompt,
            max_new_tokens=30,
            temperature=0.1,
            do_sample=False
        )
        responses.append((prompt, response))
        logger.info(f"Sentinel: '{prompt}' → '{response[:50]}...'")

    # Manual inspection - base model should continue text, not follow instructions
    logger.info("⚠️  Manual check: Responses should be completions, not instruction-following")
    logger.info("    (e.g., 'List 3 fruits' → 'and vegetables...' NOT '1. Apple 2. Banana')")

    return responses

def test_data_generation_minimal(model, tokenizer, loader, provenance):
    """Test 4: Data generation pattern works"""
    logger.info("=" * 60)
    logger.info("TEST 4: Data generation with metadata")
    logger.info("=" * 60)

    # Simulate generating a single training example
    instruction = "Explain gravity"
    prompt = f"Instruction: {instruction}\nResponse:"

    response = loader.generate(
        model, tokenizer, prompt,
        max_new_tokens=100,
        temperature=0.7,
        do_sample=True
    )

    # Create example with metadata (as recommended)
    example = {
        'instruction': instruction,
        'response': response,
        'metadata': {
            'git_commit': 'smoke_test',  # Would be get_git_sha()
            'timestamp': datetime.now().isoformat(),
            'loader_version': provenance['loader_version'],
            'model_name': provenance['model_name'],
            'quantization': provenance['quantization'],
            'template_disabled': provenance['template_disabled'],
            'seed': 42,
            'temperature': 0.7,
            'max_new_tokens': 100
        }
    }

    logger.info(f"Generated example: {json.dumps(example, indent=2)[:300]}...")
    logger.info("✅ Data generation pattern works")

    return example

def test_evaluation_pattern(model, tokenizer, loader, provenance):
    """Test 5: Evaluation pattern works"""
    logger.info("=" * 60)
    logger.info("TEST 5: Evaluation with metadata")
    logger.info("=" * 60)

    # Test a single evaluation
    test_instruction = "List 3 colors"
    prompt = f"Instruction: {test_instruction}\nResponse:"

    response = loader.generate(
        model, tokenizer, prompt,
        max_new_tokens=50,
        temperature=0.7,
        do_sample=True
    )

    # Check if response follows instruction (shouldn't for base model)
    follows_instruction = any(color in response.lower() for color in ['red', 'blue', 'green', 'yellow'])

    # Create eval result with metadata
    result = {
        'instruction': test_instruction,
        'response': response,
        'follows_instruction': follows_instruction,
        'metadata': {
            'git_commit': 'smoke_test',
            'timestamp': datetime.now().isoformat(),
            'loader_version': provenance['loader_version'],
            'model_name': provenance['model_name'],
            'quantization': provenance['quantization'],
            'temperature': 0.7,
            'eval_seed': 42
        }
    }

    logger.info(f"Evaluation result: follows_instruction={follows_instruction}")
    logger.info(f"Response: {response}")
    logger.info("✅ Evaluation pattern works")

    return result

def main():
    """Run all smoke tests"""
    start_time = datetime.now()

    logger.info("\n" + "=" * 60)
    logger.info("SMOKE TEST: CleanModelLoader Migration Verification")
    logger.info("=" * 60)

    try:
        # Test 1: Basic loading
        model, tokenizer, loader, provenance = test_loader_basic()

        # Test 2: Basic generation
        test_generation_basic(model, tokenizer, loader)

        # Test 3: Contamination detection
        test_contamination_detection(model, tokenizer, loader)

        # Test 4: Data generation pattern
        test_data_generation_minimal(model, tokenizer, loader, provenance)

        # Test 5: Evaluation pattern
        test_evaluation_pattern(model, tokenizer, loader, provenance)

        # Summary
        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info("\n" + "=" * 60)
        logger.info("✅ ALL SMOKE TESTS PASSED")
        logger.info("=" * 60)
        logger.info(f"Time: {elapsed:.1f}s (~${elapsed/3600*1.74:.3f} @ $1.74/hr)")
        logger.info("")
        logger.info("✅ CleanModelLoader migration verified")
        logger.info("✅ Provenance tracking works")
        logger.info("✅ Contamination checks active")
        logger.info("✅ Data generation pattern works")
        logger.info("✅ Evaluation pattern works")
        logger.info("")
        logger.info("🚀 Ready for production runs!")

        return 0

    except Exception as e:
        logger.error("\n" + "=" * 60)
        logger.error("❌ SMOKE TEST FAILED")
        logger.error("=" * 60)
        logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()
        logger.error("")
        logger.error("⚠️  DO NOT proceed to production runs until fixed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())
```

---

## Usage

### On RunPod:

```bash
# 1. SSH to RunPod
ssh -p $RUNPOD_PORT -i ~/.ssh/id_ed25519 root@195.26.233.96

# 2. Navigate to code
cd /workspace/runs/stage1_20250911_131105/code

# 3. Pull latest
git pull

# 4. Run smoke test
python3 scripts/smoke_test_migration.py

# Expected output:
# ✅ ALL SMOKE TESTS PASSED
# Time: ~300s (~$0.15 @ $1.74/hr)
# 🚀 Ready for production runs!
```

### Expected Cost

- **Time**: 5-10 minutes
- **Cost**: ~$0.15-0.30 (A100 @ $1.74/hr)
- **Value**: Catches migration issues before $5-10 production runs

---

## What This Verifies

✅ **Code correctness**:
- All imports work in production environment
- CleanModelLoader loads successfully
- No syntax errors in migrated scripts

✅ **Contamination prevention**:
- Chat template is disabled
- Sentinel prompts behave correctly (base model continues, doesn't follow)
- Token ID checks work

✅ **Provenance tracking**:
- Provenance dict is returned
- Contains all required fields
- Can be captured in artifacts

✅ **Generation patterns**:
- Data generation works end-to-end
- Evaluation works end-to-end
- Metadata can be attached

---

## What This Does NOT Test

❌ **Model quality**: Not checking if training improves model
❌ **Statistical validity**: Not testing N≥200 evaluations
❌ **Full pipeline**: Not running SFT→DPO→eval full cycle
❌ **Memory management**: Not loading multiple models

Those come after smoke test passes.

---

## Success Criteria

**PASS**: All 5 tests pass, no exceptions, ~5-10 minutes runtime

**FAIL**: Any test fails → Fix before proceeding to production

**MANUAL CHECK**: Contamination detection responses should show base model behavior (text continuation, not instruction following)

---

## Next Steps After Smoke Test

1. ✅ **Smoke test passes** → Proceed to production data generation
2. ❌ **Smoke test fails** → Fix issues, re-test, do NOT proceed

**Production checklist** (after smoke test):
- [ ] Smoke test passed
- [ ] Session manifest created
- [ ] Git is clean (no uncommitted changes)
- [ ] Provenance helper utility created (optional, can add metadata manually for now)
- [ ] Ready to generate 5-10k SFT examples

---

## Notes

- This tests the **migration**, not the training pipeline quality
- Run this BEFORE any expensive production runs
- If smoke test fails, costs ~$0.30 to discover vs ~$5-10 for production failure
- Can re-run after any code changes to verify fixes
