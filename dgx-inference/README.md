# DGX Inference Stack

Dual-model AI inference stack for NVIDIA DGX Spark deployment, featuring:

- **Reasoning**: DeepSeek-R1-Distill-Llama-70B via SGLang with speculative decoding (EAGLE)
- **Coding**: Claude API (Anthropic)
- **Routing**: Automatic task classification with OpenAI-compatible API

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         DGX Spark                                   │
│                                                                     │
│  ┌─────────────────┐         ┌─────────────────────────────────┐   │
│  │  Router (8080)  │────────▶│      SGLang Server (8000)       │   │
│  │   FastAPI       │         │  DeepSeek-R1-Distill-Llama-70B  │   │
│  │                 │         │  + EAGLE Speculative Decoding   │   │
│  │  Task Routing:  │         │  + Tensor Parallel (tp=2)       │   │
│  │  - coding→Claude│         └─────────────────────────────────┘   │
│  │  - reasoning→   │                                               │
│  │    SGLang       │                                               │
│  └────────┬────────┘                                               │
│           │                                                         │
└───────────┼─────────────────────────────────────────────────────────┘
            │
            │ (coding tasks)
            ▼
    ┌───────────────┐
    │  Claude API   │
    │  (Anthropic)  │
    └───────────────┘
```

## Requirements

- NVIDIA DGX Spark (or compatible GPU system)
- Docker with NVIDIA Container Runtime
- ~96GB GPU memory (for 70B model with tp=2)
- Anthropic API key

## Quick Start

### 1. Clone and Configure

```bash
cd dgx-inference

# Copy environment template
cp .env.example .env

# Edit .env and add your ANTHROPIC_API_KEY
nano .env
```

### 2. Start the Stack

```bash
# Make scripts executable
chmod +x scripts/*.sh

# Start everything (pulls images, starts services, waits for readiness)
./scripts/start.sh
```

The startup process:
1. Pulls the SGLang Docker image
2. Starts SGLang server (loads 70B model - takes 3-5 minutes)
3. Starts the router service
4. Performs health checks
5. Prints connection info

### 3. Test

```bash
# Check status
curl http://localhost:8080/status

# Test reasoning (routes to DeepSeek)
curl http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Explain step by step how to solve: If a train travels 120 miles in 2 hours, what is its average speed?"}]
  }'

# Test coding (routes to Claude)
curl http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Write a Python function to calculate fibonacci numbers"}]
  }'

# Explicit routing
curl http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "reasoning",
    "messages": [{"role": "user", "content": "What are the implications of quantum computing for cryptography?"}]
  }'
```

## Remote Access

### SSH Tunnel (from your local machine)

```bash
# Start tunnel to DGX
./scripts/tunnel.sh dgx-spark gibsonv32

# Or with environment variables
export DGX_HOST=192.168.1.100
export DGX_USER=myuser
./scripts/tunnel.sh

# Check tunnel status
./scripts/tunnel.sh --status

# Stop tunnel
./scripts/tunnel.sh --stop
```

Once the tunnel is active, access the API at `http://localhost:8080` from your local machine.

### Direct SSH Tunnel (manual)

```bash
ssh -L 8080:localhost:8080 -L 8000:localhost:8000 gibsonv32@dgx-spark
```

## API Reference

### OpenAI-Compatible Chat Completions

**Endpoint**: `POST /v1/chat/completions`

```json
{
  "model": "auto",           // "auto", "coding", or "reasoning"
  "messages": [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Your prompt here"}
  ],
  "max_tokens": 4096,        // Optional
  "temperature": 0.7,        // Optional
  "stream": false,           // Optional - enable streaming
  "task_type": "auto"        // Optional - explicit routing: "coding", "reasoning", "auto"
}
```

**Routing Logic**:
1. If `model` contains "claude" or "coding" → Claude
2. If `model` contains "deepseek" or "reasoning" → SGLang
3. If `task_type` is set explicitly → use that
4. Otherwise, auto-detect based on prompt keywords

### Other Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Health check |
| `GET /status` | Backend status (Claude + SGLang) |
| `GET /v1/models` | List available routing models |

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | (required) | Anthropic API key |
| `SGLANG_URL` | `http://localhost:8000` | SGLang server URL |
| `CLAUDE_MODEL` | `claude-sonnet-4-20250514` | Claude model |
| `LOG_LEVEL` | `INFO` | Logging level |
| `HF_TOKEN` | (optional) | HuggingFace token |

### Task Classification Keywords

Edit `src/config.py` to customize which prompts route to which backend.

**Coding keywords** (→ Claude):
- Programming languages: python, javascript, rust, etc.
- Actions: implement, debug, refactor, write code
- Tools: docker, git, api, database

**Reasoning keywords** (→ DeepSeek):
- Analysis: explain, analyze, compare, evaluate
- Math: calculate, prove, equation
- Planning: step by step, strategy, approach

## Troubleshooting

### SGLang won't start

```bash
# Check logs
docker compose logs sglang

# Common issues:
# - Out of GPU memory: reduce --mem-fraction-static in docker-compose.yml
# - Model not found: check HF_TOKEN for gated models
```

### Router can't connect to SGLang

```bash
# Check if SGLang is running
curl http://localhost:8000/health

# Check Docker network
docker network inspect inference-net
```

### Slow inference

1. Verify speculative decoding is enabled (check SGLang logs for "EAGLE")
2. Check GPU utilization: `nvidia-smi`
3. Reduce `--max-total-tokens` if memory-bound

### Claude API errors

```bash
# Verify API key
curl https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "content-type: application/json" \
  -H "anthropic-version: 2023-06-01" \
  -d '{"model":"claude-sonnet-4-20250514","max_tokens":10,"messages":[{"role":"user","content":"Hi"}]}'
```

## Stopping the Stack

```bash
# Stop all services
./scripts/stop.sh

# Or manually
docker compose down

# Remove volumes (clears model cache)
docker compose down -v
```

## File Structure

```
dgx-inference/
├── docker-compose.yml      # Container orchestration
├── Dockerfile              # Router service image
├── requirements.txt        # Python dependencies
├── .env.example            # Environment template
├── README.md               # This file
├── src/
│   ├── __init__.py
│   ├── config.py           # Pydantic settings
│   └── router.py           # FastAPI router service
└── scripts/
    ├── start.sh            # Start the stack
    ├── stop.sh             # Stop the stack
    └── tunnel.sh           # SSH tunnel helper
```

## Performance Notes

- **DeepSeek 70B with EAGLE**: ~2-3x speedup over standard decoding
- **First request**: May be slow as model warms up
- **Tensor Parallelism**: tp=2 splits model across GPU memory efficiently
- **Memory Usage**: ~80GB VRAM for 70B model with tp=2

## License

MIT
