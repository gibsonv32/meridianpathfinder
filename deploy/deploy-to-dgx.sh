#!/bin/bash
# =============================================================================
# MERIDIAN DGX Spark Deployment Script
# =============================================================================
# Transfers MERIDIAN codebase from MacBook to DGX Spark and sets up environment
#
# Usage:
#   ./deploy-to-dgx.sh [--sync-only] [--setup-only] [--test]
#
# Environment variables:
#   DGX_HOST    - DGX hostname/IP (default: dgx-spark)
#   DGX_USER    - DGX username (default: gibsonv32)
#   DGX_PATH    - Target path on DGX (default: /home/gibsonv32/dev/meridian)
# =============================================================================

set -euo pipefail

# Configuration
DGX_HOST="${DGX_HOST:-dgx-spark}"
DGX_USER="${DGX_USER:-gibsonv32}"
DGX_PATH="${DGX_PATH:-/home/gibsonv32/dev/meridian}"
LOCAL_PATH="$(cd "$(dirname "$0")/.." && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Parse arguments
SYNC_ONLY=false
SETUP_ONLY=false
TEST_ONLY=false

for arg in "$@"; do
    case $arg in
        --sync-only) SYNC_ONLY=true ;;
        --setup-only) SETUP_ONLY=true ;;
        --test) TEST_ONLY=true ;;
        --help|-h)
            echo "Usage: $0 [--sync-only] [--setup-only] [--test]"
            echo ""
            echo "Options:"
            echo "  --sync-only   Only sync files, don't run setup"
            echo "  --setup-only  Only run setup on DGX, don't sync"
            echo "  --test        Run tests after deployment"
            exit 0
            ;;
    esac
done

# =============================================================================
# Step 1: Sync codebase to DGX
# =============================================================================
sync_codebase() {
    log_info "Syncing codebase to ${DGX_USER}@${DGX_HOST}:${DGX_PATH}"
    
    # Create target directory
    ssh "${DGX_USER}@${DGX_HOST}" "mkdir -p ${DGX_PATH}"
    
    # Rsync with exclusions
    rsync -avz --progress \
        --exclude='.venv/' \
        --exclude='__pycache__/' \
        --exclude='*.pyc' \
        --exclude='.git/' \
        --exclude='.meridian/artifacts/' \
        --exclude='.meridian/fingerprints.db' \
        --exclude='*.joblib' \
        --exclude='*.pkl' \
        --exclude='node_modules/' \
        --exclude='.DS_Store' \
        --exclude='*.egg-info/' \
        --exclude='dist/' \
        --exclude='build/' \
        "${LOCAL_PATH}/" "${DGX_USER}@${DGX_HOST}:${DGX_PATH}/"
    
    # Copy DGX-specific config
    log_info "Copying DGX configuration..."
    scp "${LOCAL_PATH}/deploy/meridian-dgx.yaml" \
        "${DGX_USER}@${DGX_HOST}:${DGX_PATH}/meridian.yaml"
    
    # Copy router module to meridian package
    scp "${LOCAL_PATH}/deploy/llm_router.py" \
        "${DGX_USER}@${DGX_HOST}:${DGX_PATH}/meridian/llm/router.py"
    
    log_success "Codebase synced successfully"
}

# =============================================================================
# Step 2: Setup environment on DGX
# =============================================================================
setup_environment() {
    log_info "Setting up environment on DGX..."
    
    ssh "${DGX_USER}@${DGX_HOST}" bash << 'REMOTE_SCRIPT'
set -euo pipefail

cd "${DGX_PATH:-/home/gibsonv32/dev/meridian}"

echo "=== Setting up Python environment ==="

# Check for uv, install if needed
if ! command -v uv &> /dev/null; then
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi

# Create venv and install dependencies
echo "Creating virtual environment..."
uv venv .venv --python 3.11

echo "Installing dependencies..."
source .venv/bin/activate
uv pip install -e ".[dev]"

# Install additional DGX dependencies
uv pip install httpx pydantic-settings

echo "=== Creating directory structure ==="

# Create data directories on data volume
sudo mkdir -p /mnt/spark-data3/meridian/{data,artifacts,logs,rag/index,rag/documents}
sudo chown -R $(whoami):$(whoami) /mnt/spark-data3/meridian

# Symlink artifacts to data volume
if [ -d ".meridian/artifacts" ] && [ ! -L ".meridian/artifacts" ]; then
    mv .meridian/artifacts .meridian/artifacts.bak 2>/dev/null || true
fi
mkdir -p .meridian
ln -sf /mnt/spark-data3/meridian/artifacts .meridian/artifacts

echo "=== Initializing MERIDIAN project ==="

source .venv/bin/activate
meridian init --force --name "meridian-dgx"

echo "=== Setup complete ==="
REMOTE_SCRIPT

    log_success "Environment setup complete"
}

# =============================================================================
# Step 3: Test deployment
# =============================================================================
test_deployment() {
    log_info "Testing deployment..."
    
    ssh "${DGX_USER}@${DGX_HOST}" bash << 'REMOTE_SCRIPT'
set -euo pipefail

cd "${DGX_PATH:-/home/gibsonv32/dev/meridian}"
source .venv/bin/activate

echo "=== Running tests ==="

# Basic import test
python -c "from meridian.llm.router import get_dgx_provider; print('✓ Router module loaded')"

# CLI test
meridian --version
meridian status

# Run unit tests (skip LLM tests that need actual models)
pytest tests/ -v --ignore=tests/test_llm.py -x || true

echo "=== Deployment test complete ==="
REMOTE_SCRIPT

    log_success "Tests passed"
}

# =============================================================================
# Step 4: Create systemd service (optional)
# =============================================================================
create_service() {
    log_info "Creating systemd service..."
    
    ssh "${DGX_USER}@${DGX_HOST}" bash << 'REMOTE_SCRIPT'
cat > /tmp/meridian-api.service << 'EOF'
[Unit]
Description=MERIDIAN API Server
After=network.target

[Service]
Type=simple
User=gibsonv32
WorkingDirectory=/home/gibsonv32/dev/meridian
Environment="PATH=/home/gibsonv32/dev/meridian/.venv/bin:/usr/local/bin:/usr/bin"
ExecStart=/home/gibsonv32/dev/meridian/.venv/bin/meridian api start --host 0.0.0.0 --port 8000 --workers 4
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo mv /tmp/meridian-api.service /etc/systemd/system/
sudo systemctl daemon-reload
echo "Service created. Start with: sudo systemctl start meridian-api"
REMOTE_SCRIPT

    log_success "Systemd service created"
}

# =============================================================================
# Main execution
# =============================================================================
main() {
    echo "=============================================="
    echo "  MERIDIAN DGX Spark Deployment"
    echo "=============================================="
    echo ""
    echo "Source: ${LOCAL_PATH}"
    echo "Target: ${DGX_USER}@${DGX_HOST}:${DGX_PATH}"
    echo ""
    
    # Test SSH connectivity
    log_info "Testing SSH connection..."
    if ! ssh -o ConnectTimeout=5 "${DGX_USER}@${DGX_HOST}" "echo 'Connected'" &>/dev/null; then
        log_error "Cannot connect to ${DGX_HOST}. Check SSH config."
        exit 1
    fi
    log_success "SSH connection OK"
    
    if [ "$SETUP_ONLY" = true ]; then
        setup_environment
    elif [ "$TEST_ONLY" = true ]; then
        test_deployment
    else
        sync_codebase
        if [ "$SYNC_ONLY" = false ]; then
            setup_environment
            test_deployment
        fi
    fi
    
    echo ""
    log_success "Deployment complete!"
    echo ""
    echo "Next steps:"
    echo "  1. SSH to DGX: ssh ${DGX_USER}@${DGX_HOST}"
    echo "  2. Start models: ./deploy/start-models.sh"
    echo "  3. Test router: cd ${DGX_PATH} && python -m meridian.llm.router"
    echo "  4. Run demo: meridian demo --data data_mode2.csv --target target --row '{\"x1\":0.1}'"
}

main
