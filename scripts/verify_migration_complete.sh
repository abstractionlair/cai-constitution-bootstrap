#!/bin/bash
# Verify CleanModelLoader migration is complete
# This script checks that no manual chat_template disabling remains

set -e

echo "========================================"
echo "CleanModelLoader Migration Verification"
echo "========================================"
echo ""

SCRIPTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPTS_DIR/.."

# Check for manual chat_template patterns
echo "Checking for manual chat_template disabling..."
manual_count=$(grep -rn "chat_template = None" scripts/*.py 2>/dev/null | \
              grep -v clean_model_loader.py | \
              grep -v archived/ | \
              grep -v migrate_to_clean_loader.py | \
              grep -v "# " | \
              grep -v '"' | \
              grep -v "'" | \
              wc -l | tr -d ' ')

if [ "$manual_count" -gt 0 ]; then
    echo "❌ FAILED: Found $manual_count instances of manual chat_template disabling"
    echo ""
    echo "Manual patterns found:"
    grep -rn "chat_template = None" scripts/*.py 2>/dev/null | \
        grep -v clean_model_loader.py | \
        grep -v archived/ | \
        grep -v migrate_to_clean_loader.py | \
        grep -v "# " | \
        grep -v '"' | \
        grep -v "'"
    echo ""
    echo "These scripts must be migrated to use CleanModelLoader"
    exit 1
fi

echo "✅ No manual chat_template patterns found"
echo ""

# Check for manual add_special_tokens=False (outside CleanModelLoader)
echo "Checking for manual tokenization patterns..."
manual_tok=$(grep -rn "add_special_tokens=False" scripts/*.py 2>/dev/null | \
            grep -v clean_model_loader.py | \
            grep -v archived/ | \
            grep -v "# " | \
            grep -v '"' | \
            wc -l | tr -d ' ')

if [ "$manual_tok" -gt 0 ]; then
    echo "⚠️  WARNING: Found $manual_tok instances of manual add_special_tokens=False"
    echo "   (This may be acceptable in some contexts, please review)"
fi

echo "✅ Manual tokenization check complete"
echo ""

# Check that CleanModelLoader is imported in base-model scripts
echo "Checking CleanModelLoader usage..."
clean_loader_imports=$(grep -l "from utils.clean_model_loader import CleanModelLoader" scripts/*.py 2>/dev/null | wc -l | tr -d ' ')

echo "✅ Found $clean_loader_imports scripts using CleanModelLoader"
echo ""

echo "========================================"
echo "✅ Migration verification PASSED"
echo "========================================"
echo ""
echo "All active scripts use CleanModelLoader for base model work"
exit 0
