# UI_UX.md — MERIDIAN Conversational Dashboard (Claude Code "Cowork" Style)

## 0) Purpose
Design a production-ready UI/UX specification for a **conversational operations dashboard** for the MERIDIAN framework. The product must feel like **Claude Code Cowork**: dark, minimal, chat-like activity feed, collapsible tool outputs, clean typography, and strong information hierarchy. It is an operations console, not a generic dashboard.

---

## 1) Product Principles (Non-Negotiable)
1) **Quiet by default, details on demand**: everything verbose is collapsed unless explicitly expanded.
2) **Conversation is the primary surface**: mode runs, tools, artifacts, and notices appear as feed items.
3) **Keyboard-first**: power users can operate without a mouse.
4) **Recoverable + auditable**: rerun, retry, resume, lineage, and log bundling are first-class.
5) **Minimal chrome**: no extra panels unless directly tied to user jobs.

---

## 2) Primary User Jobs
1) Run MERIDIAN pipeline (Modes 0→7) and see progress clearly.
2) Inspect tool outputs/logs only when needed (avoid wall-of-text).
3) Upload documents/data/templates quickly (drag-and-drop anywhere it makes sense).
4) Re-run modes with different parameters; compare outputs across runs.
5) Search and retrieve artifacts/decisions fast.

---

## 3) Information Architecture (Routes)
- `/` Dashboard (Project context + Feed + Sidebars)
- `/projects` Project picker/creation (minimal)
- `/runs/:runId` Run detail (deep link; same feed filtered to run)
- `/artifacts/:artifactId` Artifact detail (deep link; same viewer)
- `/settings` Settings (appearance locked to dark; functional settings only)
- `/connections` Connection tests + credentials status (no secret exposure)
- `/help` Commands, shortcuts, troubleshooting

Deep links must be permission-aware.

---

## 4) Layout (3-Column Console)
### 4.1 Left Sidebar (Project + Pipeline + Artifacts)
**PROJECT**
- Project selector (dropdown)
- Connection indicator: `Connected | Reconnecting | Offline` with last heartbeat timestamp
- Quick actions: New Project, Import Project (optional), Open Command Palette

**PIPELINE**
- Modes 0→7 vertical list
- Each mode row shows:
  - status icon: `idle | queued | running | success | warning | failed | cancelled`
  - label (Mode name)
  - last run timestamp
  - quick actions: `Run`, `View last`, `Retry`
- Current mode highlighted; hover reveals actions to keep UI quiet.

**ARTIFACTS**
- Artifact list grouped by: `Mode` and/or `Time`
- Search + filters: `Mode`, `Type`, `Tag`, `Status`, `Time range`
- Artifact row shows: name/type, status, created_at, small badge for version (if applicable)
- Click opens artifact viewer (right drawer or modal per system setting)

### 4.2 Center (Activity Feed)
A chat-like feed that shows:
- Mode lifecycle cards (Started → Running → Completed/Failed)
- Tool execution cards (bash/python/api) with:
  - summary line + status pill
  - `▸ Expand` to show streaming output + metadata
- Artifact creation cards (generated artifacts appear as messages)
- System notices (warnings, retries, rate limits) as low-noise banners

Feed must support:
- virtualized rendering for large histories
- quick filters (Running / Failed / Warnings / Tools / Artifacts)
- jump to: latest, last failure, currently streaming tool

### 4.3 Bottom (Command/Chat Input)
- Single-line input expands to multiline
- Supports:
  - natural language (default)
  - slash commands (e.g., `/run mode=3 target=churn`)
  - structured parameter chips (optional)
- Attachment tray with drag-and-drop and paste-to-upload
- Keyboard behavior:
  - `Enter` send, `Shift+Enter` newline
  - `↑` edit last command
  - `Esc` collapse composer / close popovers
  - `Cmd+K` open Command Palette

### 4.4 Right Side (Context Drawer — On Demand)
A single drawer surface that swaps between:
- Artifact Viewer
- Run Summary
- System Health
- Comments/Notes
This avoids new permanent panels while enabling advanced features.

---

## 5) Core Entities & Mental Model
- **Project**: container for runs, artifacts, documents, notes, settings
- **Run**: one execution context across modes (may include checkpoints)
- **Mode Run**: execution of a specific mode within a run
- **Tool Call**: one tool execution inside a mode run (bash/python/api/etc.)
- **Artifact**: output object with preview + metadata + lineage
- **Document**: uploaded source file (can be attached to run, stored in library, versioned)
- **Notice**: warnings/errors/system events surfaced in feed

Everything must be addressable by deep link: `run_id`, `artifact_id`, `document_id`.

---

## 6) Command Palette (Cmd+K) — Required
**Purpose**: primary navigation and action surface.

Features:
- Search across actions and entities (fuzzy):
  - actions: run mode, retry, cancel, open settings, open connections
  - entities: projects, runs, artifacts, documents
- Autocomplete arguments:
  - `mode`, `target`, `dataset`, `artifact_id`, `run_id`
- Recent commands list
- Keyboard-only operation required

---

## 7) Feed Item Types (UI Components)
### 7.1 Mode Lifecycle Card
Fields:
- Mode name, status, timestamps, progress (optional)
- compact summary line (always visible)
- actions:
  - `View summary`
  - `Retry`
  - `Cancel` (only if running)
  - `Resume from checkpoint` (if available)
  - `Explain failure` (if failed)

### 7.2 Tool Execution Card (Collapsible Output Block)
Collapsed (default):
- tool label (Bash/Python/API), short command/summary, status, runtime

Expanded:
- streaming output viewer with:
  - auto-scroll unless user scrolls up
  - "Jump to end"
  - search within output
  - smart truncation controls:
    - show first N lines + last M lines
    - "Load more" / "Show full"
- actions:
  - Copy output (selection + "copy all")
  - Download output
  - Open full screen
  - Pin (keeps expanded in feed)

### 7.3 Artifact Created Card
- artifact name, type, status
- quick metadata: artifact_id, mode, created_at
- actions:
  - Preview
  - Download
  - Copy ID
  - View lineage
  - Compare (select another artifact)

### 7.4 System Notice Banner
- low-noise banner with severity
- collapsible details
- actions (when applicable): retry, reconnect, view diagnostics

---

## 8) Documents & Attachments (Drag-and-Drop Required)
### 8.1 Drop Zones
1) **Composer Drop Zone** (attach to next message/run)
- Drop anywhere on input area
- Shows overlay: "Drop documents to attach"

2) **Artifacts Sidebar Drop Zone** (upload to library)
- Drop into Artifacts panel to store as document or artifact (user chooses)
- Prompt minimal metadata: name, tags, optional mode association

3) **Feed Item Drop Zone** (attach to specific run/thread)
- Drop on a specific feed item to associate documents with that run/tool/mode

### 8.2 Supported Types (Allowlist)
Required:
- PDF, DOCX, TXT, MD, CSV, XLSX
Optional:
- PPTX, JSON, YAML, images (if your workflow uses them)

### 8.3 Upload UX
Per-file chip with:
- filename, type, size
- progress bar + state: queued / uploading / processing / complete / failed
- actions: Remove, Retry, Preview, Copy ID

After upload:
- produce `document_id`, checksum/hash, MIME, created_at, size
- if ingestion exists: show `Indexing…` → `Indexed` state

### 8.4 Document Preview
- PDF: first-page thumbnail + basic page count
- DOCX/MD/TXT: rendered text preview
- CSV/XLSX: table preview (first N rows), schema summary
All previews should be lightweight and safe.

### 8.5 Versioning & Collections (Recommended)
- If same doc uploaded again: offer "New Version" (chain by hash)
- Document Collections:
  - user can group documents into named sets
  - modes can reference a collection as input

### 8.6 Security & Limits
- enforce max size and type allowlist
- never silently fail; show actionable errors
- reserve hooks for malware scanning and redaction policies

---

## 9) Running, Queueing, Checkpoints, Resume
### 9.1 Run Queue (Required)
- Show queued/running/cancelled items (compact indicator in header or drawer)
- per-project concurrency controls (configurable)
- actions: cancel run, cancel subtree (current + downstream), pause (optional)

### 9.2 Checkpointing (Recommended)
- Modes can create checkpoints
- UI shows:
  - "Checkpoint created" feed item
  - "Resume from checkpoint" on mode cards
- Clear banner when reusing artifacts:
  - "Using artifacts from Run {run_id} / Checkpoint {id}"

### 9.3 Replayability
- "Re-run same inputs"
- "Re-run with edits" opens a param editor (drawer)
- "Fork run" creates new run_id with lineage pointer to parent

---

## 10) Search Everywhere (Required)
One search entry point:
- Command Palette supports search
- Optional inline search field in sidebar

Search targets:
- feed messages
- tool calls
- runs/mode runs
- artifacts
- documents
- notes/annotations

Filters:
- time range
- mode
- status
- artifact/document type
- tags

---

## 11) Run History, Compare, Diff
### 11.1 Run Timeline
- per-mode run timeline (drawer view)
- show status changes and key artifacts produced
- quick jump into any run

### 11.2 Compare
- select two artifacts or two tool outputs:
  - side-by-side viewer (drawer full width or dedicated compare route)
- support:
  - text diff (for logs/markdown/json)
  - metadata diff (params, timestamps, versions)
  - table compare (basic for CSV/XLSX: schema + sample rows)

Keep compare as an on-demand view, not a permanent panel.

---

## 12) Trust, Explainability, Provenance
### 12.1 Run Summary Card (Required)
Auto-generated, compact summary per mode/run:
- Inputs used (document_id + hash/version)
- Parameters used
- Outputs produced (artifact list)
- Key metrics/verdict
- Warnings encountered
- Runtime (+ cost/tokens if applicable)

### 12.2 Provenance / Lineage (On Demand)
Artifact viewer includes:
- parent artifacts
- tool calls that generated it
- upstream documents/versions used
Presented as a simple lineage list or minimal graph.

### 12.3 Failure Triage (Required)
"Explain failure" action produces:
- likely root cause (structured)
- top log snippets (short)
- suggested next steps (action buttons where possible)
- "Copy diagnostic bundle" (run_id, params, logs, artifact IDs)

---

## 13) Collaboration (Minimal, Useful)
### 13.1 Notes & Annotations (Required)
- attach short notes to runs, artifacts, tool outputs
- stored with author + timestamp
- view in drawer; show a small "note" indicator on item

### 13.2 Pins & Bookmarks (Required)
- pin messages/tool outputs/artifacts
- pinned section in sidebar
- optional tags for pinned items ("Decision", "Bug", "Baseline")

### 13.3 Shareable Links (Required)
- copy link to run/message/artifact
- permission-aware:
  - if user lacks access, show "request access" path (optional)

---

## 14) Safety, Governance, Compliance
- Confirm destructive actions:
  - delete, overwrite, rerun from scratch, cancel subtree
- Display input provenance:
  - which documents/versions/hashes were used
- Audit trail:
  - who ran what, when, inputs, outputs, status
  - export JSON/CSV
- Secrets safety:
  - never render secrets in logs
  - redact common patterns; show "redacted" placeholders

---

## 15) System Health & Observability
A "System Health" drawer includes:
- WebSocket status + reconnect button
- backend latency + last error
- queue depth
- last heartbeat time
- diagnostics export (sanitized)

Optional per-run resource snapshot:
- runtime, memory, GPU usage (if available), disk IO (if collected)

---

## 16) States & Edge Cases (Must Be Designed)
- New/empty project (no runs) → guided empty state with example commands
- Loading states: skeletons (avoid spinners everywhere)
- Offline mode:
  - banner + disabled actions
  - queue commands locally (optional) with explicit user control
- Partial failures:
  - tool failed but mode continues: show warning state and allow "inspect + retry tool"
- Large outputs:
  - truncate + virtualize + search within expanded output
- Many artifacts/documents:
  - pagination or virtualization, fast filters
- Upload failures:
  - retry, remove, clear error message (type/size/network)
- Permissions:
  - read-only mode with clear badges; disable actions gracefully

---

## 17) Visual Design Tokens (Minimal, Dark Only)
### Typography
- UI: Inter (or system sans fallback)
- Code/output: JetBrains Mono (or monospace fallback)

### Color Semantics (Use Sparingly)
- success, warning, error, info in muted tones
- no decorative color blocks; color = meaning only

### Surfaces
- background: near-black
- cards: slightly lighter with subtle borders
- rounded corners; minimal shadows

### Density
- compact, console-like spacing
- consistent vertical rhythm in feed

---

## 18) Component Inventory (High-Level)
Atomic:
- StatusPill, Icon, Badge, Button, Tooltip, Dropdown, Tabs (minimal), Skeleton
- TextInput, TextArea, Chip, ProgressBar

Composite:
- ModeRow (sidebar)
- ArtifactRow, DocumentRow
- FeedItem (base), ModeCard, ToolCard, ArtifactCard, NoticeBanner
- OutputViewer (streaming + search + truncation)
- ArtifactViewer (preview + metadata + actions + lineage)
- RunSummaryPanel
- CompareViewer
- CommandPalette
- UploadTray (chips + progress)
- SystemHealthPanel
- NotesPanel
- PinnedPanel

---

## 19) Events & Data Model (WebSocket + REST)
### Status Enums
- `idle | queued | running | success | warning | failed | cancelled`

### Core Event Types (WebSocket)
- `run.created`
- `mode.started | mode.progress | mode.completed | mode.failed`
- `tool.started | tool.output.delta | tool.completed | tool.failed`
- `artifact.created | artifact.updated`
- `document.uploaded | document.processing | document.indexed | document.failed`
- `system.notice`
- `connection.status`

### REST Essentials
- list/search projects, runs, artifacts, documents
- fetch artifact/document preview metadata
- download endpoints
- run mode / cancel / retry / resume
- create note / pin / share link (permission checks)

---

## 20) Acceptance Criteria (Testable)
### Feed
- Can run a mode and see Started → Running → Completed as feed items
- Tool outputs default collapsed; expand shows streaming output correctly
- Output viewer supports copy, download, full screen, search, truncation

### Documents
- Drag-and-drop works in composer, sidebar, and feed item targets
- Upload chips show progress and failure recovery
- Preview works for PDF/DOCX/MD/TXT/CSV/XLSX
- Document IDs returned and referenced in subsequent run

### Operations
- Run queue shows queued/running states; cancel works
- Retry and rerun flows preserve parameters unless edited
- Resume from checkpoint reuses artifacts and shows banner

### Search/Compare
- Cmd+K opens palette; can open artifacts/runs and execute actions
- Search filters work; results open correct item
- Compare view shows side-by-side for selected artifacts/outputs

### Governance
- Destructive actions require confirmation
- Provenance shows hashes/versions for inputs
- Audit export produces consistent record

---

## 21) Constraints
- Dark mode only.
- No new permanent panels beyond the 3-column layout; advanced features live in the right drawer.
- Avoid generic dashboards; this is a conversational operations console.
- Optimize for clarity, speed, and recoverability.

---
