"""MERIDIAN REST API Server using FastAPI"""

import os
import signal
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

from meridian.core.state import MeridianProject
from meridian.core.modes import Mode
from meridian.llm.providers import get_provider
from meridian.config import load_config

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting MERIDIAN API server")
    yield
    # Shutdown
    logger.info("Shutting down MERIDIAN API server")

app = FastAPI(
    title="MERIDIAN API",
    description="ML Pipeline Orchestration API",
    version="0.1.0",
    lifespan=lifespan
)

# Enable CORS for web frontends (restrict for production)
allowed_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:8080").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins if os.getenv("ENV") == "production" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = datetime.now()
    response = await call_next(request)
    process_time = (datetime.now() - start_time).total_seconds()
    logger.info(
        f"{request.method} {request.url.path} - {response.status_code} - {process_time:.3f}s"
    )
    return response


# Request/Response Models
class ProjectInitRequest(BaseModel):
    path: str = Field(..., description="Project directory path")
    name: str = Field(..., description="Project name")
    force: bool = Field(False, description="Overwrite existing project")


class ModeRunRequest(BaseModel):
    mode: str = Field(..., description="Mode to run (e.g., '0', '2', '6.5')")
    params: Dict[str, Any] = Field({}, description="Mode-specific parameters")
    headless: bool = Field(False, description="Skip LLM calls")


class ProjectStatus(BaseModel):
    project_name: str
    path: str
    current_mode: Optional[str]
    modes: List[Dict[str, Any]]


class ArtifactInfo(BaseModel):
    artifact_id: str
    artifact_type: str
    mode: str
    created_at: datetime
    verified: bool


# API Endpoints
@app.get("/")
def root():
    """API health check"""
    return {"status": "ok", "service": "MERIDIAN API"}


@app.post("/project/init")
def init_project(request: ProjectInitRequest):
    """Initialize a new MERIDIAN project"""
    try:
        from meridian.core.state import MeridianProject
        
        project_path = Path(request.path)
        if project_path.exists() and not request.force:
            raise HTTPException(400, "Project already exists. Use force=true to overwrite.")
        
        # Create project
        config = {
            "llm": {
                "provider": "anthropic",
                "model": "claude-3-haiku-20240307"
            }
        }
        
        project = MeridianProject.create(
            path=project_path,
            name=request.name,
            config=config
        )
        
        return {
            "status": "success",
            "project_name": request.name,
            "path": str(project_path)
        }
        
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/project/status")
def get_status(project_path: str) -> ProjectStatus:
    """Get current project status"""
    try:
        project = MeridianProject.load(Path(project_path))
        
        modes = []
        for mode in Mode:
            ms = project.state.mode_states[mode]
            modes.append({
                "mode": mode.value,
                "status": ms.status,
                "verdict": ms.gate_verdict.value if ms.gate_verdict else None,
                "artifacts": ms.artifact_ids or []
            })
        
        return ProjectStatus(
            project_name=project.state.project_name,
            path=str(project.project_path),
            current_mode=project.state.current_mode.value if project.state.current_mode else None,
            modes=modes
        )
        
    except Exception as e:
        raise HTTPException(404, f"Project not found: {str(e)}")


@app.post("/mode/run")
async def run_mode(request: ModeRunRequest, background_tasks: BackgroundTasks):
    """Execute a specific mode"""
    try:
        # This would typically be run as a background task
        # For now, returning immediate acknowledgment
        
        mode_value = request.mode.replace(".", "_")
        
        # Queue the mode execution
        background_tasks.add_task(
            execute_mode_async,
            mode_value,
            request.params,
            request.headless
        )
        
        return {
            "status": "queued",
            "mode": request.mode,
            "message": f"Mode {request.mode} execution queued"
        }
        
    except Exception as e:
        raise HTTPException(400, str(e))


@app.get("/artifacts/list")
def list_artifacts(
    project_path: str,
    artifact_type: Optional[str] = None,
    mode: Optional[str] = None,
    latest_only: bool = False
) -> List[ArtifactInfo]:
    """List project artifacts"""
    try:
        project = MeridianProject.load(Path(project_path))
        
        artifacts = []
        if project.artifact_store.exists():
            for p in project.artifact_store.rglob("*.json"):
                # Parse artifact info from filename and content
                import json
                data = json.loads(p.read_text())
                
                # Apply filters
                if artifact_type and data.get("artifact_type") != artifact_type:
                    continue
                if mode and not str(p.parent.name).endswith(mode.replace(".", "_")):
                    continue
                
                artifacts.append(ArtifactInfo(
                    artifact_id=data.get("artifact_id", ""),
                    artifact_type=data.get("artifact_type", ""),
                    mode=p.parent.name.replace("mode_", "").replace("_", "."),
                    created_at=datetime.fromisoformat(data.get("created_at", "")),
                    verified=False  # Would check fingerprint here
                ))
        
        # Sort by creation time
        artifacts.sort(key=lambda x: x.created_at, reverse=True)
        
        if latest_only:
            # Keep only latest per type
            seen_types = set()
            filtered = []
            for a in artifacts:
                if a.artifact_type not in seen_types:
                    filtered.append(a)
                    seen_types.add(a.artifact_type)
            artifacts = filtered
        
        return artifacts
        
    except Exception as e:
        raise HTTPException(404, str(e))


@app.get("/artifacts/{artifact_id}")
def get_artifact(project_path: str, artifact_id: str):
    """Get specific artifact content"""
    try:
        project = MeridianProject.load(Path(project_path))
        
        # Find artifact file
        for p in project.artifact_store.rglob(f"*{artifact_id}*.json"):
            import json
            return json.loads(p.read_text())
        
        raise HTTPException(404, f"Artifact not found: {artifact_id}")
        
    except Exception as e:
        raise HTTPException(404, str(e))


@app.post("/demo")
def run_demo(
    project_path: str,
    data_path: str,
    target_col: str,
    prediction_row: Dict[str, float]
):
    """Run the demo pipeline"""
    import subprocess
    import json
    
    try:
        project = MeridianProject.load(Path(project_path))
        
        # Run PROJECT/demo.py
        demo_script = project.project_path / "PROJECT" / "demo.py"
        if not demo_script.exists():
            raise HTTPException(404, "Demo script not found. Run mode 5 first.")
        
        cmd = [
            "python", str(demo_script),
            "--data", data_path,
            "--target", target_col,
            "--row", json.dumps(prediction_row)
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=project.project_path
        )
        
        if result.returncode != 0:
            raise HTTPException(500, f"Demo failed: {result.stderr}")
        
        # Parse output
        output_lines = result.stdout.split("\n")
        train_output = {}
        predict_output = {}
        
        for i, line in enumerate(output_lines):
            if line.startswith("TRAIN:"):
                # Parse JSON from next lines
                j = i + 1
                json_str = ""
                while j < len(output_lines) and not output_lines[j].startswith("PREDICT:"):
                    json_str += output_lines[j]
                    j += 1
                train_output = json.loads(json_str) if json_str else {}
            elif line.startswith("PREDICT:"):
                # Parse JSON from remaining lines
                json_str = "\n".join(output_lines[i+1:])
                predict_output = json.loads(json_str) if json_str else {}
        
        return {
            "status": "success",
            "train": train_output,
            "prediction": predict_output
        }
        
    except Exception as e:
        raise HTTPException(500, str(e))


# Async helper functions
async def execute_mode_async(mode: str, params: dict, headless: bool):
    """Execute mode in background (placeholder for actual implementation)"""
    # This would integrate with the actual mode executors
    # For now, it's a placeholder
    pass


# CLI to start server
def start_server(host: str = None, port: int = None):
    """Start the API server with environment variable support"""
    host = host or os.getenv("API_HOST", "127.0.0.1")  # Default to localhost for security
    port = port or int(os.getenv("API_PORT", "8000"))
    
    # Handle graceful shutdown
    def handle_shutdown(signum, frame):
        logger.info("Received shutdown signal, cleaning up...")
        raise KeyboardInterrupt
    
    signal.signal(signal.SIGTERM, handle_shutdown)
    signal.signal(signal.SIGINT, handle_shutdown)
    
    logger.info(f"Starting server on {host}:{port}")
    uvicorn.run(
        app, 
        host=host, 
        port=port,
        log_level=os.getenv("LOG_LEVEL", "info").lower(),
        access_log=True
    )


if __name__ == "__main__":
    start_server()