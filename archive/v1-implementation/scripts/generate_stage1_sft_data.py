#!/usr/bin/env python3
"""
DEPRECATED: This script has been superseded by generate_sample_data_v2.py

The old script used template-based instructions and lacked quality filtering.
The new v2 script uses:
- Model-generated instructions (instruction_generator)
- Logprob-based quality filtering (instruction_critic)
- CleanModelLoader for safe base model handling
- Full provenance tracking

Use instead:
    python3 scripts/generate_sample_data_v2.py --count <N>

See:
- scripts/generate_sample_data_v2.py (modern replacement)
- docs/IMPLEMENTATION_REGISTRY.md (implementation status)
- reviews/responses/20251006_methodology_audit_codex.md (why this change)

Deprecated: 2025-10-06
Reason: Missing model-generated instructions and quality filtering
"""

import sys
print("❌ ERROR: This script is deprecated.")
print("")
print("Use: python3 scripts/generate_sample_data_v2.py --count <N>")
print("")
print("Reason: Old script used templates instead of model-generated instructions")
print("        and lacked quality filtering via logprob critique.")
print("")
print("See docs/IMPLEMENTATION_REGISTRY.md for details.")
sys.exit(1)
