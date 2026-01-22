#!/bin/bash
# =============================================================================
# MERIDIAN Model Serving Script for DGX Spark
# =============================================================================
# Starts vLLM servers for both fast (Qwen-14B) and reasoning (DeepSeek-70B) models
#
# Prerequisites:
#   - vLLM installed: pip install vllm
#   - Models downloaded to /mnt/spark-data3/models/
#   - CUDA available
#
# Usage:
#   ./start-models.sh [--fast-only] [--reasoning-only] [--stop]
# =============================================================================

set -euo pipefail

# Configuration
MODEL_PATH="/mnt/spark-data3/models"
LOG_PATH="/mnt/spark-data3/meridian/logs"

# Fast model (Qwen-14B)
FAST_MODEL="Qwen/Qwen2.5-14B-Instruct"
FAST_PORT=30001
FAST_GPU=0

# Reasoning model (DeepSeek-70B with AWQ quantization)
REASONING_MODEL="deepseek-ai/DeepSeek-R1-Distill-Llama-70B"
REASONING_PORT=30002
REASONING_GPU=0  # Same GPU, will use remaining memory

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
FAST_ONLY=false
REASONING_ONLY=false
STOP=false
STATUS=false

for arg in "$@"; do
    case $arg in
        --fast-only) FAST_ONLY=true ;;
        --reasoning-only) REASONING_ONLY=true ;;
        --stop) STOP=true ;;
        --status) STATUS=true ;;
        --help|-h)
            echo "Usage: $0 [--fast-only] [--reasoning-only] [--stop] [--status]"
            echo ""
            echo "Options:"
            echo "  --fast-only       Start only the fast model (Qwen-14B)"
            echo "  --reasoning-only  Start only the reasoning model (DeepSeek-70B)"
            echo "  --stop            Stop all model servers"
            echo "  --status          Check status of model servers"
            exit 0
            ;;
    esac
done

# Create log directory
mkdir -p "${LOG_PATH}"

# =============================================================================
# Stop servers
# =============================================================================
stop_servers() {
    log_info "Stopping model servers..."
    
    # Kill by port
    for port in $FAST_PORT $REASONING_PORT; do
        pid=$(lsof -ti:$port 2>/dev/null || true)
        if [ -n "$pid" ]; then
            kill $pid 2>/dev/null || true
            log_info "Stopped server on port $port (PID: $pid)"
        fi
    done
    
    # Also kill any vllm processes
    pkill -f "vllm.entrypoints" 2>/dev/null || true
    
    log_success "Servers stopped"
}

# =============================================================================
# Check status
# =============================================================================
check_status() {
    echo "=== Model Server Status ==="
    echo ""
    
    for port in $FAST_PORT $REASONING_PORT; do
        name="Fast (Qwen-14B)"
        [ $port -eq $REASONING_PORT ] && name="Reasoning (DeepSeek-70B)"
        
        if curl -s "http://localhost:$port/v1/models" &>/dev/null; then
            models=$(curl -s "http://localhost:$port/v1/models" | python3 -c "import sys,json; d=json.load(sys.stdin); print(', '.join(m['id'] for m in d.get('data',[])))" 2>/dev/null || echo "unknown")
            echo -e "${GREEN}✓${NC} $name (port $port): ONLINE - Models: $models"
        else
            echo -e "${RED}✗${NC} $name (port $port): OFFLINE"
        fi
    done
    
    echo ""
    echo "=== GPU Memory ==="
    nvidia-smi --query-gpu=index,name,memory.used,memory.total --format=csv,noheader
}

# =============================================================================
# Start fast model (Qwen-14B)
# =============================================================================
start_fast_model() {
    log_info "Starting fast model (Qwen-14B) on port ${FAST_PORT}..."
    
    # Check if already running
    if curl -s "http://localhost:${FAST_PORT}/v1/models" &>/dev/null; then
        log_warn "Fast model already running on port ${FAST_PORT}"
        return 0
    fi
    
    CUDA_VISIBLE_DEVICES=${FAST_GPU} python -m vllm.entrypoints.openai.api_server \
        --model "${FAST_MODEL}" \
        --port ${FAST_PORT} \
        --tensor-parallel-size 1 \
        --max-model-len 32768 \
        --gpu-memory-utilization 0.45 \
        --trust-remote-code \
        --disable-log-requests \
        > "${LOG_PATH}/vllm-fast.log" 2>&1 &
    
    echo $! > "${LOG_PATH}/vllm-fast.pid"
    
    # Wait for server to start
    log_info "Waiting for fast model to load..."
    for i in {1..60}; do
        if curl -s "http://localhost:${FAST_PORT}/v1/models" &>/dev/null; then
            log_success "Fast model ready on port ${FAST_PORT}"
            return 0
        fi
        sleep 5
    done
    
    log_error "Fast model failed to start. Check ${LOG_PATH}/vllm-fast.log"
    return 1
}

# =============================================================================
# Start reasoning model (DeepSeek-70B)
# =============================================================================
start_reasoning_model() {
    log_info "Starting reasoning model (DeepSeek-70B) on port ${REASONING_PORT}..."
    
    # Check if already running
    if curl -s "http://localhost:${REASONING_PORT}/v1/models" &>/dev/null; then
        log_warn "Reasoning model already running on port ${REASONING_PORT}"
        return 0
    fi
    
    # Use AWQ quantization to fit 70B in remaining GPU memory
    CUDA_VISIBLE_DEVICES=${REASONING_GPU} python -m vllm.entrypoints.openai.api_server \
        --model "${REASONING_MODEL}" \
        --port ${REASONING_PORT} \
        --tensor-parallel-size 1 \
        --max-model-len 16384 \
        --gpu-memory-utilization 0.50 \
        --quantization awq \
        --trust-remote-code \
        --disable-log-requests \
        > "${LOG_PATH}/vllm-reasoning.log" 2>&1 &
    
    echo $! > "${LOG_PATH}/vllm-reasoning.pid"
    
    # Wait for server to start (longer for 70B)
    log_info "Waiting for reasoning model to load (this may take a few minutes)..."
    for i in {1..120}; do
        if curl -s "http://localhost:${REASONING_PORT}/v1/models" &>/dev/null; then
            log_success "Reasoning model ready on port ${REASONING_PORT}"
            return 0
        fi
        sleep 5
    done
    
    log_error "Reasoning model failed to start. Check ${LOG_PATH}/vllm-reasoning.log"
    return 1
}

# =============================================================================
# Main
# =============================================================================
main() {
    echo "=============================================="
    echo "  MERIDIAN Model Server Manager"
    echo "=============================================="
    echo ""
    
    if [ "$STATUS" = true ]; then
        check_status
        exit 0
    fi
    
    if [ "$STOP" = true ]; then
        stop_servers
        exit 0
    fi
    
    # Check prerequisites
    if ! command -v python &>/dev/null; then
        log_error "Python not found. Activate the venv first."
        exit 1
    fi
    
    if ! python -c "import vllm" &>/dev/null; then
        log_error "vLLM not installed. Run: pip install vllm"
        exit 1
    fi
    
    # Start models
    if [ "$REASONING_ONLY" = false ]; then
        start_fast_model
    fi
    
    if [ "$FAST_ONLY" = false ]; then
        start_reasoning_model
    fi
    
    echo ""
    check_status
    
    echo ""
    log_success "Model servers started!"
    echo ""
    echo "Test the router:"
    echo "  python -m meridian.llm.router"
    echo ""
    echo "Logs:"
    echo "  Fast model:      ${LOG_PATH}/vllm-fast.log"
    echo "  Reasoning model: ${LOG_PATH}/vllm-reasoning.log"
}

main
