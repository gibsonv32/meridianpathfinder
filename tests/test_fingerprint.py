from __future__ import annotations

from pathlib import Path

import pytest

from meridian.core.fingerprint import (
    ArtifactFingerprint,
    FingerprintStore,
    compute_sha256,
    generate_fingerprint,
)


def test_fingerprint_auto_populates_system_fields(tmp_path: Path):
    fp = generate_fingerprint(
        artifact_type="Mode0GatePacket",
        content=b'{"x":1}',
        parent_ids=[],
        mode="mode_0",
        input_paths=[],
        config_path=None,
        created_by="tester",
        execution_duration_ms=12,
        meridian_version="0.1.0",
    )
    assert fp.artifact_id
    assert fp.hostname
    assert fp.python_version
    assert fp.created_at is not None
    assert fp.content_hash == compute_sha256(b'{"x":1}')


def test_fingerprint_immutable():
    fp = ArtifactFingerprint(
        artifact_type="X",
        schema_version="2.3.1",
        parent_artifacts=[],
        mode="mode_0",
        mode_version="1.0.0",
        created_by="tester",
        execution_duration_ms=1,
        input_hash=compute_sha256(b""),
        config_hash=compute_sha256(b""),
        content_hash=compute_sha256(b"abc"),
        meridian_version="0.1.0",
        gpu_available=False,
    )
    with pytest.raises(Exception):
        fp.artifact_type = "Y"  # type: ignore[misc]


def test_content_hash_changes_with_content():
    fp1 = generate_fingerprint("T", b"a", [], "mode_0", meridian_version="0.1.0")
    fp2 = generate_fingerprint("T", b"b", [], "mode_0", meridian_version="0.1.0")
    assert fp1.content_hash != fp2.content_hash


def test_store_save_and_retrieve(tmp_path: Path):
    store = FingerprintStore(tmp_path / "fingerprints.db")
    fp = generate_fingerprint("T", b"a", [], "mode_0", meridian_version="0.1.0")
    store.save(fp)
    got = store.get(fp.artifact_id)
    assert got is not None
    assert got.artifact_id == fp.artifact_id


def test_verify_unchanged_artifact_returns_true(tmp_path: Path):
    store = FingerprintStore(tmp_path / "fingerprints.db")
    content = b"hello"
    fp = generate_fingerprint("T", content, [], "mode_0", meridian_version="0.1.0")
    store.save(fp)
    assert store.verify(fp.artifact_id, content) is True


def test_verify_tampered_artifact_returns_false(tmp_path: Path):
    store = FingerprintStore(tmp_path / "fingerprints.db")
    fp = generate_fingerprint("T", b"hello", [], "mode_0", meridian_version="0.1.0")
    store.save(fp)
    assert store.verify(fp.artifact_id, b"tampered") is False


def test_lineage_returns_ancestors(tmp_path: Path):
    store = FingerprintStore(tmp_path / "fingerprints.db")
    parent = generate_fingerprint("Parent", b"p", [], "mode_0", meridian_version="0.1.0")
    store.save(parent)
    child = generate_fingerprint("Child", b"c", [parent.artifact_id], "mode_1", meridian_version="0.1.0")
    store.save(child)

    lineage = store.get_lineage(child.artifact_id, depth=3)
    assert len(lineage) >= 1
    assert lineage[0].artifact_id == parent.artifact_id

