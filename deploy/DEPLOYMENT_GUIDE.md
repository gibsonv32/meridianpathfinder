# MERIDIAN DGX Spark Deployment Guide

Complete guide for deploying the MERIDIAN ML Decision Engineering Framework to NVIDIA DGX Spark.

## Overview

This deployment includes:
- **MERIDIAN API Server** - FastAPI backend (port 8000)
- **Conversational Dashboard** - React frontend (port 3000)
- **LLM Model Stack** - Dual-model inference (ports 30001, 30002)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              DGX Spark                                       │
│                                                                              │
│  ┌───────────────┐   ┌────────────────┐   ┌─────────────────────────────┐   │
│  │   Dashboard   │   │   MERIDIAN     │   │     LLM Model Stack         │   │
│  │   (React)     │──▶│   API Server   │──▶│  ┌─────────┬───────────┐   │   │
│  │   Port 3000   │   │   Port 8000    │   │  │Qwen-14B │DeepSeek-70B│   │   │
│  └───────────────┘   └────────────────┘   │  │ :30001  │  :30002   │   │   │
│         │                    │            │  └─────────┴───────────┘   │   │
│         │                    │            └─────────────────────────────┘   │
│         │                    │                         │                    │
│         └────────────────────┴─────────────────────────┘                    │
│                              │                                               │
└──────────────────────────────┼───────────────────────────────────────────────┘
                               │
                               ▼ (Claude API fallback)
                       ┌───────────────┐
                       │   Anthropic   │
                       │   Claude API  │
                       └───────────────┘
```

## Prerequisites

### On DGX Spark
- Docker with NVIDIA Container Runtime
- Docker Compose v2
- ~96GB GPU memory (for 70B model with tensor parallelism)
- SSH access configured

### On Development Machine
- SSH key configured for DGX access
- Git (for syncing changes)
- Optional: Docker for local testing

## Quick Start

### 1. Configure Environment

```bash
# Copy environment template
cp deploy/env.template .env

# Edit with your settings
nano .env

# Required: Add your Anthropic API key
# ANTHROPIC_API_KEY=sk-ant-...
```

### 2. Deploy to DGX

```bash
# Make scripts executable
chmod +x deploy/*.sh

# Deploy full stack to DGX
./deploy/deploy-full-stack.sh

# Or with LLM models
./deploy/deploy-full-stack.sh --with-models
```

### 3. Access the Dashboard

```bash
# From your local machine, create SSH tunnel
ssh -L 3000:localhost:3000 -L 8000:localhost:8000 gibsonv32@dgx-spark

# Then open in browser
open http://localhost:3000
```

## Deployment Options

### Option A: Docker Compose (Recommended)

Deploys API + Dashboard as Docker containers:

```bash
# On DGX
cd /home/gibsonv32/dev/meridian

# Start services
docker compose -f deploy/docker-compose.dgx.yml up -d

# View logs
docker compose -f deploy/docker-compose.dgx.yml logs -f

# Stop services
docker compose -f deploy/docker-compose.dgx.yml down
```

### Option B: Systemd Service

For automatic startup on boot:

```bash
# Copy service file
sudo cp meridian.service /etc/systemd/system/meridian@gibsonv32.service

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable meridian@gibsonv32
sudo systemctl start meridian@gibsonv32

# Check status
systemctl status meridian@gibsonv32

# View logs
journalctl -u meridian@gibsonv32 -f
```

### Option C: Manual (Development)

Run services directly without Docker:

```bash
# Terminal 1: API Server
cd /home/gibsonv32/dev/meridian
source .venv/bin/activate
uvicorn meridian.api.server:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2: Dashboard
cd dashboard
npm install
VITE_API_URL=http://localhost:8000 npm run dev
```

## LLM Model Configuration

### Start LLM Models (vLLM)

```bash
# Start both models
./deploy/start-models.sh

# Or start individually
./deploy/start-models.sh --fast-only      # Qwen-14B only
./deploy/start-models.sh --reasoning-only  # DeepSeek-70B only

# Check status
./deploy/start-models.sh --status

# Stop models
./deploy/start-models.sh --stop
```

### Model Routing

MERIDIAN automatically routes requests based on mode complexity:

| Mode | Task | Model |
|------|------|-------|
| 0 | EDA | Qwen-14B (fast) |
| 0.5 | Opportunity Discovery | Qwen-14B (fast) |
| 1 | Decision Intelligence | Qwen-14B (fast) |
| 2 | Feasibility | DeepSeek-70B (reasoning) |
| 3 | Strategy | DeepSeek-70B (reasoning) |
| 4 | Business Case | DeepSeek-70B (reasoning) |
| 5 | Code Generation | DeepSeek-70B (reasoning) |
| 6 | Execution/Ops | DeepSeek-70B (reasoning) |
| 6.5 | Interpretation | DeepSeek-70B (reasoning) |
| 7 | Delivery | Qwen-14B (fast) |

### Fallback Configuration

If local models are unavailable, MERIDIAN falls back to Claude API:

```yaml
# In meridian.yaml
llm:
  provider: dgx
  fallback_provider: anthropic
  fallback_model: claude-3-haiku-20240307
```

## Remote Access

### SSH Tunnel (Recommended)

```bash
# Create tunnel script
cat > ~/bin/meridian-tunnel.sh << 'EOF'
#!/bin/bash
ssh -N \
  -L 3000:localhost:3000 \
  -L 8000:localhost:8000 \
  -L 30001:localhost:30001 \
  -L 30002:localhost:30002 \
  gibsonv32@dgx-spark
EOF
chmod +x ~/bin/meridian-tunnel.sh

# Start tunnel
~/bin/meridian-tunnel.sh
```

### Direct Access (if on same network)

```bash
# If DGX is directly accessible
open http://dgx-spark:3000
```

## Directory Structure on DGX

```
/home/gibsonv32/dev/meridian/     # Code (NVMe)
├── meridian/                      # Python package
├── dashboard/                     # React frontend
├── deploy/                        # Deployment scripts
├── tests/                         # Unit tests
├── .venv/                         # Python environment
├── meridian.yaml                  # Config file
└── .env                           # Environment variables

/mnt/spark-data3/meridian/        # Data (8TB volume)
├── data/                          # Input datasets
├── artifacts/                     # Generated artifacts
├── logs/                          # Application logs
└── models/                        # LLM model weights
```

## Monitoring

### View Container Logs

```bash
# All containers
docker compose -f deploy/docker-compose.dgx.yml logs -f

# API only
docker compose -f deploy/docker-compose.dgx.yml logs -f api

# Dashboard only
docker compose -f deploy/docker-compose.dgx.yml logs -f dashboard
```

### Check Service Status

```bash
# API health
curl http://localhost:8000/health

# API status
curl http://localhost:8000/status

# Model status (if using vLLM)
curl http://localhost:30001/v1/models
curl http://localhost:30002/v1/models
```

### GPU Monitoring

```bash
# Watch GPU usage
watch -n1 nvidia-smi

# GPU memory summary
nvidia-smi --query-gpu=name,memory.used,memory.total --format=csv
```

## Troubleshooting

### API Won't Start

```bash
# Check logs
docker compose -f deploy/docker-compose.dgx.yml logs api

# Common issues:
# - Port 8000 already in use: lsof -ti:8000 | xargs kill
# - Missing .env file: cp deploy/env.template .env
```

### Dashboard Connection Issues

```bash
# Verify API is running
curl http://localhost:8000/health

# Check WebSocket endpoint
# Open browser console and look for WebSocket errors

# Verify CORS settings in API
```

### Models Won't Load

```bash
# Check GPU memory
nvidia-smi

# Check model logs
tail -f /mnt/spark-data3/meridian/logs/vllm-fast.log
tail -f /mnt/spark-data3/meridian/logs/vllm-reasoning.log

# Reduce memory if needed (edit start-models.sh):
# --gpu-memory-utilization 0.40
```

### SSH Tunnel Drops

```bash
# Use autossh for persistent tunnel
autossh -M 0 -f -N \
  -o "ServerAliveInterval 30" \
  -o "ServerAliveCountMax 3" \
  -L 3000:localhost:3000 \
  -L 8000:localhost:8000 \
  gibsonv32@dgx-spark
```

## Performance Tuning

### API Server

```yaml
# For higher throughput, increase workers
docker compose -f deploy/docker-compose.dgx.yml up -d --scale api=4
```

### LLM Models

```bash
# For faster inference, enable speculative decoding
# Edit start-models.sh:
# --speculative-algorithm EAGLE
# --speculative-num-steps 5
```

### Dashboard

```bash
# Pre-build for production
cd dashboard
npm run build

# Serve with nginx (already configured in Dockerfile)
```

## Updating

### Update Codebase

```bash
# On development machine
git pull origin main

# Re-deploy
./deploy/deploy-full-stack.sh --build
```

### Update Models

```bash
# Pull new model weights
huggingface-cli download Qwen/Qwen2.5-14B-Instruct --local-dir /mnt/spark-data3/models/Qwen2.5-14B-Instruct

# Restart models
./deploy/start-models.sh --stop
./deploy/start-models.sh
```

## Security Notes

1. **API Keys**: Never commit `.env` files to git
2. **Network**: API listens on 0.0.0.0 - use firewall rules if needed
3. **SSH**: Use key-based authentication, disable password auth
4. **Docker**: Run containers as non-root when possible

## Quick Reference

```bash
# Deploy
./deploy/deploy-full-stack.sh

# Start/Stop
docker compose -f deploy/docker-compose.dgx.yml up -d
docker compose -f deploy/docker-compose.dgx.yml down

# Logs
docker compose -f deploy/docker-compose.dgx.yml logs -f

# Models
./deploy/start-models.sh
./deploy/start-models.sh --status
./deploy/start-models.sh --stop

# Test
curl http://localhost:8000/health
curl http://localhost:3000/health

# SSH Tunnel
ssh -L 3000:localhost:3000 -L 8000:localhost:8000 gibsonv32@dgx-spark
```

---

*MERIDIAN v0.1.0 | DGX Spark Deployment Guide*
