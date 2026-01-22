#!/bin/bash
# =============================================================================
# SSH Tunnel Setup for DGX Inference Stack Remote Access
# =============================================================================
# Creates SSH tunnel to forward inference ports from DGX to local machine.
#
# Usage:
#   ./scripts/tunnel.sh [DGX_HOST] [DGX_USER]
#
# Examples:
#   ./scripts/tunnel.sh                     # Use defaults from env
#   ./scripts/tunnel.sh dgx-spark           # Specify host only
#   ./scripts/tunnel.sh dgx-spark gibsonv32 # Specify host and user
#   ./scripts/tunnel.sh --status            # Check if tunnel is running
#   ./scripts/tunnel.sh --stop              # Stop the tunnel
# =============================================================================

set -euo pipefail

# Configuration (can be overridden by env vars or arguments)
DGX_HOST="${DGX_HOST:-dgx-spark}"
DGX_USER="${DGX_USER:-gibsonv32}"

# Ports to forward
ROUTER_PORT=8080
SGLANG_PORT=8000

# PID file for tracking tunnel process
PID_FILE="/tmp/dgx-inference-tunnel.pid"

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
for arg in "$@"; do
    case $arg in
        --status)
            if [ -f "$PID_FILE" ]; then
                PID=$(cat "$PID_FILE")
                if ps -p "$PID" > /dev/null 2>&1; then
                    log_success "Tunnel is running (PID: $PID)"
                    echo "  Router: http://localhost:$ROUTER_PORT"
                    echo "  SGLang: http://localhost:$SGLANG_PORT"
                    exit 0
                else
                    log_warn "PID file exists but process not running"
                    rm -f "$PID_FILE"
                    exit 1
                fi
            else
                log_info "No tunnel running"
                exit 1
            fi
            ;;
        --stop)
            if [ -f "$PID_FILE" ]; then
                PID=$(cat "$PID_FILE")
                if kill "$PID" 2>/dev/null; then
                    log_success "Tunnel stopped (PID: $PID)"
                else
                    log_warn "Could not kill process $PID"
                fi
                rm -f "$PID_FILE"
            else
                log_info "No tunnel to stop"
            fi
            exit 0
            ;;
        --help|-h)
            echo "Usage: $0 [DGX_HOST] [DGX_USER]"
            echo ""
            echo "Arguments:"
            echo "  DGX_HOST    DGX hostname or IP (default: dgx-spark or \$DGX_HOST)"
            echo "  DGX_USER    SSH username (default: gibsonv32 or \$DGX_USER)"
            echo ""
            echo "Options:"
            echo "  --status    Check if tunnel is running"
            echo "  --stop      Stop the tunnel"
            echo ""
            echo "Environment Variables:"
            echo "  DGX_HOST    Override default DGX host"
            echo "  DGX_USER    Override default SSH user"
            echo ""
            echo "Examples:"
            echo "  $0                           # Use defaults"
            echo "  $0 192.168.1.100             # Specify host"
            echo "  $0 dgx-spark myuser          # Specify host and user"
            echo "  DGX_HOST=dgx.local $0        # Use env var"
            echo ""
            exit 0
            ;;
        -*)
            log_error "Unknown option: $arg"
            exit 1
            ;;
        *)
            # Positional arguments
            if [ -z "${POSITIONAL_1:-}" ]; then
                POSITIONAL_1="$arg"
            elif [ -z "${POSITIONAL_2:-}" ]; then
                POSITIONAL_2="$arg"
            fi
            ;;
    esac
done

# Apply positional arguments
[ -n "${POSITIONAL_1:-}" ] && DGX_HOST="$POSITIONAL_1"
[ -n "${POSITIONAL_2:-}" ] && DGX_USER="$POSITIONAL_2"

# =============================================================================
# Check if tunnel already running
# =============================================================================
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        log_warn "Tunnel already running (PID: $PID)"
        log_info "Use --stop to stop the existing tunnel, or --status to check"
        exit 1
    else
        rm -f "$PID_FILE"
    fi
fi

# =============================================================================
# Check if ports are available locally
# =============================================================================
check_port() {
    local port=$1
    if lsof -i :"$port" > /dev/null 2>&1; then
        log_error "Port $port is already in use locally"
        return 1
    fi
    return 0
}

log_info "Checking local port availability..."
if ! check_port $ROUTER_PORT || ! check_port $SGLANG_PORT; then
    log_error "Cannot start tunnel - ports in use"
    exit 1
fi

# =============================================================================
# Test SSH Connection
# =============================================================================
log_info "Testing SSH connection to ${DGX_USER}@${DGX_HOST}..."

if ! ssh -o ConnectTimeout=10 -o BatchMode=yes "${DGX_USER}@${DGX_HOST}" "echo 'Connected'" 2>/dev/null; then
    log_error "Cannot connect to ${DGX_USER}@${DGX_HOST}"
    log_info "Make sure:"
    log_info "  1. DGX is accessible from this machine"
    log_info "  2. SSH keys are set up correctly"
    log_info "  3. Host/user are correct"
    exit 1
fi

log_success "SSH connection OK"

# =============================================================================
# Check if services are running on DGX
# =============================================================================
log_info "Checking if inference services are running on DGX..."

SGLANG_RUNNING=$(ssh "${DGX_USER}@${DGX_HOST}" "curl -s http://localhost:8000/health 2>/dev/null || echo 'offline'")
ROUTER_RUNNING=$(ssh "${DGX_USER}@${DGX_HOST}" "curl -s http://localhost:8080/health 2>/dev/null || echo 'offline'")

if [ "$SGLANG_RUNNING" = "offline" ]; then
    log_warn "SGLang server does not appear to be running on DGX"
fi

if [ "$ROUTER_RUNNING" = "offline" ]; then
    log_warn "Router service does not appear to be running on DGX"
fi

# =============================================================================
# Create SSH Tunnel
# =============================================================================
log_info "Creating SSH tunnel..."

# Start tunnel in background
ssh -N -f \
    -o ServerAliveInterval=30 \
    -o ServerAliveCountMax=3 \
    -o ExitOnForwardFailure=yes \
    -L ${ROUTER_PORT}:localhost:${ROUTER_PORT} \
    -L ${SGLANG_PORT}:localhost:${SGLANG_PORT} \
    "${DGX_USER}@${DGX_HOST}"

# Find the PID of the SSH tunnel
sleep 1
TUNNEL_PID=$(pgrep -f "ssh.*${DGX_HOST}.*${ROUTER_PORT}:localhost" | tail -1)

if [ -z "$TUNNEL_PID" ]; then
    log_error "Failed to start tunnel"
    exit 1
fi

echo "$TUNNEL_PID" > "$PID_FILE"

# =============================================================================
# Verify Tunnel
# =============================================================================
log_info "Verifying tunnel..."
sleep 2

TUNNEL_OK=true

if curl -s http://localhost:${ROUTER_PORT}/health &>/dev/null; then
    log_success "Router accessible at http://localhost:${ROUTER_PORT}"
else
    log_warn "Router not responding (may not be running on DGX)"
    TUNNEL_OK=false
fi

if curl -s http://localhost:${SGLANG_PORT}/health &>/dev/null; then
    log_success "SGLang accessible at http://localhost:${SGLANG_PORT}"
else
    log_warn "SGLang not responding (may not be running on DGX)"
    TUNNEL_OK=false
fi

# =============================================================================
# Print Summary
# =============================================================================
echo ""
echo "=============================================="
echo "  SSH Tunnel Active"
echo "=============================================="
echo ""
echo "  PID:     $TUNNEL_PID"
echo "  Target:  ${DGX_USER}@${DGX_HOST}"
echo ""
echo "  Local Endpoints:"
echo "    Router API: http://localhost:${ROUTER_PORT}/v1/chat/completions"
echo "    SGLang:     http://localhost:${SGLANG_PORT}/v1/chat/completions"
echo ""
echo "  Commands:"
echo "    Check status:  $0 --status"
echo "    Stop tunnel:   $0 --stop"
echo ""

if [ "$TUNNEL_OK" = true ]; then
    echo "Quick test:"
    echo '  curl http://localhost:8080/v1/chat/completions \\'
    echo '    -H "Content-Type: application/json" \\'
    echo '    -d '"'"'{"messages":[{"role":"user","content":"Hello!"}]}'"'"
    echo ""
    log_success "Tunnel ready!"
else
    log_warn "Tunnel created but services may not be running on DGX"
    log_info "Start services on DGX with: ./scripts/start.sh"
fi
