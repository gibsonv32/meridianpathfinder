"""MERIDIAN REST API Server using FastAPI with WebSocket support"""

import os
import signal
import logging
import json
import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from dataclasses import dataclass, field

from fastapi import FastAPI, HTTPException, BackgroundTasks, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
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


# WebSocket Connection Manager
class ConnectionManager:
    """Manages WebSocket connections for real-time updates"""
    
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self._lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        async with self._lock:
            self.active_connections.add(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")
    
    async def disconnect(self, websocket: WebSocket):
        async with self._lock:
            self.active_connections.discard(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")
    
    async def broadcast(self, event_type: str, payload: dict):
        """Broadcast event to all connected clients"""
        message = {
            "type": event_type,
            "payload": payload,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        message_json = json.dumps(message, default=str)
        
        disconnected = set()
        async with self._lock:
            for connection in self.active_connections:
                try:
                    await connection.send_text(message_json)
                except Exception as e:
                    logger.warning(f"Failed to send to websocket: {e}")
                    disconnected.add(connection)
            
            # Clean up disconnected
            self.active_connections -= disconnected
    
    async def send_to(self, websocket: WebSocket, event_type: str, payload: dict):
        """Send event to specific client"""
        message = {
            "type": event_type,
            "payload": payload,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        await websocket.send_text(json.dumps(message, default=str))


# Global connection manager
ws_manager = ConnectionManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting MERIDIAN API server with WebSocket support")
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


# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await ws_manager.connect(websocket)
    
    try:
        # Connection established - no need to send a message
        # Connection status is already shown in the dashboard header
        
        # Listen for incoming messages
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                await handle_ws_message(websocket, message)
            except json.JSONDecodeError:
                await ws_manager.send_to(websocket, "error", {
                    "message": "Invalid JSON"
                })
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await ws_manager.disconnect(websocket)


async def handle_ws_message(websocket: WebSocket, message: dict):
    """Handle incoming WebSocket messages"""
    msg_type = message.get("type")
    payload = message.get("payload", {})
    
    if msg_type == "ping":
        await ws_manager.send_to(websocket, "pong", {"time": datetime.now(timezone.utc).isoformat()})
    
    elif msg_type == "subscribe":
        # Subscribe to project updates
        project_path = payload.get("project_path")
        if project_path:
            await ws_manager.send_to(websocket, "subscribed", {
                "project_path": project_path
            })
    
    elif msg_type == "run_mode":
        # Trigger mode execution via WebSocket
        project_path = payload.get("project_path")
        mode_id = payload.get("mode")
        params = payload.get("params", {})
        
        if project_path and mode_id:
            # Start mode execution in background
            asyncio.create_task(
                execute_mode_with_updates(project_path, mode_id, params)
            )
            await ws_manager.send_to(websocket, "mode_update", {
                "modeId": mode_id,
                "status": "queued",
                "message": f"Mode {mode_id} execution queued"
            })
    
    elif msg_type == "command":
        # Handle slash commands from dashboard
        command = payload.get("command")
        args = payload.get("args", {})
        await handle_command(websocket, command, args)


async def handle_command(websocket: WebSocket, command: str, args: dict):
    """Handle slash commands from the dashboard"""
    project_path = args.get("project_path", os.getcwd())
    
    if command == "status":
        try:
            project = MeridianProject.load(Path(project_path))
            modes_status = []
            for mode in Mode:
                ms = project.state.mode_states[mode]
                modes_status.append({
                    "id": mode.value,
                    "status": ms.status,
                    "verdict": ms.gate_verdict.value if ms.gate_verdict else None,
                    "artifactCount": len(ms.artifact_ids) if ms.artifact_ids else 0
                })
            
            await ws_manager.send_to(websocket, "status_response", {
                "project_name": project.state.project_name,
                "modes": modes_status
            })
        except Exception as e:
            await ws_manager.send_to(websocket, "error", {
                "message": f"Failed to get status: {str(e)}"
            })
    
    elif command == "artifacts":
        try:
            project = MeridianProject.load(Path(project_path))
            artifacts = []
            
            if project.artifact_store.exists():
                for p in project.artifact_store.rglob("*.json"):
                    try:
                        data = json.loads(p.read_text())
                        artifacts.append({
                            "id": data.get("artifact_id", ""),
                            "type": data.get("artifact_type", ""),
                            "modeId": p.parent.name.replace("mode_", "").replace("_", "."),
                            "createdAt": data.get("created_at", ""),
                            "name": data.get("artifact_type", "Unknown")
                        })
                    except:
                        pass
            
            await ws_manager.send_to(websocket, "artifacts_response", {
                "artifacts": artifacts
            })
        except Exception as e:
            await ws_manager.send_to(websocket, "error", {
                "message": f"Failed to list artifacts: {str(e)}"
            })
    
    elif command.startswith("mode"):
        # Run a specific mode
        mode_id = args.get("mode") or command.replace("mode", "").strip()
        if mode_id:
            asyncio.create_task(
                execute_mode_with_updates(project_path, mode_id, args)
            )
    
    else:
        await ws_manager.send_to(websocket, "error", {
            "message": f"Unknown command: {command}"
        })


async def execute_mode_with_updates(project_path: str, mode_id: str, params: dict):
    """Execute a mode and broadcast updates via WebSocket"""
    try:
        # Broadcast mode started
        await ws_manager.broadcast("mode_update", {
            "modeId": mode_id,
            "status": "running",
            "message": f"Starting Mode {mode_id}..."
        })
        
        # Load project
        project = MeridianProject.load(Path(project_path))
        
        # Get the mode executor
        mode_enum = Mode(mode_id)
        
        # Import and run the mode
        from meridian.modes import get_mode_runner
        runner = get_mode_runner(mode_enum)
        
        # Execute mode
        headless = params.get("headless", False)
        result = await asyncio.to_thread(
            runner.run,
            project=project,
            headless=headless,
            **{k: v for k, v in params.items() if k != "headless"}
        )
        
        # Broadcast success
        await ws_manager.broadcast("mode_update", {
            "modeId": mode_id,
            "status": "completed",
            "verdict": result.verdict.value if hasattr(result, 'verdict') else "go",
            "message": f"Mode {mode_id} completed successfully"
        })
        
        # If artifacts were created, broadcast them
        if hasattr(result, 'artifact_ids'):
            for artifact_id in result.artifact_ids:
                await ws_manager.broadcast("artifact_created", {
                    "id": artifact_id,
                    "modeId": mode_id,
                    "type": "artifact"
                })
        
    except Exception as e:
        logger.error(f"Mode {mode_id} execution failed: {e}")
        await ws_manager.broadcast("mode_update", {
            "modeId": mode_id,
            "status": "failed",
            "message": f"Mode {mode_id} failed: {str(e)}"
        })
        await ws_manager.broadcast("error", {
            "message": str(e),
            "severity": "error"
        })


# Additional REST endpoints for dashboard

@app.get("/projects")
def list_projects():
    """List available MERIDIAN projects"""
    # Check common locations for projects
    projects = []
    cwd = Path.cwd()
    
    # Check if current directory is a project
    if (cwd / ".meridian").exists():
        try:
            project = MeridianProject.load(cwd)
            projects.append({
                "name": project.state.project_name,
                "path": str(cwd),
                "created_at": project.state.created_at.isoformat() if project.state.created_at else None
            })
        except:
            pass
    
    return {"projects": projects}


@app.get("/modes")
def list_modes(project_path: str):
    """Get all modes with their current status"""
    try:
        project = MeridianProject.load(Path(project_path))
        
        modes = []
        for mode in Mode:
            ms = project.state.mode_states[mode]
            modes.append({
                "id": mode.value,
                "name": get_mode_name(mode),
                "status": ms.status,
                "verdict": ms.gate_verdict.value if ms.gate_verdict else None,
                "artifactCount": len(ms.artifact_ids) if ms.artifact_ids else 0,
                "startedAt": ms.started_at.isoformat() if ms.started_at else None,
                "completedAt": ms.completed_at.isoformat() if ms.completed_at else None
            })
        
        return {"modes": modes}
    except Exception as e:
        raise HTTPException(404, str(e))


@app.get("/artifacts/{artifact_id}/download")
def download_artifact(project_path: str, artifact_id: str):
    """Download artifact as JSON file"""
    try:
        project = MeridianProject.load(Path(project_path))
        
        for p in project.artifact_store.rglob(f"*{artifact_id}*.json"):
            return FileResponse(
                path=p,
                filename=p.name,
                media_type="application/json"
            )
        
        raise HTTPException(404, f"Artifact not found: {artifact_id}")
    except Exception as e:
        raise HTTPException(404, str(e))


@app.get("/deliverables")
def list_deliverables(project_path: str):
    """List generated deliverables"""
    try:
        project = MeridianProject.load(Path(project_path))
        deliverables_path = project.project_path / ".meridian" / "deliverables"
        
        deliverables = []
        if deliverables_path.exists():
            for p in deliverables_path.glob("*"):
                if p.is_file():
                    deliverables.append({
                        "name": p.name,
                        "path": str(p),
                        "size": p.stat().st_size,
                        "modified_at": datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc).isoformat()
                    })
        
        return {"deliverables": deliverables}
    except Exception as e:
        raise HTTPException(404, str(e))


@app.get("/deliverables/{filename}")
def get_deliverable(project_path: str, filename: str):
    """Get deliverable content"""
    try:
        project = MeridianProject.load(Path(project_path))
        deliverable_path = project.project_path / ".meridian" / "deliverables" / filename
        
        if not deliverable_path.exists():
            raise HTTPException(404, f"Deliverable not found: {filename}")
        
        return {
            "name": filename,
            "content": deliverable_path.read_text()
        }
    except Exception as e:
        raise HTTPException(404, str(e))


def get_mode_name(mode: Mode) -> str:
    """Get human-readable mode name"""
    names = {
        Mode.MODE_0_5: "Opportunity Discovery",
        Mode.MODE_0: "Data Fingerprint",
        Mode.MODE_1: "Decision Intelligence",
        Mode.MODE_2: "Feasibility Assessment",
        Mode.MODE_3: "Feature Engineering",
        Mode.MODE_4: "Business Case",
        Mode.MODE_5: "Code Generation",
        Mode.MODE_6: "Execution & Testing",
        Mode.MODE_6_5: "Interpretation",
        Mode.MODE_7: "Delivery"
    }
    return names.get(mode, f"Mode {mode.value}")


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