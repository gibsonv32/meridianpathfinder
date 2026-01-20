from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

import yaml


def _read_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def _write_yaml(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def find_project_config(start: Optional[Path] = None) -> Optional[Path]:
    """Find nearest project-level `meridian.yaml` by walking up directories."""
    cur = (start or Path.cwd()).resolve()
    for candidate in [cur, *cur.parents]:
        path = candidate / "meridian.yaml"
        if path.exists():
            return path
    return None


def global_config_path() -> Path:
    """Default global config path (per build plan)."""
    return Path.home() / ".meridian-global" / "config.yaml"


def load_config() -> Dict[str, Any]:
    """Load config with precedence: project meridian.yaml > global config.yaml > defaults."""
    cfg: Dict[str, Any] = {}

    global_path = global_config_path()
    cfg.update(_read_yaml(global_path))

    project_path = find_project_config()
    if project_path:
        # merge shallowly; project overrides global
        project_cfg = _read_yaml(project_path)
        cfg.update(project_cfg)

    return cfg


def save_project_llm_config(
    provider: Optional[str] = None, model: Optional[str] = None, start: Optional[Path] = None
) -> Path:
    """Update project `meridian.yaml` (create in cwd if missing)."""
    path = find_project_config(start=start)
    if path is None:
        path = (start or Path.cwd()).resolve() / "meridian.yaml"
    cfg = _read_yaml(path)
    llm = cfg.get("llm")
    if not isinstance(llm, dict):
        llm = {}
    if provider is not None:
        llm["provider"] = provider
    if model is not None:
        llm["model"] = model
    cfg["llm"] = llm
    _write_yaml(path, cfg)
    return path

