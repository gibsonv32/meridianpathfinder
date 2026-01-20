# MERIDIAN Pathfinder — Claude Code Handoff

## Repo + paths
- **Repo root**: `~/dev/meridianpathfinder`
- **CLI**: `meridian/cli.py` (Typer app entry)
- **Modes**: `meridian/modes/`
- **Artifact schemas**: `meridian/artifacts/schemas.py`
- **Gates**: `meridian/core/gates.py`
- **State**: `.meridian/state.json`
- **Fingerprints DB**: `.meridian/fingerprints.db`
- **Artifacts dir**: `.meridian/artifacts/`
- **Deliverables dir**: `.meridian/deliverables/`
- **Generated runnable scaffold**: `PROJECT/`

## Current status (done + verified)
- Modes implemented + wired into CLI: **0.5, 0, 1, 2, 3, 4, 5, 6, 6.5, 7**
- Hard gates + provenance/fingerprints working; `--verify` shows `fp=ok` for latest artifacts.
- UX commands implemented:
  - `meridian status`
  - `meridian mode list`
  - `meridian artifacts list` (filters: `--type`, `--mode`, `--latest-per-type`, `--verify`)
  - `meridian artifacts show` (selectors: `--type`, `--id`, `--file`, with `--verify`)
  - Clean gate-block errors (no tracebacks).
- `PROJECT/` is **real** (not placeholder):
  - `PROJECT/src/pipeline.py` implements:
    - `train()` → trains LogisticRegression, writes `PROJECT/artifacts/model.joblib` + `metrics.json`
    - `predict_row()` → uses saved model (or returns neutral 0.5 if untrained)
    - `health()` → minimal health payload
  - `PROJECT/demo.py` is a single-command demo: train + predict.

## Verified commands (run from repo root)
```bash
cd ~/dev/meridianpathfinder

/Users/vincentgibson/.local/bin/uv run meridian status
/Users/vincentgibson/.local/bin/uv run meridian artifacts list --latest-per-type --verify

# Example: show + verify an artifact by id
/Users/vincentgibson/.local/bin/uv run meridian artifacts show --id ecce75a9-6197-428d-880e-a78c4983da10

# Single-command PROJECT demo (train + predict)
/Users/vincentgibson/.local/bin/uv run python PROJECT/demo.py --data data_mode2.csv --target target --row '{"x1":0.1,"x2":-0.2}'
```

## Next work (Claude Code)
### 1) Add a single-command MERIDIAN demo runner (highest leverage)
Implement something like:
```bash
meridian demo --data <csv> --target <col> --row '<json>'
```
Behavior:
- Prints `meridian status`
- Prints latest artifacts summary (optionally `--verify`)
- Runs `PROJECT/demo.py` and prints TRAIN + PREDICT output
- Prints paths to `.meridian/deliverables/*` and latest `DeliveryManifest`

Constraints:
- Keep dependency-light (no servers required).
- Use consistent exit codes (0 success, 2 usage/gate block, 3 external/LLM failure if you add it).

### 2) Production hardening
- Implement `meridian init` (create `meridian.yaml`, `.meridian/`, data dirs).
- Add config templates and safer defaults.
- Improve help text + error consistency.

### 3) Docs + packaging
- README “new dataset quickstart”
- “How to interpret artifacts” walkthrough
- “How to configure LLM provider” section (no secrets in repo)

