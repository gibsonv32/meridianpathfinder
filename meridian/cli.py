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
def init() -> None:
    """Initialize a new MERIDIAN project (stub)."""
    typer.echo("init: not implemented")


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


app.add_typer(mode_app, name="mode", help="Mode-related commands.")
app.add_typer(artifacts_app, name="artifacts", help="Artifact-related commands.")
app.add_typer(llm_app, name="llm", help="LLM-related commands.")
app.add_typer(skills_app, name="skills", help="Skill-related commands.")

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

