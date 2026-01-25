from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import typer

from meridian import __version__
from meridian.config import load_config, save_project_llm_config
from meridian.llm.providers import get_provider
from meridian.skills.loader import SkillLoader
from meridian.core.modes import Mode

app = typer.Typer(add_completion=False, no_args_is_help=True)


def _cli_error(message: str, *, code: int = 2) -> None:
    typer.secho(message, fg=typer.colors.RED, err=True)
    raise typer.Exit(code=code)


def _handle_mode_error(exc: Exception) -> None:
    msg = str(exc).strip()
    if isinstance(exc, RuntimeError) and msg.startswith("Gate blocked:"):
        _cli_error(f"{msg}\nTip: run `meridian status` to see what’s missing.", code=2)
    if isinstance(exc, FileNotFoundError):
        _cli_error(f"{msg}", code=2)
    if isinstance(exc, ValueError):
        _cli_error(f"{msg}", code=2)
    raise exc


def _parse_mode_sort_key(m: Mode) -> float:
    try:
        return float(m.value)
    except Exception:
        return 999.0


def _format_dt(s: Any) -> str:
    if not s:
        return "-"
    if isinstance(s, datetime):
        return s.isoformat()
    return str(s)


def _read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _artifact_mode_dir(path: Path) -> str:
    # Expected under .meridian/artifacts/<mode_dir>/ArtifactType_<id>.json
    try:
        return path.parent.name
    except Exception:
        return "-"


def _normalize_mode_filter(s: str) -> str:
    s = s.strip()
    if s.startswith("mode_"):
        return s
    return "mode_" + s.replace(".", "_")


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(__version__)
        raise typer.Exit(code=0)


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        help="Show MERIDIAN version and exit.",
        callback=_version_callback,
        is_eager=True,
    ),
) -> None:
    """MERIDIAN CLI (scaffold)."""


@app.command()
def init(
    project_name: str = typer.Option(None, "--name", help="Project name (defaults to directory name)"),
    force: bool = typer.Option(False, "--force", help="Overwrite existing configuration"),
) -> None:
    """Initialize a new MERIDIAN project with configuration and directory structure."""
    from meridian.core.state import MeridianProject, ProjectState, ModeState
    from meridian.core.modes import Mode
    from meridian.config import _write_yaml
    from datetime import datetime, timezone
    from hashlib import sha256
    
    cwd = Path.cwd()
    
    # Check if already initialized
    meridian_dir = cwd / ".meridian"
    config_file = cwd / "meridian.yaml"
    
    if not force:
        if meridian_dir.exists():
            _cli_error("Project already initialized. Use --force to reinitialize.", code=2)
        if config_file.exists():
            _cli_error("meridian.yaml already exists. Use --force to overwrite.", code=2)
    
    # Determine project name
    if not project_name:
        project_name = cwd.name
    
    # Create directory structure
    typer.echo(f"Initializing MERIDIAN project: {project_name}")
    
    # Create .meridian directories
    (meridian_dir / "artifacts").mkdir(parents=True, exist_ok=True)
    (meridian_dir / "deliverables").mkdir(parents=True, exist_ok=True)
    typer.echo("✓ Created .meridian/ directory structure")
    
    # Create default meridian.yaml configuration
    default_config = {
        "project": {
            "name": project_name,
            "version": "0.1.0",
            "description": f"MERIDIAN project: {project_name}",
        },
        "llm": {
            "provider": "anthropic",
            "model": "claude-3-haiku-20240307",
            "temperature": 0.3,
            "max_tokens": 4096,
        },
        "data": {
            "default_path": "data/",
            "cache_enabled": True,
        },
        "artifacts": {
            "retention_days": 30,
            "auto_verify": True,
        },
        "execution": {
            "parallel_enabled": False,
            "timeout_seconds": 3600,
        },
    }
    
    _write_yaml(config_file, default_config)
    typer.echo("✓ Created meridian.yaml configuration")
    
    # Initialize state.json
    if not (meridian_dir / "state.json").exists() or force:
        # Compute config hash
        cfg_bytes = config_file.read_bytes() if config_file.exists() else b""
        cfg_hash = sha256(cfg_bytes).hexdigest()
        
        # Create mode states for all modes
        mode_states = {m: ModeState(mode=m, status="not_started", artifact_ids=[]) for m in Mode}
        
        # Create project state
        state = ProjectState(
            project_name=project_name,
            created_at=datetime.now(timezone.utc),
            current_mode=None,
            mode_states=mode_states,
            config_hash=cfg_hash,
        )
        
        # Save state
        state_path = meridian_dir / "state.json"
        state_path.write_text(state.model_dump_json(indent=2), encoding="utf-8")
        typer.echo("✓ Initialized project state")
    
    # Create sample data directory
    (cwd / "data").mkdir(exist_ok=True)
    typer.echo("✓ Created data/ directory")
    
    # Create .gitignore if not exists
    gitignore_path = cwd / ".gitignore"
    if not gitignore_path.exists():
        gitignore_content = """# MERIDIAN project files
.meridian/artifacts/
.meridian/deliverables/
.meridian/fingerprints.db
.meridian/state.json

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
.venv/
venv/
ENV/

# IDE
.vscode/
.idea/
*.swp
*.swo
.DS_Store

# Data files
*.csv
*.parquet
*.json
!meridian.yaml
!pyproject.toml

# ML artifacts
*.joblib
*.pkl
*.h5
*.pt
*.pth
models/
checkpoints/
"""
        gitignore_path.write_text(gitignore_content)
        typer.echo("✓ Created .gitignore")
    
    typer.echo("")
    typer.secho(f"Successfully initialized MERIDIAN project: {project_name}", fg=typer.colors.GREEN)
    typer.echo("")
    typer.echo("Next steps:")
    typer.echo("1. Review and customize meridian.yaml configuration")
    typer.echo("2. Set up your LLM provider credentials (see: meridian llm --help)")
    typer.echo("3. Place your data files in the data/ directory")
    typer.echo("4. Run 'meridian status' to verify setup")
    typer.echo("5. Start with Mode 0.5: 'meridian mode 0.5 run --help'")


@app.command()
def status() -> None:
    """Show current project status."""
    from meridian.core.state import MeridianProject

    try:
        project = MeridianProject.load(Path.cwd())
    except Exception as e:
        _cli_error(f"Not a MERIDIAN project here.\n{e}", code=2)

    typer.echo(f"project: {project.state.project_name}")
    typer.echo(f"path: {project.project_path}")
    typer.echo(f"current_mode: {project.state.current_mode.value if project.state.current_mode else '-'}")
    typer.echo("")
    typer.echo("modes:")
    for m in sorted(list(Mode), key=_parse_mode_sort_key):
        ms = project.state.mode_states[m]
        artifacts = ", ".join(ms.artifact_ids or [])
        typer.echo(
            f"- {m.value:>3}  status={ms.status:<11}  verdict={(ms.gate_verdict.value if ms.gate_verdict else '-'):>11}  "
            f"started={_format_dt(ms.started_at)}  completed={_format_dt(ms.completed_at)}  artifacts=[{artifacts}]"
        )


@app.command()
def demo(
    data: Path = typer.Option(..., "--data", exists=True, dir_okay=False, help="Path to CSV dataset"),
    target: str = typer.Option(..., "--target", help="Target column name"),
    row: str = typer.Option(..., "--row", help="JSON string for prediction row (e.g., '{\"x1\":0.1,\"x2\":-0.2}')"),
    verify: bool = typer.Option(False, "--verify", help="Verify artifact fingerprints"),
) -> None:
    """Run a single-command demo: status + artifacts + PROJECT/demo.py execution."""
    import subprocess
    from meridian.core.state import MeridianProject
    
    try:
        project = MeridianProject.load(Path.cwd())
    except Exception as e:
        _cli_error(f"Not a MERIDIAN project here.\n{e}", code=2)
    
    # 1. Print status
    typer.echo("=" * 60)
    typer.echo("MERIDIAN STATUS")
    typer.echo("=" * 60)
    typer.echo(f"project: {project.state.project_name}")
    typer.echo(f"path: {project.project_path}")
    typer.echo(f"current_mode: {project.state.current_mode.value if project.state.current_mode else '-'}")
    typer.echo("")
    typer.echo("modes:")
    for m in sorted(list(Mode), key=_parse_mode_sort_key):
        ms = project.state.mode_states[m]
        artifacts = ", ".join(ms.artifact_ids or [])
        typer.echo(
            f"- {m.value:>3}  status={ms.status:<11}  verdict={(ms.gate_verdict.value if ms.gate_verdict else '-'):>11}  "
            f"artifacts=[{artifacts}]"
        )
    
    # 2. Print latest artifacts summary
    typer.echo("")
    typer.echo("=" * 60)
    typer.echo("LATEST ARTIFACTS")
    typer.echo("=" * 60)
    
    if project.artifact_store.exists():
        seen: set[str] = set()
        artifacts: list[tuple[float, Path, dict[str, Any]]] = []
        
        for p in project.artifact_store.rglob("*.json"):
            data_dict = _read_json(p)
            at = str(data_dict.get("artifact_type") or "")
            if at and at not in seen:
                seen.add(at)
                artifacts.append((p.stat().st_mtime, p, data_dict))
        
        artifacts.sort(key=lambda t: t[0], reverse=True)
        
        for _, p, data_dict in artifacts[:10]:  # Show up to 10 latest artifacts
            at = str(data_dict.get("artifact_type") or "-")
            aid = str(data_dict.get("artifact_id") or p.stem.split("_")[-1])
            created = str(data_dict.get("created_at") or "-")
            fp_id = data_dict.get("fingerprint_id")
            ok = "-"
            if verify and fp_id:
                try:
                    ok = "ok" if project.fingerprint_store.verify(str(fp_id), p.read_bytes()) else "bad"
                except Exception:
                    ok = "?"
            typer.echo(f"{_artifact_mode_dir(p)}\t{at}\t{aid[:8]}...\tfp={ok}")
    else:
        typer.echo("(no artifacts)")
    
    # 3. Run PROJECT/demo.py
    typer.echo("")
    typer.echo("=" * 60)
    typer.echo("PROJECT DEMO EXECUTION")
    typer.echo("=" * 60)
    
    demo_script = project.project_path / "PROJECT" / "demo.py"
    if not demo_script.exists():
        _cli_error(f"Demo script not found: {demo_script}", code=2)
    
    cmd = [
        "python", str(demo_script),
        "--data", str(data),
        "--target", target,
        "--row", row
    ]
    
    typer.echo(f"Running: {' '.join(cmd)}")
    typer.echo("")
    
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=project.project_path)
    
    if result.stdout:
        typer.echo(result.stdout)
    if result.stderr:
        typer.secho(result.stderr, fg=typer.colors.YELLOW, err=True)
    
    if result.returncode != 0:
        _cli_error(f"Demo script failed with exit code {result.returncode}", code=3)
    
    # 4. Print deliverables summary
    typer.echo("")
    typer.echo("=" * 60)
    typer.echo("DELIVERABLES")
    typer.echo("=" * 60)
    
    deliverables_dir = project.project_path / ".meridian" / "deliverables"
    if deliverables_dir.exists():
        for p in sorted(deliverables_dir.glob("*")):
            typer.echo(f"- {p.name}: {p}")
    else:
        typer.echo("(no deliverables)")
    
    # 5. Show latest DeliveryManifest if exists
    latest_manifest = project.get_artifact("DeliveryManifest")
    if latest_manifest:
        typer.echo("")
        typer.echo("Latest DeliveryManifest: " + str(latest_manifest))


mode_app = typer.Typer(add_completion=False, no_args_is_help=True)
artifacts_app = typer.Typer(add_completion=False, no_args_is_help=True)
llm_app = typer.Typer(add_completion=False, no_args_is_help=True)
skills_app = typer.Typer(add_completion=False, no_args_is_help=True)
mode0_5_app = typer.Typer(add_completion=False, no_args_is_help=True)
mode0_app = typer.Typer(add_completion=False, no_args_is_help=True)
mode1_app = typer.Typer(add_completion=False, no_args_is_help=True)
mode2_app = typer.Typer(add_completion=False, no_args_is_help=True)
mode3_app = typer.Typer(add_completion=False, no_args_is_help=True)
mode4_app = typer.Typer(add_completion=False, no_args_is_help=True)
mode5_app = typer.Typer(add_completion=False, no_args_is_help=True)
mode6_app = typer.Typer(add_completion=False, no_args_is_help=True)
mode6_5_app = typer.Typer(add_completion=False, no_args_is_help=True)
mode7_app = typer.Typer(add_completion=False, no_args_is_help=True)


@mode_app.command("list")
def mode_list() -> None:
    """List modes and their status."""
    from meridian.core.state import MeridianProject

    try:
        project = MeridianProject.load(Path.cwd())
    except Exception as e:
        _cli_error(f"Not a MERIDIAN project here.\n{e}", code=2)

    for m in sorted(list(Mode), key=_parse_mode_sort_key):
        ms = project.state.mode_states[m]
        typer.echo(f"{m.value}\t{ms.status}\t{ms.gate_verdict.value if ms.gate_verdict else '-'}")


@artifacts_app.command("list")
def artifacts_list(
    artifact_type: Optional[str] = typer.Option(None, "--type", help="Filter by artifact type (e.g., FeasibilityReport)"),
    mode: Optional[str] = typer.Option(None, "--mode", help="Filter by mode (e.g., 2, 0.5, 6.5, mode_3)"),
    limit: int = typer.Option(50, "--limit", min=1, max=500, help="Max rows to show"),
    latest_per_type: bool = typer.Option(False, "--latest-per-type", help="Show only newest artifact per type"),
    verify: bool = typer.Option(False, "--verify", help="Verify fingerprints while listing (slower)"),
) -> None:
    """List artifacts for the current project."""
    from meridian.core.state import MeridianProject

    try:
        project = MeridianProject.load(Path.cwd())
    except Exception as e:
        _cli_error(f"Not a MERIDIAN project here.\n{e}", code=2)

    if not project.artifact_store.exists():
        typer.echo("(no artifacts)")
        raise typer.Exit(code=0)

    mode_filter = _normalize_mode_filter(mode) if mode else None

    rows: list[tuple[float, Path, dict[str, Any]]] = []
    for p in project.artifact_store.rglob("*.json"):
        if mode_filter and _artifact_mode_dir(p) != mode_filter:
            continue
        data = _read_json(p)
        at = data.get("artifact_type") or ""
        if artifact_type and at != artifact_type:
            continue
        rows.append((p.stat().st_mtime, p, data))

    rows.sort(key=lambda t: t[0], reverse=True)

    if latest_per_type:
        seen: set[str] = set()
        filtered: list[tuple[float, Path, dict[str, Any]]] = []
        for mtime, p, data in rows:
            at = str(data.get("artifact_type") or "")
            if not at or at in seen:
                continue
            seen.add(at)
            filtered.append((mtime, p, data))
        rows = filtered

    rows = rows[:limit]
    if not rows:
        typer.echo("(no matching artifacts)")
        raise typer.Exit(code=0)

    for _, p, data in rows:
        at = str(data.get("artifact_type") or "-")
        aid = str(data.get("artifact_id") or p.stem.split("_")[-1])
        created = str(data.get("created_at") or "-")
        fp_id = data.get("fingerprint_id")
        ok = "-"
        if verify and fp_id:
            try:
                ok = "ok" if project.fingerprint_store.verify(str(fp_id), p.read_bytes()) else "bad"
            except Exception:
                ok = "?"
        typer.echo(f"{_artifact_mode_dir(p)}\t{at}\t{aid}\tcreated={created}\tfp={ok}\t{p}")


@artifacts_app.command("show")
def artifacts_show(
    artifact_id: Optional[str] = typer.Option(None, "--id", help="Artifact id (UUID)"),
    artifact_type: Optional[str] = typer.Option(None, "--type", help="Artifact type (shows latest by default)"),
    file: Optional[Path] = typer.Option(None, "--file", exists=True, dir_okay=False, help="Path to a specific artifact JSON"),
    latest: bool = typer.Option(True, "--latest/--no-latest", help="For --type, show latest artifact"),
    verify: bool = typer.Option(True, "--verify/--no-verify", help="Verify fingerprint before printing"),
) -> None:
    """Show an artifact JSON by id/type/path (supports latest shortcut)."""
    from meridian.core.state import MeridianProject

    try:
        project = MeridianProject.load(Path.cwd())
    except Exception as e:
        _cli_error(f"Not a MERIDIAN project here.\n{e}", code=2)

    target: Optional[Path] = None
    if file is not None:
        target = file
    elif artifact_id:
        if not project.artifact_store.exists():
            _cli_error("No artifacts directory found.", code=2)
        matches = [p for p in project.artifact_store.rglob("*.json") if artifact_id in p.name]
        if not matches:
            _cli_error(f"Artifact id not found: {artifact_id}", code=2)
        target = sorted(matches, key=lambda p: p.stat().st_mtime, reverse=True)[0]
    elif artifact_type:
        target = project.get_artifact(artifact_type) if latest else project.get_artifact(artifact_type)
        if not target:
            _cli_error(f"No artifact found for type: {artifact_type}", code=2)
    else:
        _cli_error("Provide one of: --file, --id, or --type.", code=2)

    data = _read_json(target)
    fp_id = data.get("fingerprint_id")
    if verify and fp_id:
        ok = project.fingerprint_store.verify(str(fp_id), target.read_bytes())
        typer.echo(f"fingerprint: {'ok' if ok else 'BAD'} ({fp_id})")
    typer.echo(f"path: {target}")
    typer.echo(target.read_text(encoding="utf-8"))


@llm_app.command("status")
def llm_status() -> None:
    """Show LLM provider, model, and connectivity status."""
    cfg = load_config()
    provider = get_provider(cfg)
    ok = provider.test_connection()
    typer.echo(f"provider: {cfg.get('llm', {}).get('provider', 'anthropic')}")
    typer.echo(f"model: {provider.model_name}")
    typer.echo(f"connection: {'ok' if ok else 'failed'}")


@llm_app.command("enable-intelligence")
def llm_enable_intelligence(
    memory: bool = typer.Option(True, "--memory/--no-memory", help="Enable conversation memory"),
    few_shot: bool = typer.Option(True, "--few-shot/--no-few-shot", help="Enable few-shot learning"),
    optimization: bool = typer.Option(True, "--optimize/--no-optimize", help="Enable prompt optimization"),
) -> None:
    """Enable enhanced LLM intelligence features."""
    from meridian.config import load_config, save_config
    
    try:
        config = load_config()
        
        # Add intelligence configuration
        if "llm" not in config:
            config["llm"] = {}
        
        config["llm"]["intelligence"] = {
            "enabled": True,
            "memory": memory,
            "few_shot": few_shot,
            "optimization": optimization
        }
        
        save_config(config)
        
        typer.secho("✓ Enhanced LLM intelligence enabled!", fg=typer.colors.GREEN)
        typer.echo(f"  Memory: {'✓' if memory else '✗'}")
        typer.echo(f"  Few-shot learning: {'✓' if few_shot else '✗'}")
        typer.echo(f"  Prompt optimization: {'✓' if optimization else '✗'}")
        
    except Exception as e:
        _cli_error(f"Failed to enable intelligence: {e}", code=2)


@llm_app.command("intelligence-report")
def llm_intelligence_report() -> None:
    """Show LLM intelligence performance report."""
    from meridian.config import load_config
    from meridian.llm.providers import get_provider
    from pathlib import Path
    import json
    
    try:
        config = load_config()
        provider = get_provider(config, Path.cwd())
        
        # Check if enhanced provider
        if not hasattr(provider, 'get_performance_report'):
            typer.echo("Enhanced intelligence not enabled. Run: meridian llm enable-intelligence")
            return
        
        report = provider.get_performance_report()
        
        typer.echo("\n=== LLM INTELLIGENCE REPORT ===")
        typer.echo(f"Memory turns: {report.get('memory_turns', 0)}")
        typer.echo(f"Few-shot examples: {report.get('few_shot_examples', 0)}")
        
        if "prompt_optimization" in report:
            typer.echo("\nPrompt Optimization Performance:")
            for mode, data in report["prompt_optimization"].items():
                typer.echo(f"\n  Mode {mode}:")
                for item in data[:3]:  # Top 3
                    typer.echo(f"    Success rate: {item['success_rate']:.2%}")
                    typer.echo(f"    Avg quality: {item['avg_quality']:.2f}")
                    typer.echo(f"    Uses: {item['total_uses']}")
                    typer.echo()
    
    except Exception as e:
        _cli_error(f"Failed to generate report: {e}", code=2)


@llm_app.command("test")
def llm_test() -> None:
    """Test LLM connectivity."""
    cfg = load_config()
    provider = get_provider(cfg)
    ok = provider.test_connection()
    if ok:
        typer.echo("OK")
        raise typer.Exit(code=0)
    typer.echo("FAILED")
    raise typer.Exit(code=3)


@llm_app.command("set-provider")
def llm_set_provider(name: str = typer.Argument(..., help="Provider name: anthropic|ollama")) -> None:
    """Set the default LLM provider (project meridian.yaml)."""
    path = save_project_llm_config(provider=name)
    typer.echo(f"updated: {path}")


@llm_app.command("set-model")
def llm_set_model(name: str = typer.Argument(..., help="Model identifier")) -> None:
    """Set the default LLM model (project meridian.yaml)."""
    path = save_project_llm_config(model=name)
    typer.echo(f"updated: {path}")


api_app = typer.Typer(add_completion=False, no_args_is_help=True)
backup_app = typer.Typer(add_completion=False, no_args_is_help=True)
data_app = typer.Typer(add_completion=False, no_args_is_help=True)

app.add_typer(mode_app, name="mode", help="Mode-related commands.")
app.add_typer(artifacts_app, name="artifacts", help="Artifact-related commands.")
app.add_typer(llm_app, name="llm", help="LLM-related commands.")
app.add_typer(skills_app, name="skills", help="Skill-related commands.")
app.add_typer(api_app, name="api", help="API server commands.")
app.add_typer(backup_app, name="backup", help="Backup and restore commands.")
app.add_typer(data_app, name="data", help="Data quality and preprocessing commands.")

# ML app for AutoML commands
ml_app = typer.Typer(add_completion=False, no_args_is_help=True)
app.add_typer(ml_app, name="ml", help="Machine learning and AutoML commands.")

# Mode subcommands
mode_app.add_typer(mode0_5_app, name="0.5", help="Mode 0.5 (Opportunity Discovery).")
mode_app.add_typer(mode0_app, name="0", help="Mode 0 (EDA).")
mode_app.add_typer(mode1_app, name="1", help="Mode 1 (Decision Intelligence).")
mode_app.add_typer(mode2_app, name="2", help="Mode 2 (Feasibility).")
mode_app.add_typer(mode3_app, name="3", help="Mode 3 (Strategy).")
mode_app.add_typer(mode4_app, name="4", help="Mode 4 (Business Case).")
mode_app.add_typer(mode5_app, name="5", help="Mode 5 (Code Generation Plan).")
mode_app.add_typer(mode6_app, name="6", help="Mode 6 (Execution / Ops).")
mode_app.add_typer(mode6_5_app, name="6.5", help="Mode 6.5 (Interpreter).")
mode_app.add_typer(mode7_app, name="7", help="Mode 7 (Delivery).")
@mode0_5_app.command("run")
def mode0_5_run(
    problem: str = typer.Option(..., "--problem", help="Business problem statement"),
    target_entity: str = typer.Option("customer", "--target-entity", help="Target entity (e.g., customer, order, claim)"),
    candidate: list[str] = typer.Option(
        [],
        "--candidate",
        help="Candidate opportunity in format 'type:description' (repeatable). Type is optional.",
    ),
    select_id: Optional[str] = typer.Option(None, "--select", help="Pick a specific opportunity id from the backlog"),
    stakeholder_brief: str = typer.Option("", "--stakeholder-brief", help="Short stakeholder summary"),
    data_requirement: list[str] = typer.Option([], "--data-requirement", help="Data requirement (repeatable)"),
    headless: bool = typer.Option(False, "--headless", help="Skip LLM enrichment"),
) -> None:
    """Execute Mode 0.5 (Opportunity Discovery) and write OpportunityBacklog + OpportunityBrief artifacts."""
    from meridian.core.state import MeridianProject
    from meridian.llm.providers import get_provider
    from meridian.modes.mode_0_5 import Mode0_5Executor

    try:
        project = MeridianProject.load(Path.cwd())
        llm = None if headless else get_provider(load_config())
        ex = Mode0_5Executor(project=project, llm=llm)
        backlog, brief = ex.run(
            problem_statement=problem,
            target_entity=target_entity,
            candidates=candidate,
            select_id=select_id,
            stakeholder_brief=stakeholder_brief,
            data_requirements=data_requirement,
            headless=headless,
        )
        typer.echo(brief.artifact_id)
    except Exception as e:
        _handle_mode_error(e)



@mode0_app.command("run")
def mode0_run(
    data: Path = typer.Option(..., "--data", exists=True, dir_okay=False, help="Path to CSV dataset"),
    headless: bool = typer.Option(False, "--headless", help="Skip LLM narrative generation"),
) -> None:
    """Execute Mode 0 (EDA) and write Mode0GatePacket artifact."""
    from meridian.core.state import MeridianProject
    from meridian.llm.providers import get_provider
    from meridian.modes.mode_0 import Mode0Executor

    try:
        project = MeridianProject.load(Path.cwd())
        llm = None if headless else get_provider(load_config())
        exec0 = Mode0Executor(project=project, llm=llm)
        artifact = exec0.run(data_path=data, headless=headless)
        typer.echo(artifact.artifact_id)
    except Exception as e:
        _handle_mode_error(e)


@mode1_app.command("run")
def mode1_run(
    business_kpi: str = typer.Option(..., "--business-kpi", help="Business KPI objective"),
    hypothesis: list[str] = typer.Option(..., "--hypothesis", help="Hypothesis statement (repeatable)", min=2),
    verdict: str = typer.Option("go", "--verdict", help="go|conditional|no_go|blocked"),
    headless: bool = typer.Option(False, "--headless", help="Skip LLM enrichment"),
) -> None:
    """Execute Mode 1 (Decision Intelligence) and write DecisionIntelProfile artifact."""
    from meridian.core.gates import GateVerdict
    from meridian.core.state import MeridianProject
    from meridian.llm.providers import get_provider
    from meridian.modes.mode_1 import Mode1Executor

    try:
        project = MeridianProject.load(Path.cwd())
        llm = None if headless else get_provider(load_config())
        exec1 = Mode1Executor(project=project, llm=llm)
        artifact = exec1.run(
            business_kpi=business_kpi,
            hypotheses=hypothesis,
            verdict=GateVerdict(verdict),
            headless=headless,
        )
        typer.echo(artifact.artifact_id)
    except Exception as e:
        _handle_mode_error(e)


@mode2_app.command("run")
def mode2_run(
    data: Path = typer.Option(..., "--data", exists=True, dir_okay=False, help="Path to CSV dataset"),
    target: str = typer.Option(..., "--target", help="Target column name"),
    split: str = typer.Option("stratified", "--split", help="stratified|random"),
    date_col: Optional[str] = typer.Option(None, "--date-col", help="Date column for temporal checks (optional)"),
    headless: bool = typer.Option(False, "--headless", help="Skip LLM interpretation"),
) -> None:
    """Execute Mode 2 (Feasibility) and write FeasibilityReport artifact."""
    from meridian.core.state import MeridianProject
    from meridian.llm.providers import get_provider
    from meridian.modes.mode_2 import Mode2Executor

    try:
        project = MeridianProject.load(Path.cwd())
        llm = None if headless else get_provider(load_config())
        exec2 = Mode2Executor(project=project, llm=llm)
        artifact = exec2.run(data_path=data, target_col=target, split=split, date_col=date_col, headless=headless)
        typer.echo(artifact.artifact_id)
    except Exception as e:
        _handle_mode_error(e)


@mode3_app.command("run")
def mode3_run(
    data: Path = typer.Option(..., "--data", exists=True, dir_okay=False, help="Path to CSV dataset"),
    target: str = typer.Option(..., "--target", help="Target column name"),
    headless: bool = typer.Option(False, "--headless", help="Skip LLM enrichment"),
) -> None:
    """Execute Mode 3 (Strategy) and write ModelRecommendations + FeatureRegistry artifacts."""
    from meridian.core.state import MeridianProject
    from meridian.llm.providers import get_provider
    from meridian.modes.mode_3 import Mode3Executor

    try:
        project = MeridianProject.load(Path.cwd())
        llm = None if headless else get_provider(load_config())
        exec3 = Mode3Executor(project=project, llm=llm)
        model_recs, feature_registry = exec3.run(data_path=data, target_col=target, headless=headless)
        typer.echo(model_recs.artifact_id)
    except Exception as e:
        _handle_mode_error(e)


@mode4_app.command("run")
def mode4_run(
    headless: bool = typer.Option(False, "--headless", help="Skip LLM enrichment"),
) -> None:
    """Execute Mode 4 (Business Case) and write BusinessCaseScorecard + ThresholdFramework artifacts."""
    from meridian.core.state import MeridianProject
    from meridian.llm.providers import get_provider
    from meridian.modes.mode_4 import Mode4Executor

    try:
        project = MeridianProject.load(Path.cwd())
        llm = None if headless else get_provider(load_config())
        exec4 = Mode4Executor(project=project, llm=llm)
        scorecard, tf = exec4.run(headless=headless)
        typer.echo(scorecard.artifact_id)
    except Exception as e:
        _handle_mode_error(e)


@mode5_app.command("run")
def mode5_run(
    output: Optional[Path] = typer.Option(None, "--output", dir_okay=True, help="Where to write PROJECT scaffold (default: ./PROJECT)"),
    headless: bool = typer.Option(False, "--headless", help="Skip LLM enrichment"),
) -> None:
    """Execute Mode 5 (Code Generation Plan) and write CodeGenerationPlan artifact + PROJECT scaffold."""
    from meridian.core.state import MeridianProject
    from meridian.llm.providers import get_provider
    from meridian.modes.mode_5 import Mode5Executor

    try:
        project = MeridianProject.load(Path.cwd())
        llm = None if headless else get_provider(load_config())
        exec5 = Mode5Executor(project=project, llm=llm)
        artifact = exec5.run(output_dir=output, headless=headless)
        typer.echo(artifact.artifact_id)
    except Exception as e:
        _handle_mode_error(e)


@mode6_app.command("run")
def mode6_run(
    project_dir: Optional[Path] = typer.Option(None, "--project", dir_okay=True, help="Path to generated PROJECT/ (default: CodeGenerationPlan.output_path)"),
    headless: bool = typer.Option(False, "--headless", help="Skip LLM enrichment"),
) -> None:
    """Execute Mode 6 (Execution/Ops) and write ExecutionOpsScorecard artifact."""
    from meridian.core.state import MeridianProject
    from meridian.llm.providers import get_provider
    from meridian.modes.mode_6 import Mode6Executor

    try:
        project = MeridianProject.load(Path.cwd())
        llm = None if headless else get_provider(load_config())
        exec6 = Mode6Executor(project=project, llm=llm)
        artifact = exec6.run(project_dir=project_dir, headless=headless)
        typer.echo(artifact.artifact_id)
    except Exception as e:
        _handle_mode_error(e)


@mode6_5_app.command("run")
def mode6_5_run(
    headless: bool = typer.Option(False, "--headless", help="Skip LLM enrichment"),
) -> None:
    """Execute Mode 6.5 (Interpreter) and write InterpretationPackage artifact."""
    from meridian.core.state import MeridianProject
    from meridian.llm.providers import get_provider
    from meridian.modes.mode_6_5 import Mode6_5Executor

    try:
        project = MeridianProject.load(Path.cwd())
        llm = None if headless else get_provider(load_config())
        exec65 = Mode6_5Executor(project=project, llm=llm)
        artifact = exec65.run(headless=headless)
        typer.echo(artifact.artifact_id)
    except Exception as e:
        _handle_mode_error(e)


@mode7_app.command("run")
def mode7_run(
    headless: bool = typer.Option(False, "--headless", help="Skip LLM enrichment"),
) -> None:
    """Execute Mode 7 (Delivery) and write DeliveryManifest artifact."""
    from meridian.core.state import MeridianProject
    from meridian.llm.providers import get_provider
    from meridian.modes.mode_7 import Mode7Executor

    try:
        project = MeridianProject.load(Path.cwd())
        llm = None if headless else get_provider(load_config())
        exec7 = Mode7Executor(project=project, llm=llm)
        artifact = exec7.run(headless=headless)
        typer.echo(artifact.artifact_id)
    except Exception as e:
        _handle_mode_error(e)


@skills_app.command("list")
def skills_list() -> None:
    """List available skill files."""
    loader = SkillLoader()
    for name in loader.list_skills():
        typer.echo(name)


@skills_app.command("show")
def skills_show(
    name: str = typer.Argument(..., help="Skill name (filename stem)"),
    mode: str = typer.Option(..., "--mode", help="Mode number, e.g. 0, 2, 6.5"),
) -> None:
    """Show skill sections aligned to a mode."""
    mode_enum = Mode(mode)
    loader = SkillLoader()
    typer.echo(loader.format_context(name, mode_enum))


@api_app.command("start")
def api_start(
    host: str = typer.Option(None, "--host", help="API server host (default: from env or 127.0.0.1)"),
    port: int = typer.Option(None, "--port", help="API server port (default: from env or 8000)"),
    reload: bool = typer.Option(False, "--reload", help="Enable auto-reload for development"),
    workers: int = typer.Option(1, "--workers", help="Number of worker processes"),
    timeout: int = typer.Option(300, "--timeout", help="Request timeout in seconds"),
) -> None:
    """Start the MERIDIAN REST API server with resource limits."""
    import os
    
    try:
        import uvicorn
    except ImportError:
        _cli_error("FastAPI dependencies not installed. Run: pip install fastapi uvicorn", code=2)
    
    # Set environment variables for timeout
    os.environ["REQUEST_TIMEOUT"] = str(timeout)
    
    # Use environment defaults if not specified
    actual_host = host or os.getenv("API_HOST", "127.0.0.1")
    actual_port = port or int(os.getenv("API_PORT", "8000"))
    
    typer.echo(f"Starting MERIDIAN API server on {actual_host}:{actual_port}")
    typer.echo(f"Workers: {workers}, Timeout: {timeout}s")
    typer.echo(f"Documentation will be available at http://{actual_host}:{actual_port}/docs")
    typer.echo("Press CTRL+C to stop the server")
    
    try:
        from meridian.api.server import app
        uvicorn.run(
            app, 
            host=actual_host, 
            port=actual_port, 
            reload=reload,
            workers=1 if reload else workers,
            timeout_keep_alive=timeout,
            log_level=os.getenv("LOG_LEVEL", "info").lower()
        )
    except ImportError:
        _cli_error("API server not found. Ensure meridian.api.server module exists.", code=2)
    except KeyboardInterrupt:
        typer.echo("\nShutting down API server...")
    except Exception as e:
        _cli_error(f"Failed to start API server: {e}", code=3)


@api_app.command("docs")
def api_docs(
    port: int = typer.Option(8000, "--port", help="API server port"),
) -> None:
    """Open API documentation in browser."""
    import webbrowser
    url = f"http://localhost:{port}/docs"
    typer.echo(f"Opening API documentation: {url}")
    webbrowser.open(url)


@backup_app.command("create")
def backup_create(
    name: Optional[str] = typer.Option(None, "--name", help="Backup name (default: timestamp)"),
    include_data: bool = typer.Option(False, "--include-data", help="Include data/ directory"),
    no_compress: bool = typer.Option(False, "--no-compress", help="Don't compress backup"),
    backup_dir: Optional[Path] = typer.Option(None, "--backup-dir", help="Backup directory"),
) -> None:
    """Create backup of MERIDIAN project."""
    from meridian.utils.backup import MeridianBackup
    
    try:
        backup_mgr = MeridianBackup(Path.cwd(), backup_dir)
        backup_file = backup_mgr.create_backup(
            name=name,
            include_data=include_data,
            compress=not no_compress
        )
        typer.secho(f"✓ Backup created: {backup_file}", fg=typer.colors.GREEN)
    except Exception as e:
        _cli_error(f"Backup failed: {e}", code=3)


@backup_app.command("restore")
def backup_restore(
    backup_file: Path = typer.Argument(..., help="Backup file to restore"),
    target: Optional[Path] = typer.Option(None, "--target", help="Target directory"),
    overwrite: bool = typer.Option(False, "--overwrite", help="Overwrite existing files"),
) -> None:
    """Restore backup to target directory."""
    from meridian.utils.backup import MeridianBackup
    
    try:
        backup_mgr = MeridianBackup(Path.cwd())
        restored_path = backup_mgr.restore_backup(
            backup_file=backup_file,
            target_path=target,
            overwrite=overwrite
        )
        typer.secho(f"✓ Backup restored to: {restored_path}", fg=typer.colors.GREEN)
    except Exception as e:
        _cli_error(f"Restore failed: {e}", code=3)


@backup_app.command("list")
def backup_list(
    backup_dir: Optional[Path] = typer.Option(None, "--backup-dir", help="Backup directory"),
) -> None:
    """List available backups."""
    from meridian.utils.backup import MeridianBackup
    
    try:
        backup_mgr = MeridianBackup(Path.cwd(), backup_dir)
        backups = backup_mgr.list_backups()
        
        if not backups:
            typer.echo("No backups found")
        else:
            typer.echo(f"Found {len(backups)} backup(s):\n")
            for backup in backups:
                typer.echo(f"  {backup['name']}")
                typer.echo(f"    Size: {backup['size']}")
                typer.echo(f"    Created: {backup['created']}")
                if backup.get('included_data'):
                    typer.echo(f"    Includes data: Yes")
                typer.echo()
    except Exception as e:
        _cli_error(f"List failed: {e}", code=3)


@backup_app.command("cleanup")
def backup_cleanup(
    keep: int = typer.Option(5, "--keep", help="Number of backups to keep"),
    backup_dir: Optional[Path] = typer.Option(None, "--backup-dir", help="Backup directory"),
) -> None:
    """Remove old backups, keeping only recent ones."""
    from meridian.utils.backup import MeridianBackup
    
    try:
        backup_mgr = MeridianBackup(Path.cwd(), backup_dir)
        deleted = backup_mgr.cleanup_old_backups(keep_count=keep)
        
        if deleted:
            typer.echo(f"Deleted {len(deleted)} old backup(s):")
            for file in deleted:
                typer.echo(f"  - {file.name}")
        else:
            typer.echo("No backups to clean up")
    except Exception as e:
        _cli_error(f"Cleanup failed: {e}", code=3)


# Data Quality Commands
@data_app.command("analyze")
def data_analyze(
    data_file: Path = typer.Argument(..., help="Path to data file"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output report path"),
    show_report: bool = typer.Option(True, "--show", help="Display report in terminal"),
) -> None:
    """Analyze data quality and generate comprehensive report."""
    from meridian.data.quality import DataQualityAnalyzer
    import pandas as pd
    import json
    
    try:
        # Load data
        df = pd.read_csv(data_file)
        typer.echo(f"Analyzing {data_file.name} ({len(df)} rows, {len(df.columns)} columns)...")
        
        # Analyze
        analyzer = DataQualityAnalyzer()
        report = analyzer.analyze(df, dataset_name=data_file.stem)
        
        # Save report
        if output:
            with open(output, "w") as f:
                json.dump(report.to_dict(), f, indent=2)
            typer.secho(f"✓ Report saved to {output}", fg=typer.colors.GREEN)
        
        # Display summary
        if show_report:
            typer.echo("\n=== DATA QUALITY REPORT ===")
            typer.echo(f"Overall Quality Score: {report.overall_quality_score:.1f}%")
            typer.echo(f"  - Completeness: {report.completeness_score:.1f}%")
            typer.echo(f"  - Consistency: {report.consistency_score:.1f}%")
            typer.echo(f"  - Validity: {report.validity_score:.1f}%")
            
            if report.issues:
                typer.echo("\n🔴 Critical Issues:")
                for issue in report.issues:
                    typer.echo(f"  - {issue}")
            
            if report.warnings:
                typer.echo("\n🟡 Warnings:")
                for warning in report.warnings[:5]:  # Show first 5
                    typer.echo(f"  - {warning}")
                if len(report.warnings) > 5:
                    typer.echo(f"  ... and {len(report.warnings) - 5} more")
            
            if report.recommendations:
                typer.echo("\n💡 Recommendations:")
                for rec in report.recommendations:
                    typer.echo(f"  - {rec}")
    
    except Exception as e:
        _cli_error(f"Analysis failed: {e}", code=3)


@data_app.command("clean")
def data_clean(
    data_file: Path = typer.Argument(..., help="Path to data file"),
    output: Path = typer.Option(None, "--output", "-o", help="Output file path"),
    missing: str = typer.Option("smart", "--missing", help="Missing value strategy: drop|mean|median|mode|smart"),
    outliers: str = typer.Option("clip", "--outliers", help="Outlier strategy: keep|clip|remove"),
    scale: str = typer.Option("none", "--scale", help="Scaling: none|standard|minmax|robust"),
    duplicates: bool = typer.Option(True, "--remove-duplicates", help="Remove duplicate rows"),
) -> None:
    """Automatically clean and preprocess data."""
    from meridian.data.quality import DataPreprocessor
    import pandas as pd
    
    try:
        # Load data
        df = pd.read_csv(data_file)
        n_before = len(df)
        typer.echo(f"Cleaning {data_file.name} ({n_before} rows, {len(df.columns)} columns)...")
        
        # Clean
        preprocessor = DataPreprocessor()
        df_clean = preprocessor.auto_clean(
            df,
            handle_missing=missing,
            handle_outliers=outliers,
            handle_duplicates=duplicates,
            scale_numeric=scale
        )
        
        # Save
        if not output:
            output = data_file.parent / f"{data_file.stem}_cleaned.csv"
        
        df_clean.to_csv(output, index=False)
        n_after = len(df_clean)
        
        typer.secho(f"✓ Cleaned data saved to {output}", fg=typer.colors.GREEN)
        typer.echo(f"  Rows: {n_before} → {n_after} ({n_before - n_after} removed)")
        typer.echo(f"  Missing values handled: {missing}")
        typer.echo(f"  Outliers handled: {outliers}")
        if scale != "none":
            typer.echo(f"  Scaling applied: {scale}")
    
    except Exception as e:
        _cli_error(f"Cleaning failed: {e}", code=3)


@data_app.command("quick")
def data_quick(
    data_file: Path = typer.Argument(..., help="Path to data file"),
) -> None:
    """Quick data profiling - show basic stats and issues."""
    import pandas as pd
    
    try:
        df = pd.read_csv(data_file)
        
        typer.echo(f"\n📊 {data_file.name}")
        typer.echo(f"{'='*50}")
        typer.echo(f"Shape: {df.shape[0]} rows × {df.shape[1]} columns")
        typer.echo(f"Memory: {df.memory_usage(deep=True).sum() / 1024 / 1024:.1f} MB")
        
        # Data types
        dtypes = df.dtypes.value_counts()
        typer.echo(f"\nData Types:")
        for dtype, count in dtypes.items():
            typer.echo(f"  {dtype}: {count} columns")
        
        # Missing values
        missing = df.isnull().sum()
        missing_cols = missing[missing > 0]
        if len(missing_cols) > 0:
            typer.echo(f"\nMissing Values:")
            for col, count in missing_cols.head(10).items():
                pct = (count / len(df)) * 100
                typer.echo(f"  {col}: {count} ({pct:.1f}%)")
        else:
            typer.echo(f"\n✓ No missing values")
        
        # Duplicates
        n_dupes = df.duplicated().sum()
        if n_dupes > 0:
            typer.echo(f"\n⚠️  {n_dupes} duplicate rows ({n_dupes/len(df)*100:.1f}%)")
        
        # Numeric summary
        numeric_cols = df.select_dtypes(include=['number']).columns
        if len(numeric_cols) > 0:
            typer.echo(f"\nNumeric Columns ({len(numeric_cols)}):")
            summary = df[numeric_cols].describe().round(2)
            for col in numeric_cols[:5]:  # Show first 5
                stats = summary[col]
                typer.echo(f"  {col}: mean={stats['mean']:.2f}, std={stats['std']:.2f}, "
                          f"range=[{stats['min']:.2f}, {stats['max']:.2f}]")
            if len(numeric_cols) > 5:
                typer.echo(f"  ... and {len(numeric_cols) - 5} more")
        
        # Categorical summary
        cat_cols = df.select_dtypes(exclude=['number']).columns
        if len(cat_cols) > 0:
            typer.echo(f"\nCategorical Columns ({len(cat_cols)}):")
            for col in cat_cols[:5]:  # Show first 5
                n_unique = df[col].nunique()
                typer.echo(f"  {col}: {n_unique} unique values")
            if len(cat_cols) > 5:
                typer.echo(f"  ... and {len(cat_cols) - 5} more")
    
    except Exception as e:
        _cli_error(f"Quick analysis failed: {e}", code=3)


@data_app.command("visualize")
def data_visualize(
    data_file: Path = typer.Argument(..., help="Path to data file"),
    target: Optional[str] = typer.Option(None, "--target", "-t", help="Target column name"),
    output_dir: Optional[Path] = typer.Option(None, "--output", "-o", help="Output directory for plots"),
    html: bool = typer.Option(False, "--html", help="Generate HTML report"),
) -> None:
    """Generate comprehensive EDA visualizations."""
    from meridian.data.visualize import DataVisualizer
    import pandas as pd
    
    try:
        # Load data
        df = pd.read_csv(data_file)
        typer.echo(f"Generating visualizations for {data_file.name}...")
        
        # Create visualizations
        visualizer = DataVisualizer()
        report = visualizer.create_eda_report(
            df, 
            target_col=target,
            dataset_name=data_file.stem
        )
        
        # Save plots
        if output_dir:
            output_dir = output_dir or Path(f"{data_file.stem}_plots")
            report.save_plots(output_dir)
            typer.secho(f"✓ Plots saved to {output_dir}/", fg=typer.colors.GREEN)
        
        # Generate HTML report
        if html:
            html_path = output_dir / "report.html" if output_dir else Path(f"{data_file.stem}_report.html")
            html_content = report.generate_html_report()
            with open(html_path, 'w') as f:
                f.write(html_content)
            typer.secho(f"✓ HTML report saved to {html_path}", fg=typer.colors.GREEN)
            
            # Try to open in browser
            import webbrowser
            webbrowser.open(f"file://{html_path.absolute()}")
        
        # Display insights
        typer.echo("\n📊 Visualization Insights:")
        for name, insight in report.insights.items():
            typer.echo(f"\n{name.replace('_', ' ').title()}:")
            typer.echo(f"  {insight}")
        
        typer.echo(f"\nGenerated {len(report.plots)} visualization(s)")
    
    except Exception as e:
        _cli_error(f"Visualization failed: {e}", code=3)


# ML/AutoML Commands
@ml_app.command("tune")
def ml_tune(
    data_file: Path = typer.Argument(..., help="Path to data file"),
    target: str = typer.Argument(..., help="Target column name"),
    algorithm: str = typer.Option("auto", "--algorithm", "-a", help="Algorithm: auto|xgboost|lightgbm|random_forest"),
    task: str = typer.Option("auto", "--task", help="Task type: auto|classification|regression"),
    trials: int = typer.Option(50, "--trials", "-n", help="Number of optimization trials"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output directory for results"),
) -> None:
    """Run AutoML hyperparameter tuning with Optuna."""
    try:
        # Check if Optuna is available
        try:
            import optuna
        except ImportError:
            _cli_error("Optuna not installed. Run: pip install optuna", code=2)
        
        from meridian.ml.automl import AutoMLPipeline
        import pandas as pd
        
        # Load data
        df = pd.read_csv(data_file)
        X = df.drop(columns=[target])
        y = df[target]
        
        typer.echo(f"Starting AutoML for {data_file.name}")
        typer.echo(f"  Target: {target}")
        typer.echo(f"  Features: {len(X.columns)}")
        typer.echo(f"  Samples: {len(X)}")
        typer.echo(f"  Algorithm: {algorithm}")
        typer.echo(f"  Trials: {trials}")
        typer.echo("")
        
        # Run AutoML
        pipeline = AutoMLPipeline(task_type=task)
        result = pipeline.fit(
            X, y,
            preprocess=True,
            algorithm=algorithm,
            n_trials=trials
        )
        
        # Display results
        typer.secho("\n✓ Optimization Complete!", fg=typer.colors.GREEN)
        typer.echo(f"\nBest Score ({result.metric}): {result.best_score:.4f}")
        typer.echo(f"Test Score: {result.test_score:.4f}" if result.test_score else "")
        typer.echo(f"Training Time: {result.training_time:.1f}s")
        typer.echo(f"\nBest Parameters:")
        for param, value in result.best_params.items():
            typer.echo(f"  {param}: {value}")
        
        if result.cross_val_scores:
            cv_mean = sum(result.cross_val_scores) / len(result.cross_val_scores)
            cv_std = pd.Series(result.cross_val_scores).std()
            typer.echo(f"\nCross-Validation: {cv_mean:.4f} ± {cv_std:.4f}")
        
        if result.feature_importance:
            typer.echo(f"\nTop 5 Important Features:")
            for feat, imp in list(result.feature_importance.items())[:5]:
                typer.echo(f"  {feat}: {imp:.4f}")
        
        # Save results
        if output:
            output.mkdir(parents=True, exist_ok=True)
            result.save(output)
            typer.secho(f"\n✓ Results saved to {output}/", fg=typer.colors.GREEN)
    
    except Exception as e:
        _cli_error(f"AutoML failed: {e}", code=3)


@ml_app.command("quick")
def ml_quick(
    data_file: Path = typer.Argument(..., help="Path to data file"),
    target: str = typer.Argument(..., help="Target column name"),
) -> None:
    """Quick ML model training with default settings."""
    from sklearn.model_selection import train_test_split
    from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
    from sklearn.metrics import accuracy_score, r2_score
    import pandas as pd
    
    try:
        # Load data
        df = pd.read_csv(data_file)
        X = df.drop(columns=[target])
        y = df[target]
        
        # Detect task type
        task_type = "classification" if y.nunique() <= 20 else "regression"
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42,
            stratify=y if task_type == "classification" else None
        )
        
        # Train model
        typer.echo(f"Training {task_type} model...")
        if task_type == "classification":
            model = RandomForestClassifier(n_estimators=100, random_state=42)
            model.fit(X_train, y_train)
            y_pred = model.predict(X_test)
            score = accuracy_score(y_test, y_pred)
            metric = "Accuracy"
        else:
            model = RandomForestRegressor(n_estimators=100, random_state=42)
            model.fit(X_train, y_train)
            y_pred = model.predict(X_test)
            score = r2_score(y_test, y_pred)
            metric = "R² Score"
        
        typer.secho(f"\n✓ Model trained!", fg=typer.colors.GREEN)
        typer.echo(f"{metric}: {score:.4f}")
        
        # Feature importance
        importances = model.feature_importances_
        feature_imp = sorted(zip(X.columns, importances), key=lambda x: x[1], reverse=True)
        
        typer.echo(f"\nTop 5 Important Features:")
        for feat, imp in feature_imp[:5]:
            typer.echo(f"  {feat}: {imp:.4f}")
    
    except Exception as e:
        _cli_error(f"Quick ML failed: {e}", code=3)

