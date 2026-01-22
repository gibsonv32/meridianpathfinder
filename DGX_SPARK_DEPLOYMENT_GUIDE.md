# MERIDIAN on DGX Spark: Production Deployment Guide

## Overview

This guide walks you through deploying the MERIDIAN ML framework on NVIDIA DGX systems with Apache Spark, providing a scalable, production-ready environment for data scientists and ML engineers.

## Prerequisites

- NVIDIA DGX system with Spark cluster
- Docker support
- Network access for SGLang model servers
- Access to your data sources

## Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   MERIDIAN      │    │   SGLang LLM    │    │   Spark         │
│   Framework     │◄──►│   Server        │    │   Cluster       │
│                 │    │   (gpt-oss-120b)│    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
        │                       │                      │
        └───────────────────────┼──────────────────────┘
                               │
                    ┌─────────────────┐
                    │   Storage       │
                    │   (HDFS/S3)     │
                    └─────────────────┘
```

## Step-by-Step Deployment

### 1. Prepare the DGX Environment

```bash
# SSH into your DGX system
ssh user@dgx-hostname

# Create deployment directory
mkdir -p /workspace/meridian-deploy
cd /workspace/meridian-deploy

# Clone MERIDIAN repository
git clone <your-meridian-repo> .
```

### 2. Deploy SGLang Model Server

```bash
# Create SGLang deployment
cat > sglang-deployment.yaml << EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sglang-server
spec:
  replicas: 2
  selector:
    matchLabels:
      app: sglang
  template:
    metadata:
      labels:
        app: sglang
    spec:
      containers:
      - name: sglang
        image: lmsysorg/sglang:latest
        ports:
        - containerPort: 30000
        env:
        - name: MODEL_PATH
          value: "/models/gpt-oss-120b"
        - name: WORKER_URL
          value: "http://localhost:30000"
        resources:
          limits:
            nvidia.com/gpu: 2
          requests:
            nvidia.com/gpu: 2
        volumeMounts:
        - name: model-storage
          mountPath: /models
      volumes:
      - name: model-storage
        hostPath:
          path: /data/models
---
apiVersion: v1
kind: Service
metadata:
  name: sglang-service
spec:
  selector:
    app: sglang
  ports:
  - port: 30000
    targetPort: 30000
  type: LoadBalancer
EOF

# Deploy SGLang
kubectl apply -f sglang-deployment.yaml

# Wait for service to be ready
kubectl wait --for=condition=available deployment/sglang-server --timeout=300s
```

### 3. Configure MERIDIAN for DGX Spark

```bash
# Create production configuration
cat > meridian.yaml << EOF
# MERIDIAN Production Configuration for DGX Spark

# LLM Configuration
llm:
  provider: "openai"  # Uses OpenAI-compatible API
  base_url: "http://sglang-service:30000/v1"
  model: "gpt-oss-120b"
  api_key: "not-needed"  # SGLang doesn't require API key
  temperature: 0.3

# Self-Healing Configuration
self_healing:
  enabled: true
  max_cost_usd: 10.0  # Budget limit
  max_attempts: 5
  circuit_breaker:
    failure_threshold: 10
    recovery_timeout: 300

# Spark Configuration
spark:
  app_name: "MERIDIAN-ML-Pipeline"
  master: "spark://spark-master:7077"
  executor_memory: "8g"
  executor_cores: 4
  num_executors: 10
  
# Data Configuration
data:
  input_formats: ["csv", "parquet", "delta"]
  storage_path: "hdfs://namenode:9000/meridian"
  checkpoint_path: "hdfs://namenode:9000/meridian/checkpoints"

# Feature Store Configuration
feature_store:
  backend: "delta"
  path: "hdfs://namenode:9000/meridian/features"
  
# Monitoring
monitoring:
  enabled: true
  metrics_endpoint: "http://prometheus:9090"
  log_level: "INFO"
EOF
```

### 4. Create Spark-Enabled MERIDIAN Container

```bash
# Create Dockerfile for MERIDIAN + Spark
cat > Dockerfile << EOF
FROM apache/spark-py:v3.4.0

USER root

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    git \\
    curl \\
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install MERIDIAN framework
COPY . /opt/meridian
WORKDIR /opt/meridian
RUN pip install -e .

# Create entrypoint script
RUN cat > /opt/meridian/entrypoint.sh << 'SCRIPT'
#!/bin/bash
set -e

# Initialize Spark session with MERIDIAN
export PYSPARK_PYTHON=/opt/conda/bin/python
export SPARK_HOME=/opt/spark
export PYTHONPATH=/opt/meridian:$PYTHONPATH

# Start MERIDIAN service
if [ "$1" = "driver" ]; then
    exec python -m meridian.spark.driver
elif [ "$1" = "worker" ]; then
    exec python -m meridian.spark.worker
else
    exec "$@"
fi
SCRIPT

RUN chmod +x /opt/meridian/entrypoint.sh

ENTRYPOINT ["/opt/meridian/entrypoint.sh"]
CMD ["driver"]
EOF

# Build container
docker build -t meridian-spark:latest .
```

### 5. Deploy MERIDIAN on Spark

```bash
# Create Kubernetes deployment for MERIDIAN driver
cat > meridian-deployment.yaml << EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: meridian-driver
spec:
  replicas: 1
  selector:
    matchLabels:
      app: meridian-driver
  template:
    metadata:
      labels:
        app: meridian-driver
    spec:
      containers:
      - name: meridian
        image: meridian-spark:latest
        command: ["/opt/meridian/entrypoint.sh", "driver"]
        env:
        - name: SPARK_MASTER_URL
          value: "spark://spark-master:7077"
        - name: MERIDIAN_CONFIG
          value: "/config/meridian.yaml"
        ports:
        - containerPort: 8080  # MERIDIAN API
        - containerPort: 4040  # Spark UI
        volumeMounts:
        - name: config
          mountPath: /config
        - name: data
          mountPath: /data
        resources:
          requests:
            memory: "4Gi"
            cpu: "2"
          limits:
            memory: "8Gi"
            cpu: "4"
      volumes:
      - name: config
        configMap:
          name: meridian-config
      - name: data
        persistentVolumeClaim:
          claimName: meridian-data
---
apiVersion: v1
kind: Service
metadata:
  name: meridian-service
spec:
  selector:
    app: meridian-driver
  ports:
  - name: api
    port: 8080
    targetPort: 8080
  - name: spark-ui
    port: 4040
    targetPort: 4040
  type: LoadBalancer
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: meridian-config
data:
  meridian.yaml: |
$(cat meridian.yaml | sed 's/^/    /')
EOF

# Deploy MERIDIAN
kubectl apply -f meridian-deployment.yaml
```

### 6. Create MERIDIAN API Wrapper

```bash
# Create API server for external access
cat > meridian_api.py << 'EOF'
#!/usr/bin/env python3
"""
MERIDIAN API Server for DGX Spark deployment
"""
import os
from pathlib import Path
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse
import uvicorn
from pydantic import BaseModel
from typing import List, Optional

from meridian.core.state import MeridianProject
from meridian.config import load_config
from meridian.llm.providers import get_provider
from meridian.modes.mode_0 import Mode0Executor
from meridian.modes.mode_1 import Mode1Executor
from meridian.modes.mode_2 import Mode2Executor
from meridian.modes.mode_3 import Mode3Executor

app = FastAPI(title="MERIDIAN ML Framework API", version="1.0.0")

# Global state
project = None
llm_provider = None

class DataAnalysisRequest(BaseModel):
    file_path: str
    self_heal: bool = True
    quality_check: bool = True

class BusinessKPIRequest(BaseModel):
    business_kpi: str
    hypotheses: List[str]

class FeasibilityRequest(BaseModel):
    data_path: str
    target_col: str
    split: str = "stratified"

class MLStrategyRequest(BaseModel):
    data_path: str
    target_col: str
    self_heal: bool = True

@app.on_event("startup")
async def startup():
    global project, llm_provider
    
    # Initialize MERIDIAN project
    project = MeridianProject(Path("/workspace"))
    
    # Load configuration and LLM provider
    config = load_config()
    llm_provider = get_provider(config, Path("/workspace"))
    
    print("🚀 MERIDIAN API Server started on DGX Spark!")

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "MERIDIAN on DGX Spark"}

@app.post("/api/v1/data-analysis")
async def analyze_data(request: DataAnalysisRequest):
    """Run Mode 0: Data Understanding with self-healing"""
    try:
        mode0 = Mode0Executor(project=project, llm=llm_provider)
        result = mode0.run(
            Path(request.file_path),
            headless=True,
            self_heal=request.self_heal,
            quality_check=request.quality_check
        )
        
        return {
            "status": "success",
            "dataset_shape": [result.dataset_fingerprint.n_rows, result.dataset_fingerprint.n_cols],
            "quality_issues": len(result.risks),
            "memory_usage_mb": result.dataset_fingerprint.memory_usage_mb,
            "artifact_id": result.artifact_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/business-intelligence")
async def business_intelligence(request: BusinessKPIRequest):
    """Run Mode 1: Decision Intelligence"""
    try:
        mode1 = Mode1Executor(project=project, llm=llm_provider)
        result = mode1.run(
            business_kpi=request.business_kpi,
            hypotheses=request.hypotheses,
            verdict="go",
            headless=True
        )
        
        return {
            "status": "success", 
            "kpi": result.kpi_trace.business_kpi,
            "hypotheses_count": len(result.hypotheses),
            "gate_verdict": result.gate_verdict,
            "artifact_id": result.artifact_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/feasibility")
async def feasibility_check(request: FeasibilityRequest):
    """Run Mode 2: Feasibility Check"""
    try:
        mode2 = Mode2Executor(project=project, llm=llm_provider)
        result = mode2.run(
            data_path=Path(request.data_path),
            target_col=request.target_col,
            split=request.split,
            headless=True
        )
        
        return {
            "status": "success",
            "signal_present": result.signal_validation.signal_present,
            "lift": result.signal_validation.lift,
            "baseline_model": result.baseline_results.model_type,
            "gate_verdict": result.gate_verdict,
            "artifact_id": result.artifact_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/ml-strategy")
async def ml_strategy(request: MLStrategyRequest):
    """Run Mode 3: ML Strategy"""
    try:
        mode3 = Mode3Executor(project=project, llm=llm_provider)
        model_recs, feature_registry = mode3.run(
            data_path=Path(request.data_path),
            target_col=request.target_col,
            headless=True,
            self_heal=request.self_heal
        )
        
        return {
            "status": "success",
            "recommended_model": model_recs.recommended,
            "model_candidates": len(model_recs.candidates),
            "features_registered": len(feature_registry.features),
            "artifact_id": model_recs.artifact_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload a dataset file"""
    try:
        file_path = f"/data/{file.filename}"
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        return {"status": "success", "file_path": file_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/project/status")
async def project_status():
    """Get MERIDIAN project status"""
    return {
        "project_path": str(project.project_path),
        "meridian_version": project.meridian_version,
        "total_artifacts": len(list(project.artifact_store.glob("**/*.json"))),
        "self_healing_enabled": True
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
EOF

chmod +x meridian_api.py
```

### 7. Verification and Testing

```bash
# Test the deployment
curl -X GET http://meridian-service:8080/health

# Upload a test dataset
curl -X POST http://meridian-service:8080/api/v1/upload \\
     -F "file=@sample_data.csv"

# Run data analysis
curl -X POST http://meridian-service:8080/api/v1/data-analysis \\
     -H "Content-Type: application/json" \\
     -d '{
       "file_path": "/data/sample_data.csv",
       "self_heal": true,
       "quality_check": true
     }'
```

## Usage Examples

### Python Client

```python
import requests
import json

# MERIDIAN API endpoint
api_url = "http://meridian-service:8080"

# 1. Upload dataset
with open("customer_data.csv", "rb") as f:
    response = requests.post(f"{api_url}/api/v1/upload", 
                           files={"file": f})
file_path = response.json()["file_path"]

# 2. Analyze data (Mode 0)
analysis = requests.post(f"{api_url}/api/v1/data-analysis", 
                        json={
                            "file_path": file_path,
                            "self_heal": True,
                            "quality_check": True
                        }).json()

# 3. Define business context (Mode 1)  
business = requests.post(f"{api_url}/api/v1/business-intelligence",
                        json={
                            "business_kpi": "Reduce customer churn by 15%",
                            "hypotheses": [
                                "Account balance predicts churn",
                                "Transaction frequency matters",
                                "Geographic location affects retention"
                            ]
                        }).json()

# 4. Check feasibility (Mode 2)
feasibility = requests.post(f"{api_url}/api/v1/feasibility",
                           json={
                               "data_path": file_path,
                               "target_col": "churn",
                               "split": "stratified"
                           }).json()

print(f"Signal detected: {feasibility['signal_present']}")
print(f"Model lift: {feasibility['lift']:.3f}")
```

## Performance Tuning

### Spark Configuration

```yaml
# Add to meridian.yaml for high-performance workloads
spark:
  executor_memory: "16g"
  executor_cores: 8
  num_executors: 20
  driver_memory: "8g"
  
  # Performance optimizations
  sql.adaptive.enabled: true
  sql.adaptive.coalescePartitions.enabled: true
  serializer: "org.apache.spark.serializer.KryoSerializer"
  
  # GPU acceleration (if available)
  plugins: "com.nvidia.spark.SQLPlugin"
  rapids.sql.enabled: true
```

### SGLang Model Server Scaling

```bash
# Scale SGLang deployment for higher throughput
kubectl scale deployment sglang-server --replicas=4

# Add load balancer configuration
kubectl patch service sglang-service -p '{"spec":{"sessionAffinity":"ClientIP"}}'
```

## Monitoring and Logging

### Prometheus Metrics

```yaml
# Add to Kubernetes deployment
annotations:
  prometheus.io/scrape: "true"
  prometheus.io/port: "8080"
  prometheus.io/path: "/metrics"
```

### Log Aggregation

```bash
# Configure log forwarding to central system
kubectl create configmap fluentd-config --from-file=fluent.conf

# fluent.conf content:
<source>
  @type kubernetes_logs
  path /var/log/containers/meridian*.log
  tag kubernetes.meridian.*
</source>

<match kubernetes.meridian.**>
  @type forward
  host log-aggregator.company.com
  port 24224
</match>
```

## Security Considerations

### Network Policies

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: meridian-network-policy
spec:
  podSelector:
    matchLabels:
      app: meridian-driver
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: data-science
    ports:
    - protocol: TCP
      port: 8080
```

### Resource Limits

```yaml
resources:
  requests:
    memory: "4Gi"
    cpu: "2"
    nvidia.com/gpu: "0"  # CPU-only for API server
  limits:
    memory: "16Gi"
    cpu: "8"
```

## Troubleshooting

### Common Issues

1. **SGLang Connection Failed**
   ```bash
   kubectl logs deployment/sglang-server
   kubectl get events --field-selector involvedObject.name=sglang-server
   ```

2. **Spark Driver OOM**
   ```bash
   # Increase driver memory in meridian.yaml
   spark:
     driver_memory: "16g"
     driver_maxResultSize: "4g"
   ```

3. **Self-Healing Budget Exceeded**
   ```bash
   # Check circuit breaker status
   curl http://meridian-service:8080/api/v1/project/status
   
   # Reset if needed
   kubectl delete pod -l app=meridian-driver
   ```

## Next Steps

1. **Data Integration**: Connect to your data sources (HDFS, S3, databases)
2. **Model Registry**: Set up MLflow or similar for model versioning
3. **CI/CD Pipeline**: Integrate with GitOps for automated deployments
4. **Scaling**: Add horizontal pod autoscaling based on workload

---

🚀 **Your MERIDIAN framework is now production-ready on DGX Spark!**

The self-healing ML pipeline will automatically handle data quality issues, provide intelligent recommendations, and scale with your workload demands.

For support or questions, refer to the MERIDIAN documentation or contact your platform team.