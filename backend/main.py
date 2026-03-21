from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routers import audit, documents, health, igce, packages, pws, rules
from backend.phase2.router_phase2 import router as phase2_router
from backend.core.audit.middleware import AuditMiddleware
from backend.database.db import init_database


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await init_database()
    yield


app = FastAPI(title="FedProcure", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:3001", "http://127.0.0.1:3001", "http://localhost:3002", "http://127.0.0.1:3002", "http://192.168.68.74:3002"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(AuditMiddleware)
app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(rules.router, prefix="/api/v1")
app.include_router(packages.router, prefix="/api/v1")
app.include_router(pws.router, prefix="/api/v1")
app.include_router(igce.router, prefix="/api/v1")
app.include_router(documents.router, prefix="/api/v1")
app.include_router(audit.router, prefix="/api/v1")
app.include_router(phase2_router, prefix="/api/v1")

