from __future__ import annotations

import json
import socket
import sqlite3
import sys
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import List, Optional
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class ArtifactFingerprint(BaseModel):
    """System-owned, auto-generated provenance record."""

    model_config = ConfigDict(frozen=True)

    # Identity
    artifact_id: str = Field(default_factory=lambda: str(uuid4()))
    artifact_type: str
    schema_version: str

    # Lineage
    parent_artifacts: List[str] = Field(default_factory=list)
    mode: str
    mode_version: str

    # Provenance
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: str
    execution_duration_ms: int

    # Integrity
    input_hash: str
    config_hash: str
    content_hash: str

    # Environment
    hostname: str = Field(default_factory=socket.gethostname)
    python_version: str = Field(default_factory=lambda: sys.version)
    meridian_version: str
    gpu_available: bool = False


def compute_sha256(data: bytes) -> str:
    return sha256(data).hexdigest()


def _canonicalize_artifact_bytes(data: bytes) -> bytes:
    """
    Canonicalize JSON artifact bytes for hashing.

    Per MERIDIAN spec, artifact integrity should be computed from the artifact
    content excluding fingerprint linkage fields (e.g., fingerprint_id).
    """
    try:
        obj = json.loads(data.decode("utf-8"))
    except Exception:
        return data

    if isinstance(obj, dict):
        obj.pop("fingerprint_id", None)
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")


def compute_file_hash(path: Path) -> str:
    return compute_sha256(path.read_bytes())


def _detect_gpu_available() -> bool:
    # Best-effort: should never raise.
    try:
        import torch  # type: ignore

        return bool(getattr(torch, "cuda", None) and torch.cuda.is_available())
    except Exception:
        pass
    try:
        import tensorflow as tf  # type: ignore

        return bool(tf.config.list_physical_devices("GPU"))
    except Exception:
        return False


def generate_fingerprint(
    artifact_type: str,
    content: bytes,
    parent_ids: List[str],
    mode: str,
    input_paths: Optional[List[Path]] = None,
    config_path: Optional[Path] = None,
    *,
    artifact_id: Optional[str] = None,
    schema_version: str = "2.3.1",
    mode_version: str = "1.0.0",
    created_by: str = "meridian-cli:0.1.0",
    execution_duration_ms: int = 0,
    meridian_version: str = "0.1.0",
) -> ArtifactFingerprint:
    input_paths = input_paths or []
    # Stable hashing: sort by path string
    input_hash = compute_sha256(
        b"".join([compute_file_hash(p).encode("utf-8") for p in sorted(input_paths, key=lambda x: str(x))])
    )
    config_hash = compute_file_hash(config_path) if config_path and config_path.exists() else compute_sha256(b"")
    content_hash = compute_sha256(_canonicalize_artifact_bytes(content))

    return ArtifactFingerprint(
        artifact_id=artifact_id or str(uuid4()),
        artifact_type=artifact_type,
        schema_version=schema_version,
        parent_artifacts=parent_ids,
        mode=mode,
        mode_version=mode_version,
        created_by=created_by,
        execution_duration_ms=execution_duration_ms,
        input_hash=input_hash,
        config_hash=config_hash,
        content_hash=content_hash,
        meridian_version=meridian_version,
        gpu_available=_detect_gpu_available(),
    )


class FingerprintStore:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS artifacts(
                  artifact_id TEXT PRIMARY KEY,
                  artifact_type TEXT NOT NULL,
                  mode TEXT NOT NULL,
                  created_at TEXT NOT NULL,
                  content_hash TEXT NOT NULL,
                  fingerprint_json TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS lineage(
                  child_id TEXT NOT NULL,
                  parent_id TEXT NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_lineage_child ON lineage(child_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_lineage_parent ON lineage(parent_id)")

    def save(self, fingerprint: ArtifactFingerprint) -> None:
        # Use Pydantic JSON mode so datetimes/UUIDs serialize correctly.
        payload = json.loads(fingerprint.model_dump_json())
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO artifacts(
                  artifact_id, artifact_type, mode, created_at, content_hash, fingerprint_json
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    fingerprint.artifact_id,
                    fingerprint.artifact_type,
                    fingerprint.mode,
                    fingerprint.created_at.isoformat(),
                    fingerprint.content_hash,
                    json.dumps(payload, separators=(",", ":"), sort_keys=True),
                ),
            )
            conn.execute("DELETE FROM lineage WHERE child_id = ?", (fingerprint.artifact_id,))
            for parent in fingerprint.parent_artifacts:
                conn.execute(
                    "INSERT INTO lineage(child_id, parent_id) VALUES (?, ?)",
                    (fingerprint.artifact_id, parent),
                )

    def get(self, artifact_id: str) -> Optional[ArtifactFingerprint]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT fingerprint_json FROM artifacts WHERE artifact_id = ?", (artifact_id,)
            ).fetchone()
            if not row:
                return None
            return ArtifactFingerprint.model_validate_json(row["fingerprint_json"])

    def verify(self, artifact_id: str, current_content: bytes) -> bool:
        fp = self.get(artifact_id)
        if not fp:
            return False
        return fp.content_hash == compute_sha256(_canonicalize_artifact_bytes(current_content))

    def get_lineage(self, artifact_id: str, depth: int = 10) -> List[ArtifactFingerprint]:
        """Return ancestor fingerprints up to `depth`."""
        out: List[ArtifactFingerprint] = []
        current_ids = [artifact_id]
        seen: set[str] = set()

        with self._connect() as conn:
            for _ in range(depth):
                next_ids: list[str] = []
                for cid in current_ids:
                    if cid in seen:
                        continue
                    seen.add(cid)
                    parents = conn.execute("SELECT parent_id FROM lineage WHERE child_id = ?", (cid,)).fetchall()
                    for p in parents:
                        pid = p["parent_id"]
                        next_ids.append(pid)
                if not next_ids:
                    break
                for nid in next_ids:
                    fp = self.get(nid)
                    if fp:
                        out.append(fp)
                current_ids = next_ids

        return out

    def list_all(self) -> List[ArtifactFingerprint]:
        with self._connect() as conn:
            rows = conn.execute("SELECT fingerprint_json FROM artifacts ORDER BY created_at DESC").fetchall()
            return [ArtifactFingerprint.model_validate_json(r["fingerprint_json"]) for r in rows]

    def log_override(self, *, mode: str, reason: str, fingerprint_id: str) -> None:
        """Append an override record to the fingerprint DB (best-effort audit trail)."""
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS overrides(
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  created_at TEXT NOT NULL,
                  mode TEXT NOT NULL,
                  reason TEXT NOT NULL,
                  fingerprint_id TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "INSERT INTO overrides(created_at, mode, reason, fingerprint_id) VALUES (?, ?, ?, ?)",
                (datetime.now(timezone.utc).isoformat(), mode, reason, fingerprint_id),
            )

    def list_overrides(self) -> list[dict]:
        with self._connect() as conn:
            try:
                rows = conn.execute("SELECT created_at, mode, reason, fingerprint_id FROM overrides").fetchall()
            except sqlite3.OperationalError:
                return []
            return [dict(r) for r in rows]

