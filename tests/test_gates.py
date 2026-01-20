from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from meridian.core.fingerprint import FingerprintStore
from meridian.core.gates import GateEnforcer, GateVerdict
from meridian.core.modes import Mode


@dataclass
class _FakeArtifact:
    ok: bool = True

    def validates(self) -> bool:
        return self.ok


class _FakeProject:
    def __init__(self, db_path: Path):
        self._complete: set[Mode] = set()
        self._verdicts: dict[Mode, GateVerdict] = {}
        self._artifacts: dict[str, object] = {}
        self.fingerprint_store = FingerprintStore(db_path)

    def is_mode_complete(self, mode: Mode) -> bool:
        return mode in self._complete

    def get_gate_verdict(self, mode: Mode) -> Optional[GateVerdict]:
        return self._verdicts.get(mode)

    def get_artifact(self, artifact_type: str):
        return self._artifacts.get(artifact_type)


def test_entry_mode_always_allowed(tmp_path: Path):
    p = _FakeProject(tmp_path / "fp.db")
    g = GateEnforcer(p)
    assert g.can_enter_mode(Mode.MODE_0).allowed is True
    assert g.can_enter_mode(Mode.MODE_0_5).allowed is True


def test_blocked_without_predecessor_complete(tmp_path: Path):
    p = _FakeProject(tmp_path / "fp.db")
    g = GateEnforcer(p)
    r = g.can_enter_mode(Mode.MODE_2)
    assert r.allowed is False


def test_blocked_without_required_artifact(tmp_path: Path):
    p = _FakeProject(tmp_path / "fp.db")
    p._complete.add(Mode.MODE_0)
    p._verdicts[Mode.MODE_0] = GateVerdict.GO
    g = GateEnforcer(p)
    r = g.can_enter_mode(Mode.MODE_1)
    assert r.allowed is False


def test_blocked_with_no_go_verdict(tmp_path: Path):
    p = _FakeProject(tmp_path / "fp.db")
    p._complete.add(Mode.MODE_0)
    p._verdicts[Mode.MODE_0] = GateVerdict.NO_GO
    p._artifacts["Mode0GatePacket"] = _FakeArtifact(ok=True)
    g = GateEnforcer(p)
    r = g.can_enter_mode(Mode.MODE_1)
    assert r.allowed is False
    assert r.override_permitted is True


def test_blocked_verdict_cannot_override(tmp_path: Path):
    p = _FakeProject(tmp_path / "fp.db")
    p._complete.add(Mode.MODE_0)
    p._verdicts[Mode.MODE_0] = GateVerdict.BLOCKED
    p._artifacts["Mode0GatePacket"] = _FakeArtifact(ok=True)
    g = GateEnforcer(p)
    r = g.can_enter_mode(Mode.MODE_1)
    assert r.allowed is False
    assert r.override_permitted is False


def test_conditional_verdict_allows_with_warning(tmp_path: Path):
    p = _FakeProject(tmp_path / "fp.db")
    p._complete.add(Mode.MODE_0)
    p._verdicts[Mode.MODE_0] = GateVerdict.CONDITIONAL
    p._artifacts["Mode0GatePacket"] = _FakeArtifact(ok=True)
    g = GateEnforcer(p)
    r = g.can_enter_mode(Mode.MODE_1)
    assert r.allowed is True
    assert r.verdict == GateVerdict.CONDITIONAL


def test_go_verdict_allows(tmp_path: Path):
    p = _FakeProject(tmp_path / "fp.db")
    p._complete.add(Mode.MODE_0)
    p._verdicts[Mode.MODE_0] = GateVerdict.GO
    p._artifacts["Mode0GatePacket"] = _FakeArtifact(ok=True)
    g = GateEnforcer(p)
    r = g.can_enter_mode(Mode.MODE_1)
    assert r.allowed is True


def test_override_logged_to_store(tmp_path: Path):
    p = _FakeProject(tmp_path / "fp.db")
    g = GateEnforcer(p)
    g.log_override(Mode.MODE_2, "proceed anyway", "fp123")
    rows = p.fingerprint_store.list_overrides()
    assert any(r["mode"] == "2" and r["reason"] == "proceed anyway" and r["fingerprint_id"] == "fp123" for r in rows)

