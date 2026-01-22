#!/bin/bash
# =============================================================================
# MERIDIAN Full Stack Deployment to DGX Spark
# =============================================================================
# Comprehensive deployment script that:
#   1. Syncs codebase to DGX
#   2. Builds and starts Docker containers (API + Dashboard)
#   3. Optionally starts LLM models via vLLM
#   4. Runs health checks
#
# Usage:
#   ./deploy-full-stack.sh [--build] [--with-models] [--local]
# =============================================================================

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
DGX_HOST="${DGX_HOST:-dgx-spark}"
DGX_USER="${DGX_USER:-gibsonv32}"
DGX_PATH="${DGX_PATH:-/home/gibsonv32/dev/meridian}"
LOCAL_MODE=false
BUILD_IMAGES=false
WITH_MODELS=false

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_step() { echo -e "\n${CYAN}=== $1 ===${NC}\n"; }

# Parse arguments
for arg in "$@"; do
    case $arg in
        --local) LOCAL_MODE=true ;;
        --build) BUILD_IMAGES=true ;;
        --with-models) WITH_MODELS=true ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --local        Deploy locally (skip rsync to DGX)"
            echo "  --build        Force rebuild Docker images"
            echo "  --with-models  Also start LLM models via vLLM"
            echo ""
            exit 0
            ;;
    esac
done

# =============================================================================
# Pre-flight Checks
# =============================================================================
preflight_checks() {
    log_step "Pre-flight Checks"
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker not found. Please install Docker."
        exit 1
    fi
    log_info "✓ Docker available"
    
    # Check Docker Compose
    if ! docker compose version &> /dev/null; then
        log_error "Docker Compose v2 not found. Please upgrade Docker."
        exit 1
    fi
    log_info "✓ Docker Compose v2 available"
    
    # Check for .env file
    if [ ! -f "$PROJECT_DIR/.env" ] && [ ! -f "$SCRIPT_DIR/.env" ]; then
        log_warn "No .env file found. Creating from template..."
        if [ -f "$PROJECT_DIR/dgx-inference/env.template" ]; then
            cp "$PROJECT_DIR/dgx-inference/env.template" "$PROJECT_DIR/.env"
            log_warn "Please edit $PROJECT_DIR/.env with your API keys"
        fi
    fi
    
    # Load environment
    if [ -f "$PROJECT_DIR/.env" ]; then
        export $(grep -v '^#' "$PROJECT_DIR/.env" | xargs)
        log_info "✓ Environment loaded from .env"
    fi
    
    # Check required variables
    if [ -z "${ANTHROPIC_API_KEY:-}" ]; then
        log_error "ANTHROPIC_API_KEY not set. Add it to .env file."
        exit 1
    fi
    log_info "✓ ANTHROPIC_API_KEY configured"
    
    log_success "Pre-flight checks passed"
}

# =============================================================================
# Sync to DGX (if not local mode)
# =============================================================================
sync_to_dgx() {
    if [ "$LOCAL_MODE" = true ]; then
        log_info "Skipping sync (local mode)"
        return 0
    fi
    
    log_step "Syncing to DGX"
    
    # Test SSH connectivity
    log_info "Testing SSH connection to ${DGX_HOST}..."
    if ! ssh -o ConnectTimeout=5 "${DGX_USER}@${DGX_HOST}" "echo 'Connected'" &>/dev/null; then
        log_error "Cannot connect to ${DGX_HOST}. Check SSH config."
        exit 1
    fi
    log_success "SSH connection OK"
    
    # Create target directory
    ssh "${DGX_USER}@${DGX_HOST}" "mkdir -p ${DGX_PATH}"
    
    # Rsync with exclusions
    log_info "Syncing files..."
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
        --exclude='dashboard/dist/' \
        "${PROJECT_DIR}/" "${DGX_USER}@${DGX_HOST}:${DGX_PATH}/"
    
    log_success "Files synced to ${DGX_HOST}:${DGX_PATH}"
}

# =============================================================================
# Build Docker Images
# =============================================================================
build_images() {
    log_step "Building Docker Images"
    
    if [ "$LOCAL_MODE" = true ]; then
        cd "$PROJECT_DIR"
    else
        ssh "${DGX_USER}@${DGX_HOST}" "cd ${DGX_PATH} && bash" << 'REMOTE_BUILD'
set -e
cd "${DGX_PATH:-/home/gibsonv32/dev/meridian}"
REMOTE_BUILD
    fi
    
    BUILD_CMD="docker compose -f deploy/docker-compose.dgx.yml build"
    if [ "$BUILD_IMAGES" = true ]; then
        BUILD_CMD="$BUILD_CMD --no-cache"
    fi
    
    if [ "$LOCAL_MODE" = true ]; then
        log_info "Building locally..."
        cd "$PROJECT_DIR"
        eval "$BUILD_CMD"
    else
        log_info "Building on DGX..."
        ssh "${DGX_USER}@${DGX_HOST}" "cd ${DGX_PATH} && $BUILD_CMD"
    fi
    
    log_success "Docker images built"
}

# =============================================================================
# Start Services
# =============================================================================
start_services() {
    log_step "Starting Services"
    
    COMPOSE_CMD="docker compose -f deploy/docker-compose.dgx.yml up -d"
    
    if [ "$LOCAL_MODE" = true ]; then
        cd "$PROJECT_DIR"
        eval "$COMPOSE_CMD"
    else
        ssh "${DGX_USER}@${DGX_HOST}" "cd ${DGX_PATH} && $COMPOSE_CMD"
    fi
    
    log_success "Services started"
}

# =============================================================================
# Start LLM Models (optional)
# =============================================================================
start_models() {
    if [ "$WITH_MODELS" = false ]; then
        return 0
    fi
    
    log_step "Starting LLM Models"
    
    if [ "$LOCAL_MODE" = true ]; then
        log_warn "LLM models should only be started on DGX with GPU support"
        return 0
    fi
    
    ssh "${DGX_USER}@${DGX_HOST}" "cd ${DGX_PATH} && ./deploy/start-models.sh"
    
    log_success "LLM models started"
}

# =============================================================================
# Health Checks
# =============================================================================
health_checks() {
    log_step "Running Health Checks"
    
    TARGET_HOST="localhost"
    if [ "$LOCAL_MODE" = false ]; then
        # Set up temporary SSH tunnel for health checks
        log_info "Setting up SSH tunnel for health checks..."
        ssh -f -N -L 8000:localhost:8000 -L 3000:localhost:3000 "${DGX_USER}@${DGX_HOST}"
        TUNNEL_PID=$!
        sleep 2
    fi
    
    # Check API
    log_info "Checking API server..."
    for i in {1..30}; do
        if curl -s "http://${TARGET_HOST}:8000/health" &>/dev/null; then
            log_success "API server is healthy"
            break
        fi
        sleep 2
    done
    
    # Check Dashboard
    log_info "Checking Dashboard..."
    for i in {1..30}; do
        if curl -s "http://${TARGET_HOST}:3000/health" &>/dev/null; then
            log_success "Dashboard is healthy"
            break
        fi
        sleep 2
    done
    
    # Kill tunnel if we created one
    if [ "$LOCAL_MODE" = false ] && [ -n "${TUNNEL_PID:-}" ]; then
        kill $TUNNEL_PID 2>/dev/null || true
    fi
}

# =============================================================================
# Print Summary
# =============================================================================
print_summary() {
    echo ""
    echo "=============================================="
    echo "  MERIDIAN Full Stack - Deployment Complete"
    echo "=============================================="
    echo ""
    
    if [ "$LOCAL_MODE" = true ]; then
        echo "Services running locally:"
        echo "  API:        http://localhost:8000"
        echo "  Dashboard:  http://localhost:3000"
        echo "  API Docs:   http://localhost:8000/docs"
    else
        echo "Services running on ${DGX_HOST}:"
        echo "  API:        http://${DGX_HOST}:8000"
        echo "  Dashboard:  http://${DGX_HOST}:3000"
        echo ""
        echo "For local access, create SSH tunnel:"
        echo "  ssh -L 8000:localhost:8000 -L 3000:localhost:3000 ${DGX_USER}@${DGX_HOST}"
        echo ""
        echo "Then access:"
        echo "  Dashboard:  http://localhost:3000"
        echo "  API:        http://localhost:8000"
    fi
    
    echo ""
    echo "Commands:"
    echo "  View logs:  docker compose -f deploy/docker-compose.dgx.yml logs -f"
    echo "  Stop:       docker compose -f deploy/docker-compose.dgx.yml down"
    echo "  Restart:    docker compose -f deploy/docker-compose.dgx.yml restart"
    echo ""
    
    if [ "$WITH_MODELS" = true ]; then
        echo "LLM Models:"
        echo "  Fast (Qwen-14B):      http://localhost:30001"
        echo "  Reasoning (DeepSeek): http://localhost:30002"
        echo "  Status: ./deploy/start-models.sh --status"
        echo ""
    fi
    
    log_success "Deployment complete!"
}

# =============================================================================
# Main
# =============================================================================
main() {
    echo ""
    echo "╔══════════════════════════════════════════════════════════════════╗"
    echo "║           MERIDIAN Full Stack Deployment                        ║"
    echo "║                                                                  ║"
    echo "║   Mode: $([ "$LOCAL_MODE" = true ] && echo "Local" || echo "DGX Spark (${DGX_HOST})")                                          ║"
    echo "╚══════════════════════════════════════════════════════════════════╝"
    echo ""
    
    preflight_checks
    sync_to_dgx
    build_images
    start_services
    start_models
    health_checks
    print_summary
}

main
