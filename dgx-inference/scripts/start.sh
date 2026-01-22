#!/bin/bash
# =============================================================================
# DGX Inference Stack - Startup Script
# =============================================================================
# Starts the dual-model inference stack:
#   - SGLang server with DeepSeek-R1-Distill-Llama-70B
#   - Router service (Claude + SGLang)
#
# Usage:
#   ./scripts/start.sh [--pull] [--build] [--logs]
# =============================================================================

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="$PROJECT_DIR/docker-compose.yml"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Parse arguments
PULL=false
BUILD=false
SHOW_LOGS=false
DETACH=true

for arg in "$@"; do
    case $arg in
        --pull) PULL=true ;;
        --build) BUILD=true ;;
        --logs) SHOW_LOGS=true; DETACH=false ;;
        --foreground|-f) DETACH=false ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --pull        Pull latest Docker images before starting"
            echo "  --build       Rebuild the router service image"
            echo "  --logs        Show logs (don't detach)"
            echo "  --foreground  Run in foreground (same as --logs)"
            echo ""
            exit 0
            ;;
    esac
done

# =============================================================================
# Pre-flight Checks
# =============================================================================
log_info "Running pre-flight checks..."

# Check Docker
if ! command -v docker &> /dev/null; then
    log_error "Docker not found. Please install Docker."
    exit 1
fi

# Check Docker Compose (v2)
if ! docker compose version &> /dev/null; then
    log_error "Docker Compose v2 not found. Please upgrade Docker."
    exit 1
fi

# Check NVIDIA runtime
if ! docker info 2>/dev/null | grep -q "nvidia"; then
    log_warn "NVIDIA Container Runtime not detected. GPU access may not work."
fi

# Check for required environment variables
if [ -z "${ANTHROPIC_API_KEY:-}" ]; then
    if [ -f "$PROJECT_DIR/.env" ]; then
        log_info "Loading environment from .env file"
        export $(grep -v '^#' "$PROJECT_DIR/.env" | xargs)
    fi
    
    if [ -z "${ANTHROPIC_API_KEY:-}" ]; then
        log_error "ANTHROPIC_API_KEY not set. Export it or add to .env file."
        exit 1
    fi
fi

# Check GPU availability
if command -v nvidia-smi &> /dev/null; then
    GPU_COUNT=$(nvidia-smi -L | wc -l)
    GPU_MEM=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | head -1)
    log_info "Found $GPU_COUNT GPU(s) with ${GPU_MEM}MB VRAM"
else
    log_warn "nvidia-smi not found. Cannot verify GPU availability."
fi

log_success "Pre-flight checks passed"

# =============================================================================
# Pull Images
# =============================================================================
if [ "$PULL" = true ]; then
    log_info "Pulling latest Docker images..."
    docker compose -f "$COMPOSE_FILE" pull
fi

# =============================================================================
# Build Router
# =============================================================================
if [ "$BUILD" = true ]; then
    log_info "Building router service..."
    docker compose -f "$COMPOSE_FILE" build router
fi

# =============================================================================
# Start Services
# =============================================================================
log_info "Starting inference stack..."

cd "$PROJECT_DIR"

if [ "$DETACH" = true ]; then
    docker compose up -d
else
    docker compose up
    exit 0
fi

# =============================================================================
# Health Checks
# =============================================================================
log_info "Waiting for SGLang server to be ready (this may take several minutes for 70B model)..."

MAX_WAIT=600  # 10 minutes
INTERVAL=10
ELAPSED=0

while [ $ELAPSED -lt $MAX_WAIT ]; do
    if curl -s http://localhost:8000/health &>/dev/null; then
        log_success "SGLang server is ready!"
        break
    fi
    
    # Check if container is still running
    if ! docker compose ps sglang | grep -q "running"; then
        log_error "SGLang container stopped unexpectedly. Check logs:"
        docker compose logs sglang --tail 50
        exit 1
    fi
    
    echo -n "."
    sleep $INTERVAL
    ELAPSED=$((ELAPSED + INTERVAL))
done

if [ $ELAPSED -ge $MAX_WAIT ]; then
    log_error "SGLang server failed to start within ${MAX_WAIT}s"
    log_info "Checking logs..."
    docker compose logs sglang --tail 100
    exit 1
fi

# Check router
log_info "Checking router service..."
sleep 5  # Give router time to connect

if curl -s http://localhost:8080/health &>/dev/null; then
    log_success "Router service is ready!"
else
    log_warn "Router may still be starting..."
fi

# =============================================================================
# Print Status
# =============================================================================
echo ""
echo "=============================================="
echo "  DGX Inference Stack - Running"
echo "=============================================="
echo ""

# Get status
STATUS=$(curl -s http://localhost:8080/status 2>/dev/null || echo '{"error": "Router not ready"}')
echo "Backend Status:"
echo "$STATUS" | python3 -m json.tool 2>/dev/null || echo "$STATUS"

echo ""
echo "Endpoints:"
echo "  Router API:     http://localhost:8080/v1/chat/completions"
echo "  SGLang Direct:  http://localhost:8000/v1/chat/completions"
echo "  Health Check:   http://localhost:8080/health"
echo "  Models List:    http://localhost:8080/v1/models"
echo ""
echo "Quick Test:"
echo '  curl http://localhost:8080/v1/chat/completions \\'
echo '    -H "Content-Type: application/json" \\'
echo '    -d '"'"'{"messages":[{"role":"user","content":"Explain quantum computing"}]}'"'"
echo ""

# SSH tunnel command for remote access
LOCAL_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "localhost")
echo "For remote access (from another machine):"
echo "  ssh -L 8080:localhost:8080 -L 8000:localhost:8000 $USER@$LOCAL_IP"
echo ""

log_success "Startup complete!"
