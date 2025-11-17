#!/bin/bash
#
# Pre-Deployment Validation Script
# Comprehensive checks before deploying to production
#

set -e

echo "============================================"
echo "MindShift - Pre-Deployment Validation"
echo "============================================"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

ERRORS=0
WARNINGS=0

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_ROOT="$(dirname "$BACKEND_DIR")"

cd "$BACKEND_DIR"

# Helper functions
error() {
    echo -e "${RED}❌ ERROR: $1${NC}"
    ((ERRORS++))
}

warning() {
    echo -e "${YELLOW}⚠️  WARNING: $1${NC}"
    ((WARNINGS++))
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# 1. Check environment variables
echo "1. Checking environment variables..."
echo "-------------------------------------------"

required_vars=(
    "DATABASE_URL"
    "REDIS_URL"
    "JWT_SECRET"
    "ENCRYPTION_KEY"
    "OPENAI_API_KEY"
    "ANTHROPIC_API_KEY"
)

for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        if [ -f "../.env" ]; then
            # Try to load from .env
            export $(grep -v '^#' ../.env | xargs)
        fi

        if [ -z "${!var}" ]; then
            error "$var is not set"
        fi
    fi
done

if [ $ERRORS -eq 0 ]; then
    success "All required environment variables are set"
fi
echo ""

# 2. Check Python syntax and imports
echo "2. Validating Python code..."
echo "-------------------------------------------"
python scripts/validate.py
if [ $? -eq 0 ]; then
    success "Python validation passed"
else
    error "Python validation failed"
fi
echo ""

# 3. Check dependencies
echo "3. Checking Python dependencies..."
echo "-------------------------------------------"
pip check || {
    warning "Some dependencies have conflicts"
}
success "Dependencies check complete"
echo ""

# 4. Check database migrations
echo "4. Checking database migrations..."
echo "-------------------------------------------"
if [ -d "alembic/versions" ]; then
    migration_count=$(ls -1 alembic/versions/*.py 2>/dev/null | wc -l)
    if [ $migration_count -gt 0 ]; then
        success "Found $migration_count migration(s)"
    else
        warning "No migrations found"
    fi
else
    warning "Alembic versions directory not found"
fi
echo ""

# 5. Check Docker configuration
echo "5. Checking Docker configuration..."
echo "-------------------------------------------"
if [ -f "Dockerfile" ]; then
    success "Dockerfile found"

    # Validate Dockerfile syntax
    docker build --no-cache -f Dockerfile -t mindshift-backend-test . --dry-run 2>/dev/null || {
        # Fallback: just check file exists and has basic structure
        if grep -q "FROM python" Dockerfile && grep -q "CMD" Dockerfile; then
            success "Dockerfile appears valid"
        else
            error "Dockerfile may be invalid"
        fi
    }
else
    error "Dockerfile not found"
fi
echo ""

# 6. Check Kubernetes manifests
echo "6. Checking Kubernetes manifests..."
echo "-------------------------------------------"
K8S_DIR="$PROJECT_ROOT/k8s"
if [ -d "$K8S_DIR" ]; then
    yaml_files=$(find "$K8S_DIR" -name "*.yaml" -o -name "*.yml")
    if [ -n "$yaml_files" ]; then
        success "Found Kubernetes manifests"

        # Validate YAML syntax if kubectl is available
        if command -v kubectl &> /dev/null; then
            for file in $yaml_files; do
                kubectl apply --dry-run=client -f "$file" &>/dev/null || {
                    warning "Issue with $file"
                }
            done
        fi
    else
        warning "No Kubernetes manifests found"
    fi
else
    info "Kubernetes directory not found (OK for non-K8s deployments)"
fi
echo ""

# 7. Check critical files
echo "7. Checking critical files..."
echo "-------------------------------------------"

critical_files=(
    "main.py"
    "config.py"
    "database.py"
    "models.py"
    "auth.py"
    "requirements.txt"
)

for file in "${critical_files[@]}"; do
    if [ -f "$file" ]; then
        success "$file exists"
    else
        error "$file is missing"
    fi
done
echo ""

# 8. Check __init__.py files
echo "8. Checking module structure..."
echo "-------------------------------------------"

modules=(
    "ai_coach"
    "burnout_ml"
    "notifications"
    "integrations"
    "monitoring"
    "middleware"
    "admin"
    "gdpr"
    "websocket"
)

for module in "${modules[@]}"; do
    if [ -f "$module/__init__.py" ]; then
        success "$module/__init__.py exists"
    else
        warning "$module/__init__.py is missing"
    fi
done
echo ""

# 9. Security checks
echo "9. Running security checks..."
echo "-------------------------------------------"

# Check for hardcoded secrets
info "Scanning for potential hardcoded secrets..."
potential_secrets=$(grep -r -i -E "(password|secret|key|token).*=.*['\"][^'\"]{8,}" \
    --include="*.py" \
    --exclude-dir={venv,.venv,__pycache__,tests} . 2>/dev/null || true)

if [ -n "$potential_secrets" ]; then
    warning "Found potential hardcoded secrets (please verify)"
    echo "$potential_secrets" | head -5
else
    success "No obvious hardcoded secrets found"
fi
echo ""

# 10. Check test coverage
echo "10. Checking tests..."
echo "-------------------------------------------"
if [ -d "tests" ]; then
    test_count=$(find tests -name "test_*.py" | wc -l)
    if [ $test_count -gt 0 ]; then
        success "Found $test_count test files"

        # Run tests if pytest is available
        if command -v pytest &> /dev/null; then
            info "Running tests..."
            pytest tests/ -v --tb=short 2>/dev/null || {
                error "Some tests failed"
            }
        fi
    else
        warning "No test files found"
    fi
else
    warning "Tests directory not found"
fi
echo ""

# 11. Check requirements.txt for issues
echo "11. Validating requirements.txt..."
echo "-------------------------------------------"

# Check for duplicate packages
duplicates=$(cat requirements.txt | grep -v '^#' | grep -v '^$' | \
    cut -d'=' -f1 | cut -d'>' -f1 | cut -d'<' -f1 | \
    sort | uniq -d)

if [ -n "$duplicates" ]; then
    error "Duplicate packages in requirements.txt: $duplicates"
else
    success "No duplicate packages found"
fi

# Check for problematic packages
if grep -q "asyncio==" requirements.txt; then
    error "asyncio should not be in requirements.txt (stdlib)"
fi

success "Requirements.txt validation complete"
echo ""

# Final Report
echo "============================================"
echo "PRE-DEPLOYMENT VALIDATION REPORT"
echo "============================================"
echo ""

if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}✅ ALL CHECKS PASSED - READY FOR DEPLOYMENT${NC}"
    exit 0
elif [ $ERRORS -eq 0 ]; then
    echo -e "${YELLOW}⚠️  WARNINGS: $WARNINGS${NC}"
    echo -e "${GREEN}✅ No critical errors - OK to deploy with caution${NC}"
    exit 0
else
    echo -e "${RED}❌ ERRORS: $ERRORS${NC}"
    echo -e "${YELLOW}⚠️  WARNINGS: $WARNINGS${NC}"
    echo -e "${RED}❌ DEPLOYMENT NOT RECOMMENDED - Fix errors first${NC}"
    exit 1
fi
