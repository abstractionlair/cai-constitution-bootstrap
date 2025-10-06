#!/usr/bin/env python3
"""
Automated migration script to replace manual chat_template disabling
with CleanModelLoader usage.

Migrates remaining scripts to use centralized clean model loading.
"""

import re
import sys
from pathlib import Path

def migrate_script(script_path: Path) -> bool:
    """
    Migrate a single script to use CleanModelLoader.
    Returns True if migration successful, False otherwise.
    """
    print(f"Migrating: {script_path.name}")

    try:
        content = script_path.read_text()
        original_content = content

        # Skip if already using CleanModelLoader
        if 'clean_model_loader import CleanModelLoader' in content:
            print(f"  ✓ Already migrated")
            return True

        # Skip if doesn't have chat_template (not a base model script)
        if 'chat_template = None' not in content:
            print(f"  - No chat_template found, skipping")
            return True

        # Step 1: Add CleanModelLoader import after existing imports
        # Find last import statement
        import_pattern = r'((?:^import .*$|^from .* import .*$\n)+)'
        match = re.search(import_pattern, content, re.MULTILINE)

        if match:
            last_import_end = match.end()
            # Check if we need to add sys/Path imports
            needs_sys = 'import sys' not in content and 'from sys' not in content
            needs_path = 'from pathlib import Path' not in content and 'import pathlib' not in content

            addition = "\n"
            if needs_sys:
                addition += "import sys\n"
            if needs_path:
                addition += "from pathlib import Path\n"

            # Add CleanModelLoader import
            addition += "\n# Import clean model loader\nfrom utils.clean_model_loader import CleanModelLoader\n"

            content = content[:last_import_end] + addition + content[last_import_end:]

        # Step 2: Replace AutoTokenizer/AutoModelForCausalLM imports
        # Remove BitsAndBytesConfig if present (CleanModelLoader handles it)
        content = re.sub(r',\s*BitsAndBytesConfig', '', content)
        content = re.sub(r'BitsAndBytesConfig,\s*', '', content)
        content = re.sub(r'from transformers import BitsAndBytesConfig.*\n', '', content)

        # Remove AutoTokenizer and AutoModelForCausalLM imports if they're the only ones
        content = re.sub(
            r'from transformers import AutoTokenizer, AutoModelForCausalLM\n',
            '',
            content
        )
        content = re.sub(
            r'from transformers import AutoModelForCausalLM, AutoTokenizer\n',
            '',
            content
        )

        # Step 3: Replace manual model loading patterns
        # Pattern 1: Typical tokenizer + model loading
        pattern1 = r'tokenizer = AutoTokenizer\.from_pretrained\([^)]+\).*?tokenizer\.chat_template = None.*?model = AutoModelForCausalLM\.from_pretrained\([^)]+\)'

        if re.search(pattern1, content, re.DOTALL):
            replacement = '''loader = CleanModelLoader("Qwen/Qwen2.5-32B", load_in_8bit=True)
model, tokenizer = loader.load()'''
            content = re.sub(pattern1, replacement, content, flags=re.DOTALL)

        # Step 4: Replace manual generation patterns
        # This is more complex as generation code varies, so we'll do a targeted fix
        # Look for tokenizer(..., add_special_tokens=False, ...) followed by model.generate(...)

        # Write the migrated content
        if content != original_content:
            script_path.write_text(content)
            print(f"  ✓ Migrated successfully")
            return True
        else:
            print(f"  - No changes needed")
            return True

    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False

def main():
    """Migrate all remaining scripts"""

    # Scripts that need migration (from grep results)
    scripts_to_migrate = [
        "test_base_model_definitive.py",
        "evaluate_capability_differentiation_sequential.py",
        "evaluate_capability_differentiation.py",
        "evaluate_stage1_comprehensive.py",
        "evaluate_stage1_readiness.py",
        "evaluate_final.py",
        "evaluate_sft_model.py",
        "evaluate_stage1_corrected.py",
        "create_preference_pairs_improved.py",
        "train_stage1_dpo_improved.py",
        "train_stage1_sft.py",
    ]

    scripts_dir = Path(__file__).parent

    print("=" * 60)
    print("CleanModelLoader Migration Script")
    print("=" * 60)
    print()

    success_count = 0
    fail_count = 0

    for script_name in scripts_to_migrate:
        script_path = scripts_dir / script_name

        if not script_path.exists():
            print(f"Warning: {script_name} not found, skipping")
            continue

        if migrate_script(script_path):
            success_count += 1
        else:
            fail_count += 1
        print()

    print("=" * 60)
    print(f"Migration complete: {success_count} succeeded, {fail_count} failed")
    print("=" * 60)
    print()
    print("⚠️  IMPORTANT: Review migrated scripts manually!")
    print("This automated migration handles common patterns, but")
    print("complex generation code may need manual adjustment.")
    print()
    print("Next steps:")
    print("1. Review each migrated script")
    print("2. Test compilation: python3 -m py_compile scripts/*.py")
    print("3. Update IMPLEMENTATION_REGISTRY when complete")

    return 0 if fail_count == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
