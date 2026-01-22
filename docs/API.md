# MERIDIAN API Guide

MERIDIAN provides a REST API for programmatic access to all pipeline functionality. This enables integration with web applications, automation tools, and other systems.

## Quick Start

### 1. Install API Dependencies

```bash
pip install fastapi uvicorn requests
```

### 2. Start the API Server

```bash
# Start server on default port 8000
meridian api start

# Custom host and port
meridian api start --host 0.0.0.0 --port 8080

# Development mode with auto-reload
meridian api start --reload
```

### 3. Access API Documentation

The API provides interactive documentation:

```bash
# Open in browser
meridian api docs

# Or navigate to:
http://localhost:8000/docs  # Swagger UI
http://localhost:8000/redoc  # ReDoc
```

## API Endpoints

### Health Check

```http
GET /
```

Check if API is running:

```bash
curl http://localhost:8000/
```

Response:
```json
{
  "status": "ok",
  "service": "MERIDIAN API"
}
```

### Project Management

#### Initialize Project

```http
POST /project/init
```

Create a new MERIDIAN project:

```bash
curl -X POST http://localhost:8000/project/init \
  -H "Content-Type: application/json" \
  -d '{
    "path": "/path/to/project",
    "name": "My ML Project",
    "force": false
  }'
```

#### Get Project Status

```http
GET /project/status?project_path=/path/to/project
```

Get current project status:

```bash
curl "http://localhost:8000/project/status?project_path=/path/to/project"
```

Response:
```json
{
  "project_name": "My ML Project",
  "path": "/path/to/project",
  "current_mode": null,
  "modes": [
    {
      "mode": "0",
      "status": "complete",
      "verdict": "go",
      "artifacts": ["artifact-id-1", "artifact-id-2"]
    },
    ...
  ]
}
```

### Mode Execution

#### Run Mode

```http
POST /mode/run
```

Execute a specific mode:

```bash
curl -X POST http://localhost:8000/mode/run \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "2",
    "params": {
      "data_path": "data/sample.csv",
      "target_col": "target",
      "split": "stratified"
    },
    "headless": false
  }'
```

### Artifact Management

#### List Artifacts

```http
GET /artifacts/list
```

Query parameters:
- `project_path` (required): Project directory
- `artifact_type` (optional): Filter by type
- `mode` (optional): Filter by mode
- `latest_only` (optional): Only show latest per type

```bash
curl "http://localhost:8000/artifacts/list?project_path=/path/to/project&latest_only=true"
```

#### Get Artifact

```http
GET /artifacts/{artifact_id}?project_path=/path/to/project
```

Retrieve specific artifact:

```bash
curl "http://localhost:8000/artifacts/abc-123?project_path=/path/to/project"
```

### Demo Runner

#### Run Demo

```http
POST /demo
```

Execute the demo pipeline:

```bash
curl -X POST http://localhost:8000/demo \
  -H "Content-Type: application/json" \
  -d '{
    "project_path": "/path/to/project",
    "data_path": "data/sample.csv",
    "target_col": "target",
    "prediction_row": {
      "feature1": 0.5,
      "feature2": 1.0
    }
  }'
```

## Python Client

Use the provided Python client for easier integration:

### Installation

```python
from meridian.api.client import MeridianAPIClient
```

### Basic Usage

```python
# Initialize client
client = MeridianAPIClient("http://localhost:8000")

# Check health
if client.health_check():
    print("API is running")

# Get project status
status = client.get_status("/path/to/project")
print(f"Project: {status['project_name']}")
print(f"Current mode: {status['current_mode']}")

# List artifacts
artifacts = client.list_artifacts(
    project_path="/path/to/project",
    latest_only=True
)
for artifact in artifacts:
    print(f"{artifact['artifact_type']}: {artifact['artifact_id']}")

# Run a mode
result = client.run_mode(
    mode="2",
    params={
        "data_path": "data/sample.csv",
        "target_col": "target",
        "split": "stratified"
    }
)
print(f"Mode execution: {result['status']}")

# Run demo
demo_result = client.run_demo(
    project_path="/path/to/project",
    data_path="data/sample.csv",
    target_col="target",
    prediction_row={"feature1": 0.5, "feature2": 1.0}
)
print(f"Training metrics: {demo_result['train']}")
print(f"Prediction: {demo_result['prediction']}")
```

### Advanced Usage

```python
# Run pipeline sequence
client.run_pipeline(
    project_path="/path/to/project",
    modes=["0", "1", "2", "3"],
    params={
        "0": {"data_path": "data/sample.csv"},
        "1": {
            "business_kpi": "Reduce churn",
            "hypotheses": ["H1", "H2"]
        },
        "2": {
            "data_path": "data/sample.csv",
            "target_col": "target"
        },
        "3": {
            "data_path": "data/sample.csv",
            "target_col": "target"
        }
    }
)

# Export all artifacts
count = client.export_artifacts(
    project_path="/path/to/project",
    output_dir="./exports"
)
print(f"Exported {count} artifacts")
```

## JavaScript/TypeScript Client

Example using fetch API:

```javascript
// api-client.js
class MeridianClient {
  constructor(baseUrl = 'http://localhost:8000') {
    this.baseUrl = baseUrl;
  }

  async getStatus(projectPath) {
    const response = await fetch(
      `${this.baseUrl}/project/status?project_path=${encodeURIComponent(projectPath)}`
    );
    return response.json();
  }

  async runMode(mode, params = {}, headless = false) {
    const response = await fetch(`${this.baseUrl}/mode/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mode, params, headless })
    });
    return response.json();
  }

  async listArtifacts(projectPath, options = {}) {
    const params = new URLSearchParams({
      project_path: projectPath,
      ...options
    });
    const response = await fetch(`${this.baseUrl}/artifacts/list?${params}`);
    return response.json();
  }
}

// Usage
const client = new MeridianClient();
const status = await client.getStatus('/path/to/project');
console.log(status);
```

## Authentication & Security

### API Key Authentication (Optional)

Add API key authentication by modifying the server:

```python
# In meridian/api/server.py
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key")

@app.middleware("http")
async def validate_api_key(request: Request, call_next):
    if request.url.path in ["/docs", "/redoc", "/openapi.json", "/"]:
        return await call_next(request)
    
    api_key = request.headers.get("X-API-Key")
    if api_key != os.getenv("MERIDIAN_API_KEY"):
        return JSONResponse({"error": "Invalid API key"}, status_code=401)
    
    return await call_next(request)
```

Use with client:

```python
client = MeridianAPIClient("http://localhost:8000")
client.session.headers["X-API-Key"] = "your-secret-key"
```

### HTTPS Setup

For production, use HTTPS with a reverse proxy:

```nginx
# nginx.conf
server {
    listen 443 ssl;
    server_name api.meridian.example.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Deployment

### Docker

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . /app

RUN pip install -e . fastapi uvicorn

EXPOSE 8000

CMD ["uvicorn", "meridian.api.server:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build and run:

```bash
docker build -t meridian-api .
docker run -p 8000:8000 -v /local/projects:/projects meridian-api
```

### Production Server

Use Gunicorn with Uvicorn workers:

```bash
pip install gunicorn

gunicorn meridian.api.server:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --access-logfile - \
  --error-logfile -
```

### Kubernetes

```yaml
# meridian-api.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: meridian-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: meridian-api
  template:
    metadata:
      labels:
        app: meridian-api
    spec:
      containers:
      - name: api
        image: meridian-api:latest
        ports:
        - containerPort: 8000
        env:
        - name: ANTHROPIC_API_KEY
          valueFrom:
            secretKeyRef:
              name: meridian-secrets
              key: anthropic-api-key
---
apiVersion: v1
kind: Service
metadata:
  name: meridian-api-service
spec:
  selector:
    app: meridian-api
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer
```

## Monitoring

### Health Checks

```python
# Add health endpoint
@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": __version__
    }
```

### Logging

```python
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("meridian.api")

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    
    logger.info(
        f"{request.method} {request.url.path} "
        f"completed in {duration:.3f}s "
        f"status={response.status_code}"
    )
    
    return response
```

### Metrics (Prometheus)

```python
from prometheus_client import Counter, Histogram, generate_latest

request_count = Counter('meridian_api_requests_total', 'Total requests')
request_duration = Histogram('meridian_api_request_duration_seconds', 'Request duration')

@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type="text/plain")
```

## Error Handling

The API returns standard HTTP status codes:

| Status Code | Meaning |
|-------------|---------|
| 200 | Success |
| 400 | Bad Request (invalid parameters) |
| 401 | Unauthorized (invalid API key) |
| 404 | Not Found (project/artifact not found) |
| 500 | Internal Server Error |

Error response format:

```json
{
  "error": "Error message",
  "detail": "Detailed error information",
  "status_code": 400
}
```

## Rate Limiting

Add rate limiting for production:

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["100 per minute"]
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.post("/mode/run")
@limiter.limit("10 per minute")
async def run_mode(request: Request, ...):
    ...
```

## WebSocket Support (Future)

For real-time updates during long-running operations:

```python
from fastapi import WebSocket

@app.websocket("/ws/mode/{mode_id}")
async def mode_progress(websocket: WebSocket, mode_id: str):
    await websocket.accept()
    
    # Send progress updates
    while running:
        progress = get_mode_progress(mode_id)
        await websocket.send_json({
            "type": "progress",
            "value": progress
        })
        await asyncio.sleep(1)
```

## Testing

Test the API with pytest:

```python
# test_api.py
from fastapi.testclient import TestClient
from meridian.api.server import app

client = TestClient(app)

def test_health_check():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_project_status():
    response = client.get("/project/status?project_path=/test")
    assert response.status_code in [200, 404]
```

Run tests:
```bash
pytest tests/test_api.py
```

## Troubleshooting

### Port Already in Use

```bash
# Find process using port 8000
lsof -i :8000

# Kill process
kill -9 <PID>
```

### CORS Issues

Add allowed origins:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://myapp.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Connection Refused

Check server is running:
```bash
ps aux | grep uvicorn
netstat -an | grep 8000
```

### Timeout Errors

Increase timeout for long operations:
```python
client = MeridianAPIClient("http://localhost:8000", timeout=60)
```