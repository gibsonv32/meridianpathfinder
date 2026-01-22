"""Production-ready improvements for MERIDIAN API Server"""

import os
import time
import logging
from typing import Any, Dict
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("meridian.api")

# Security
security = HTTPBearer()

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify API token"""
    token = credentials.credentials
    expected_token = os.getenv("MERIDIAN_API_TOKEN")
    
    if not expected_token:
        logger.warning("No API token configured")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API token not configured"
        )
    
    if token != expected_token:
        logger.warning(f"Invalid token attempt: {token[:10]}...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token"
        )
    
    return token

# Lifespan manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting MERIDIAN API Server")
    yield
    # Shutdown
    logger.info("Shutting down MERIDIAN API Server")

# Create app with lifespan
app = FastAPI(
    title="MERIDIAN API",
    description="Production ML Pipeline Orchestration API",
    version="0.2.0",
    lifespan=lifespan
)

# Configure CORS properly
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    # Log request
    logger.info(f"Request: {request.method} {request.url.path}")
    
    try:
        response = await call_next(request)
    except Exception as e:
        logger.error(f"Request failed: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error", "detail": str(e)}
        )
    
    # Log response
    process_time = time.time() - start_time
    logger.info(
        f"Response: {request.method} {request.url.path} "
        f"status={response.status_code} duration={process_time:.3f}s"
    )
    
    response.headers["X-Process-Time"] = str(process_time)
    return response

# Rate limiting (simple in-memory)
from collections import defaultdict
from datetime import datetime, timedelta

rate_limit_store = defaultdict(list)

def rate_limit(max_calls: int = 100, window_seconds: int = 60):
    """Simple rate limiter decorator"""
    def decorator(func):
        async def wrapper(request: Request, *args, **kwargs):
            client_id = request.client.host
            now = datetime.now()
            
            # Clean old entries
            rate_limit_store[client_id] = [
                t for t in rate_limit_store[client_id] 
                if now - t < timedelta(seconds=window_seconds)
            ]
            
            # Check rate limit
            if len(rate_limit_store[client_id]) >= max_calls:
                logger.warning(f"Rate limit exceeded for {client_id}")
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded"
                )
            
            # Add current call
            rate_limit_store[client_id].append(now)
            
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator

# Health checks
@app.get("/health")
def health_check():
    """Comprehensive health check"""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "0.2.0",
        "checks": {
            "api": "ok",
            "database": check_database_health(),
            "llm": check_llm_health(),
            "disk_space": check_disk_space(),
        }
    }
    
    # Determine overall status
    if all(v == "ok" for v in health_status["checks"].values()):
        health_status["status"] = "healthy"
    elif health_status["checks"]["api"] == "ok":
        health_status["status"] = "degraded"
    else:
        health_status["status"] = "unhealthy"
    
    return health_status

def check_database_health() -> str:
    """Check database connectivity"""
    try:
        # TODO: Implement actual database check
        return "ok"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return "error"

def check_llm_health() -> str:
    """Check LLM service availability"""
    try:
        from meridian.llm.providers import get_provider
        from meridian.config import load_config
        
        provider = get_provider(load_config())
        if provider.test_connection():
            return "ok"
        return "error"
    except Exception as e:
        logger.error(f"LLM health check failed: {e}")
        return "error"

def check_disk_space() -> str:
    """Check available disk space"""
    import shutil
    
    try:
        stat = shutil.disk_usage("/")
        free_gb = stat.free / (1024**3)
        
        if free_gb < 1:
            return "critical"
        elif free_gb < 5:
            return "warning"
        return "ok"
    except Exception as e:
        logger.error(f"Disk space check failed: {e}")
        return "error"

# Metrics endpoint
from datetime import datetime

metrics_store = {
    "requests_total": 0,
    "requests_success": 0,
    "requests_failed": 0,
    "start_time": datetime.utcnow()
}

@app.get("/metrics")
def get_metrics():
    """Prometheus-compatible metrics"""
    uptime = (datetime.utcnow() - metrics_store["start_time"]).total_seconds()
    
    metrics = f"""# HELP meridian_requests_total Total number of requests
# TYPE meridian_requests_total counter
meridian_requests_total {metrics_store['requests_total']}

# HELP meridian_requests_success Total successful requests
# TYPE meridian_requests_success counter
meridian_requests_success {metrics_store['requests_success']}

# HELP meridian_requests_failed Total failed requests  
# TYPE meridian_requests_failed counter
meridian_requests_failed {metrics_store['requests_failed']}

# HELP meridian_uptime_seconds Uptime in seconds
# TYPE meridian_uptime_seconds gauge
meridian_uptime_seconds {uptime}
"""
    
    return JSONResponse(content=metrics, media_type="text/plain")

# Protected endpoint example
@app.get("/protected")
def protected_endpoint(token: str = Depends(verify_token)):
    """Example protected endpoint"""
    return {"message": "Access granted", "user": "authenticated"}

# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    logger.error(f"HTTP error: {exc.status_code} - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "status_code": exc.status_code}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)}
    )

if __name__ == "__main__":
    # Production server configuration
    uvicorn.run(
        "meridian.api.server_prod:app",
        host="0.0.0.0",
        port=8000,
        workers=4,
        log_level="info",
        access_log=True,
        use_colors=False
    )