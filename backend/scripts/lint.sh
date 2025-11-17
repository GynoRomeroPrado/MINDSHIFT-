#!/bin/bash
#
# Linting Script for MindShift Backend
# Runs code quality checks
#

set -e

echo "============================================"
echo "MindShift Backend - Code Quality Checks"
echo "============================================"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"

cd "$BACKEND_DIR"

# Check if we're in a virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
    echo -e "${YELLOW}⚠️  Warning: Not in a virtual environment${NC}"
    echo ""
fi

# 1. Validate Python syntax and imports
echo "1. Validating Python code..."
echo "-------------------------------------------"
python scripts/validate.py
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Validation passed${NC}"
else
    echo -e "${RED}❌ Validation failed${NC}"
    exit 1
fi
echo ""

# 2. Check for common security issues (if bandit is installed)
if command -v bandit &> /dev/null; then
    echo "2. Running security checks (Bandit)..."
    echo "-------------------------------------------"
    bandit -r . -ll -x ./tests,./venv,./.venv || {
        echo -e "${YELLOW}⚠️  Security issues found${NC}"
    }
    echo ""
else
    echo "2. Bandit not installed, skipping security checks"
    echo "   Install with: pip install bandit"
    echo ""
fi

# 3. Check code formatting (if black is installed)
if command -v black &> /dev/null; then
    echo "3. Checking code formatting (Black)..."
    echo "-------------------------------------------"
    black --check --exclude '/(\.git|\.venv|venv|__pycache__|alembic)/' . || {
        echo -e "${YELLOW}⚠️  Code formatting issues found${NC}"
        echo "   Run: black . --exclude '/(\.git|\.venv|venv|__pycache__|alembic)/'"
    }
    echo ""
else
    echo "3. Black not installed, skipping format check"
    echo "   Install with: pip install black"
    echo ""
fi

# 4. Check for code smells (if pylint is installed)
if command -v pylint &> /dev/null; then
    echo "4. Running code analysis (Pylint)..."
    echo "-------------------------------------------"
    pylint --disable=C,R --ignore=tests,alembic *.py **/*.py 2>/dev/null || {
        echo -e "${YELLOW}⚠️  Code quality issues found${NC}"
    }
    echo ""
else
    echo "4. Pylint not installed, skipping code analysis"
    echo "   Install with: pip install pylint"
    echo ""
fi

# 5. Check for unused imports (if autoflake is installed)
if command -v autoflake &> /dev/null; then
    echo "5. Checking for unused imports..."
    echo "-------------------------------------------"
    autoflake --check --recursive --remove-all-unused-imports \
        --exclude venv,.venv,__pycache__,alembic . || {
        echo -e "${YELLOW}⚠️  Unused imports found${NC}"
        echo "   Run: autoflake --in-place --recursive --remove-all-unused-imports ."
    }
    echo ""
else
    echo "5. Autoflake not installed, skipping unused imports check"
    echo "   Install with: pip install autoflake"
    echo ""
fi

# 6. Type checking (if mypy is installed)
if command -v mypy &> /dev/null; then
    echo "6. Running type checks (MyPy)..."
    echo "-------------------------------------------"
    mypy --ignore-missing-imports --exclude '(venv|\.venv|alembic)' . 2>/dev/null || {
        echo -e "${YELLOW}⚠️  Type hints issues found${NC}"
    }
    echo ""
else
    echo "6. MyPy not installed, skipping type checking"
    echo "   Install with: pip install mypy"
    echo ""
fi

echo "============================================"
echo -e "${GREEN}✅ Linting complete!${NC}"
echo "============================================"
