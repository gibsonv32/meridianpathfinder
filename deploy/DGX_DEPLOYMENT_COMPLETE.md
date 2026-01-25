# MERIDIAN DGX Spark Deployment - Complete Guide

## Part 1: Hardware & Software Confirmed

### DGX Spark Specifications
| Component | Spec |
|-----------|------|
| CPU | AMD EPYC 9V84 (128 cores) |
| RAM | 512 GB |
| GPU | NVIDIA RTX 6000 Ada (48GB VRAM) |
| Storage | 2TB NVMe + 8TB data volume |
| OS | Ubuntu 24.04 |

### Current Software Stack
- CUDA 12.x
- Python 3.11
- vLLM (for model serving)
- GPT-OSS-120B running on port 30000

---

## Part 2: MERIDIAN Codebase Analysis (COMPLETE)

### 2.1 Project Structure

```
meridian/
├── __init__.py          # Version: 0.1.0
├── cli.py               # Typer-based CLI (1400+ lines)
├── config.py            # YAML config loader
├── core/
│   ├── fingerprint.py   # SQLite-based artifact integrity
│   ├── gates.py         # Mode transition enforcement
│   ├── modes.py         # Mode enum (0, 0.5, 1-7)
│   └── state.py         # Project state management
├── llm/
│   ├── config.py        # LLMConfig Pydantic model
│   └── providers.py     # AnthropicProvider, OllamaProvider
├── modes/
│   ├── base.py          # Base executor class
│   ├── mode_0.py        # EDA
│   ├── mode_0_5.py      # Opportunity Discovery
│   ├── mode_1.py        # Decision Intelligence
│   ├── mode_2.py        # Feasibility
│   ├── mode_3.py        # Strategy
│   ├── mode_4.py        # Business Case
│   ├── mode_5.py        # Code Generation
│   ├── mode_6.py        # Execution/Ops
│   ├── mode_6_5.py      # Interpretation
│   └── mode_7.py        # Delivery
├── artifacts/
│   └── schemas.py       # Pydantic artifact schemas
├── api/
│   ├── server.py        # FastAPI REST API
│   └── client.py        # HTTP client
├── data/
│   ├── quality.py       # Data quality analyzer
│   └── visualize.py     # EDA visualizations
├── ml/
│   └── automl.py        # Optuna-based AutoML
├── skills/
│   └── loader.py        # Skill context loader
└── utils/
    └── backup.py        # Backup/restore utilities
```

### 2.2 Dependencies (from pyproject.toml)

```toml
dependencies = [
  "typer>=0.12.0",        # CLI framework
  "pydantic>=2.0.0",      # Data validation
  "pydantic-settings>=2.0.0",
  "pyyaml>=6.0.0",        # Config files
  "rich>=13.0.0",         # Terminal formatting
  "pandas>=2.0.0",        # Data manipulation
  "numpy>=1.24.0",        # Numerical computing
  "scikit-learn>=1.3.0",  # ML algorithms
  "anthropic>=0.40.0",    # Anthropic SDK
  "httpx>=0.27.0",        # HTTP client
  "pytest>=8.0.0",        # Testing
]
```

**Additional for DGX:**
- `fastapi` + `uvicorn` (API server)
- `optuna` (AutoML, optional)
- `matplotlib` + `seaborn` (visualizations, optional)

### 2.3 LLM Integration Points

**Provider Interface** (`meridian/llm/providers.py`):
```python
class LLMProvider(Protocol):
    @property
    def model_name(self) -> str: ...
    def complete(self, prompt: str, system: Optional[str], max_tokens: int) -> str: ...
    def complete_structured(self, prompt: str, schema: Type[BaseModel], system: Optional[str]) -> BaseModel: ...
    def test_connection(self) -> bool: ...
```

**Existing Providers:**
1. `AnthropicProvider` - Uses Anthropic SDK
2. `OllamaProvider` - Uses OpenAI-compatible `/api/generate`

**Factory Function:**
```python
def get_provider(config: dict, project_path: Optional[Path] = None) -> LLMProvider
```

**Config Integration:**
- Reads from `meridian.yaml` under `llm:` key
- Supports `provider`, `model`, `api_key`, `base_url`, `max_tokens`, `temperature`

### 2.4 CLI Commands

| Command | Description |
|---------|-------------|
| `meridian init` | Initialize new project |
| `meridian status` | Show project status |
| `meridian demo` | Run full demo pipeline |
| `meridian mode {N} run` | Execute specific mode |
| `meridian artifacts list` | List artifacts |
| `meridian artifacts show` | Show artifact details |
| `meridian llm status` | Check LLM connectivity |
| `meridian llm set-provider` | Change provider |
| `meridian api start` | Start REST API server |
| `meridian data analyze` | Data quality analysis |
| `meridian ml tune` | AutoML hyperparameter tuning |
| `meridian backup create/restore` | Backup management |

### 2.5 Mode Complexity Analysis

| Mode | Complexity | Recommended Model |
|------|------------|-------------------|
| 0 (EDA) | Low | Qwen-14B (fast) |
| 0.5 (Opportunity) | Low | Qwen-14B (fast) |
| 1 (Decision Intel) | Low | Qwen-14B (fast) |
| 2 (Feasibility) | **High** | DeepSeek-70B |
| 3 (Strategy) | **High** | DeepSeek-70B |
| 4 (Business Case) | **High** | DeepSeek-70B |
| 5 (Code Gen) | **High** | DeepSeek-70B |
| 6 (Execution) | **High** | DeepSeek-70B |
| 6.5 (Interpretation) | **High** | DeepSeek-70B |
| 7 (Delivery) | Low | Qwen-14B (fast) |

### 2.6 Artifact System

**Storage:** `.meridian/artifacts/{mode_N}/ArtifactType_{uuid}.json`

**Fingerprinting:** SQLite database at `.meridian/fingerprints.db`
- SHA-256 hash of artifact content
- Verification on read
- Override audit logging

**Key Artifact Types:**
- `Mode0GatePacket` (EDA results)
- `OpportunityBrief`, `OpportunityBacklog`
- `DecisionIntelProfile`
- `FeasibilityReport`
- `ModelRecommendations`, `FeatureRegistry`
- `BusinessCaseScorecard`, `ThresholdFramework`
- `CodeGenerationPlan`
- `ExecutionOpsScorecard`
- `InterpretationPackage`
- `DeliveryManifest`

---

## Part 3: Deployment Architecture

### 3.1 Model Configuration

```
┌─────────────────────────────────────────────────────────────┐
│                      DGX Spark GPU (48GB)                   │
├─────────────────────────────┬───────────────────────────────┤
│  Qwen-14B (~22GB)           │  DeepSeek-70B-AWQ (~24GB)     │
│  Port: 30001                │  Port: 30002                  │
│  Modes: 0, 0.5, 1, 7        │  Modes: 2, 3, 4, 5, 6, 6.5    │
│  Latency: ~1-3s             │  Latency: ~5-15s              │
└─────────────────────────────┴───────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │   LLM Router    │
                    │ (llm_router.py) │
                    └─────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │    MERIDIAN     │
                    │   CLI / API     │
                    └─────────────────┘
```

### 3.2 Directory Layout on DGX

```
/home/gibsonv32/dev/meridian/     # Code (NVMe)
├── meridian/                      # Package
├── deploy/                        # Deployment scripts
├── tests/                         # Unit tests
├── meridian.yaml                  # DGX config
└── .venv/                         # Python environment

/mnt/spark-data3/meridian/        # Data (8TB volume)
├── data/                          # Input datasets
├── artifacts/                     # Generated artifacts
├── logs/                          # Application logs
└── rag/                           # RAG indexes (optional)

/mnt/spark-data3/models/          # LLM models
├── Qwen2.5-14B-Instruct/
└── DeepSeek-R1-Distill-Llama-70B/
```

---

## Part 4: Deployment Files Created

### 4.1 `deploy/llm_router.py`
- `DGXRouterProvider` class implementing `LLMProvider` protocol
- Automatic mode-based routing to fast/reasoning models
- OpenAI-compatible API calls (works with vLLM)
- JSON mode support for structured outputs
- Health check and status endpoints

### 4.2 `deploy/meridian-dgx.yaml`
- Complete config for DGX deployment
- Dual-model LLM settings
- Data paths pointing to `/mnt/spark-data3/`
- API server settings for remote access
- vLLM serving parameters documented

### 4.3 `deploy/deploy-to-dgx.sh`
- Rsync codebase from MacBook → DGX
- Setup Python environment with uv
- Create directory structure
- Initialize MERIDIAN project
- Run validation tests

### 4.4 `deploy/start-models.sh`
- Start vLLM servers for both models
- GPU memory allocation (45% + 50%)
- AWQ quantization for 70B model
- Health monitoring
- Log management

---

## Part 5: Deployment Checklist

### Pre-Deployment
- [ ] Download models to `/mnt/spark-data3/models/`
  ```bash
  # On DGX:
  huggingface-cli download Qwen/Qwen2.5-14B-Instruct
  huggingface-cli download deepseek-ai/DeepSeek-R1-Distill-Llama-70B
  ```
- [ ] Install vLLM: `pip install vllm`
- [ ] Verify GPU access: `nvidia-smi`

### Deployment
```bash
# From MacBook:
cd /Users/vincentgibson/dev/meridianpathfinder
chmod +x deploy/*.sh

# Deploy to DGX
./deploy/deploy-to-dgx.sh
```

### Post-Deployment (on DGX)
```bash
# SSH to DGX
ssh gibsonv32@dgx-spark
cd ~/dev/meridian

# Start model servers
./deploy/start-models.sh

# Verify
./deploy/start-models.sh --status

# Test router
source .venv/bin/activate
python -m meridian.llm.router

# Run full test
meridian demo --data data_mode2.csv --target target --row '{"x1":0.1,"x2":-0.2}'
```

---

## Part 6: Performance Expectations

| Metric | Fast Model (14B) | Reasoning Model (70B) |
|--------|------------------|----------------------|
| Latency (simple) | 1-3s | 5-10s |
| Latency (complex) | 3-8s | 10-30s |
| Tokens/sec | ~50-80 | ~20-40 |
| Memory | ~22GB | ~24GB (AWQ) |

**Full Pipeline (Modes 0-7):**
- Headless (no LLM): ~30 seconds
- With LLM: ~3-5 minutes
- With complex data: ~5-10 minutes

---

## Part 7: Troubleshooting

### Model won't load
```bash
# Check GPU memory
nvidia-smi

# Reduce memory utilization in start-models.sh
--gpu-memory-utilization 0.40  # Instead of 0.45
```

### Router can't connect
```bash
# Test endpoints directly
curl http://localhost:30001/v1/models
curl http://localhost:30002/v1/models

# Check logs
tail -f /mnt/spark-data3/meridian/logs/vllm-*.log
```

### Import errors
```bash
# Ensure router is in path
cp deploy/llm_router.py meridian/llm/router.py

# Reinstall package
uv pip install -e .
```

---

## Quick Reference Commands

```bash
# Deploy
./deploy/deploy-to-dgx.sh

# Start models
./deploy/start-models.sh

# Check status
./deploy/start-models.sh --status

# Stop models
./deploy/start-models.sh --stop

# Run MERIDIAN
meridian status
meridian demo --data data.csv --target y --row '{"x1":0.5}'
meridian api start --host 0.0.0.0

# Test router
python -c "from meridian.llm.router import get_dgx_provider; p=get_dgx_provider(); print(p.get_model_status())"
```

---

*Generated: $(date)*
*MERIDIAN Version: 0.1.0*
