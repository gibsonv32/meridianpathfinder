#!/bin/bash
# =============================================================================
# MERIDIAN Deployment to DGX Spark (Secure Self-Hosted)
# =============================================================================
# Security: Services bind to localhost only, access via SSH tunnel
# 
# Usage:
#   ./deploy/deploy-to-spark.sh          # Full deploy
#   ./deploy/deploy-to-spark.sh --sync   # Sync code only
#   ./deploy/deploy-to-spark.sh --start  # Start services only
#   ./deploy/deploy-to-spark.sh --stop   # Stop services
#   ./deploy/deploy-to-spark.sh --status # Check status
#   ./deploy/deploy-to-spark.sh --health # Health check endpoints
#   ./deploy/deploy-to-spark.sh --logs   # Tail container logs
#   ./deploy/deploy-to-spark.sh --tunnel # Open SSH tunnel (foreground)
# =============================================================================

set -e

# Configuration
DGX_HOST="spark-ad77"
DGX_USER="gibsonv32"
DGX_PATH="/home/gibsonv32/dev/meridian"
LOCAL_PATH="$(dirname "$(dirname "$(realpath "$0")")")"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_cmd() { echo -e "${BLUE}[CMD]${NC} $1"; }

# =============================================================================
# Sync code to DGX (never syncs .env back)
# =============================================================================
sync_code() {
    log_info "Syncing code to ${DGX_HOST}:${DGX_PATH}..."
    
    rsync -avz --progress \
        --exclude='.git' \
        --exclude='__pycache__' \
        --exclude='*.pyc' \
        --exclude='.venv' \
        --exclude='venv' \
        --exclude='node_modules' \
        --exclude='.pytest_cache' \
        --exclude='*.egg-info' \
        --exclude='.meridian' \
        --exclude='dist' \
        --exclude='build' \
        --exclude='.env' \
        "${LOCAL_PATH}/" \
        "${DGX_USER}@${DGX_HOST}:${DGX_PATH}/"
    
    log_info "Code sync complete!"
    log_warn "Note: .env is never synced (stays local on DGX)"
}

# =============================================================================
# Start services on DGX
# =============================================================================
start_services() {
    log_info "Starting Meridian services on ${DGX_HOST}..."
    
    ssh "${DGX_USER}@${DGX_HOST}" << 'EOF'
        cd /home/gibsonv32/dev/meridian
        
        # Ensure .env has secure permissions
        if [ -f .env ]; then
            chmod 600 .env
            echo "✅ .env permissions set to 600"
        else
            echo "⚠️  .env not found - copy from .env.example and configure"
            exit 1
        fi
        
        # Check if SGLang is running
        if ! curl -s http://127.0.0.1:30000/v1/models > /dev/null 2>&1; then
            echo "⚠️  SGLang (gpt-oss-120b) is not running on port 30000"
            echo "   Start it with: docker start sglang-gpt-oss"
        else
            echo "✅ SGLang (gpt-oss-120b) is running"
        fi
        
        # Build and start Meridian containers
        cd deploy
        docker compose -f docker-compose.dgx.yml up -d --build
        
        echo ""
        echo "✅ Meridian services started (localhost-only binding)"
EOF
    
    echo ""
    log_info "Services started! Access via SSH tunnel:"
    echo ""
    log_cmd "ssh -L 3000:localhost:3000 -L 8000:localhost:8000 ${DGX_USER}@${DGX_HOST}"
    echo ""
    echo "Then open in browser:"
    echo "  Dashboard: http://localhost:3000"
    echo "  API Docs:  http://localhost:8000/docs"
    echo ""
    echo "Or use: ./deploy/deploy-to-spark.sh --tunnel"
}

# =============================================================================
# Stop services on DGX
# =============================================================================
stop_services() {
    log_info "Stopping Meridian services on ${DGX_HOST}..."
    
    ssh "${DGX_USER}@${DGX_HOST}" << 'EOF'
        cd /home/gibsonv32/dev/meridian/deploy
        docker compose -f docker-compose.dgx.yml down
        echo "✅ Meridian services stopped"
EOF
}

# =============================================================================
# Check status
# =============================================================================
check_status() {
    log_info "Checking Meridian status on ${DGX_HOST}..."
    
    ssh "${DGX_USER}@${DGX_HOST}" << 'EOF'
        echo "=== Docker Containers ==="
        docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "meridian|sglang" || echo "No Meridian containers running"
        
        echo ""
        echo "=== Port Bindings (security check) ==="
        docker ps --format "{{.Names}}: {{.Ports}}" | grep meridian || true
        echo "(Should show 127.0.0.1:port bindings, NOT 0.0.0.0)"
        
        echo ""
        echo "=== .env Permissions ==="
        if [ -f /home/gibsonv32/dev/meridian/.env ]; then
            ls -la /home/gibsonv32/dev/meridian/.env | awk '{print $1, $9}'
            echo "(Should be -rw------- for secure permissions)"
        else
            echo "⚠️  .env not found"
        fi
EOF
}

# =============================================================================
# Health check (detailed endpoint verification)
# =============================================================================
health_check() {
    log_info "Running health checks on ${DGX_HOST}..."
    
    ssh "${DGX_USER}@${DGX_HOST}" << 'EOF'
        echo "=== SGLang Model Server ==="
        if curl -sf http://127.0.0.1:30000/v1/models > /dev/null 2>&1; then
            echo "✅ SGLang is healthy"
            echo "   Models:"
            curl -s http://127.0.0.1:30000/v1/models | python3 -c "import sys,json; d=json.load(sys.stdin); print('   - ' + '\n   - '.join([m['id'] for m in d.get('data',[])]))" 2>/dev/null || echo "   (could not parse models)"
        else
            echo "❌ SGLang is NOT responding"
        fi
        
        echo ""
        echo "=== Meridian API ==="
        if curl -sf http://127.0.0.1:8000/health > /dev/null 2>&1; then
            echo "✅ API is healthy"
            curl -s http://127.0.0.1:8000/health | python3 -m json.tool 2>/dev/null || curl -s http://127.0.0.1:8000/health
        else
            echo "❌ API is NOT responding"
        fi
        
        echo ""
        echo "=== Meridian Dashboard ==="
        if curl -sf http://127.0.0.1:3000 > /dev/null 2>&1; then
            echo "✅ Dashboard is healthy"
        else
            echo "❌ Dashboard is NOT responding"
        fi
        
        echo ""
        echo "=== LLM Connectivity Test ==="
        # Quick test that API can reach SGLang
        RESPONSE=$(curl -sf http://127.0.0.1:8000/health 2>/dev/null || echo "{}")
        echo "API health response: $RESPONSE"
EOF
}

# =============================================================================
# Tail logs
# =============================================================================
tail_logs() {
    log_info "Tailing Meridian logs on ${DGX_HOST}... (Ctrl+C to stop)"
    
    ssh "${DGX_USER}@${DGX_HOST}" << 'EOF'
        cd /home/gibsonv32/dev/meridian/deploy
        docker compose -f docker-compose.dgx.yml logs -f --tail=100
EOF
}

# =============================================================================
# Open SSH tunnel (foreground)
# =============================================================================
open_tunnel() {
    log_info "Opening SSH tunnel to ${DGX_HOST}..."
    echo ""
    echo "Tunnel ports:"
    echo "  localhost:3000 -> Dashboard"
    echo "  localhost:8000 -> API"
    echo ""
    echo "Open in browser: http://localhost:3000"
    echo "Press Ctrl+C to close tunnel"
    echo ""
    
    ssh -N -L 3000:localhost:3000 -L 8000:localhost:8000 "${DGX_USER}@${DGX_HOST}"
}

# =============================================================================
# Main
# =============================================================================
case "${1:-full}" in
    --sync|-s)
        sync_code
        ;;
    --start)
        start_services
        ;;
    --stop)
        stop_services
        ;;
    --status)
        check_status
        ;;
    --health|-H)
        health_check
        ;;
    --logs|-l)
        tail_logs
        ;;
    --tunnel|-t)
        open_tunnel
        ;;
    --help|-h)
        echo "Usage: $0 [option]"
        echo ""
        echo "Deployment:"
        echo "  (default)     Full deploy (sync + start + status)"
        echo "  --sync, -s    Sync code to DGX only"
        echo "  --start       Start services on DGX"
        echo "  --stop        Stop services on DGX"
        echo ""
        echo "Monitoring:"
        echo "  --status      Check container status & security"
        echo "  --health, -H  Detailed health check of all endpoints"
        echo "  --logs, -l    Tail container logs (Ctrl+C to stop)"
        echo ""
        echo "Access:"
        echo "  --tunnel, -t  Open SSH tunnel for browser access"
        echo ""
        echo "Security: Services bind to localhost only."
        echo "Access via SSH tunnel: ssh -L 3000:localhost:3000 -L 8000:localhost:8000 ${DGX_USER}@${DGX_HOST}"
        ;;
    full|*)
        sync_code
        start_services
        check_status
        ;;
esac
