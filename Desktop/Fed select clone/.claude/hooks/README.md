# FedProcure Hooks

Adapted from [everything-claude-code](https://github.com/affaan-m/everything-claude-code) for FedProcure's Python/FastAPI/PostgreSQL stack.

## PreToolUse Hooks

| Hook | Matcher | Behavior | Exit Code |
|------|---------|----------|-----------|
| Dev server blocker | `Bash` | Blocks uvicorn/gunicorn outside tmux | 2 (blocks) |
| Git push reminder | `Bash` | Reminds to review before `git push` | 0 (warns) |
| Commit format check | `Bash` | Validates conventional commit prefixes (feat/fix/docs/test/refactor/chore) | 0 (warns) |
| File size + secrets | `Write` | Blocks files >800 lines and hardcoded credentials | 2 (blocks) |
| Doc file warning | `Write` | Warns about non-standard .md/.txt files | 0 (warns) |

## PostToolUse Hooks

| Hook | Matcher | Behavior |
|------|---------|----------|
| PR logger | `Bash` | Logs PR URL after `gh pr create` |
| Pytest summary | `Bash` | Summarizes pass/fail counts after pytest runs |
| Edit quality | `Edit` | Warns about print(), eval(), TODO in Python edits |

## Stop Hooks

| Hook | Behavior |
|------|----------|
| Session logger | Persists session markers to ~/.fedprocure/session_log.jsonl |

## Customization

Disable hooks by removing entries from hooks.json or overriding in ~/.claude/settings.json.
