#!/bin/bash
#
# Quick Validation Check
# Fast pre-commit validation
#

set -e

echo "Running quick validation checks..."

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"

cd "$BACKEND_DIR"

# 1. Python syntax validation
echo "✓ Validating Python syntax..."
python scripts/validate.py || exit 1

# 2. Check for common issues
echo "✓ Checking for common issues..."

# Check for print statements (should use logging)
if grep -r "print(" --include="*.py" --exclude-dir={tests,venv,.venv} . | grep -v "# OK: print"; then
    echo "⚠️  Warning: Found print() statements. Consider using logging instead."
fi

# Check for TODO comments
todo_count=$(grep -r "TODO\|FIXME\|XXX" --include="*.py" --exclude-dir={venv,.venv} . | wc -l)
if [ $todo_count -gt 0 ]; then
    echo "ℹ️  Found $todo_count TODO/FIXME comments"
fi

echo "✅ Quick check complete!"
