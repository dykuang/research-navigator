# Research Navigator v0.2 release-readiness checklist

**Release status (2026-11-22): CANDIDATE / GATED.** Feature implementation is on [`v0.2`](https://github.com/dykuang/research-navigator/tree/v0.2). Neither a merge to `main`, a GitHub release tag, nor installation on the owner's Windows computer should be inferred.

## Quick start — clearly SYNTHETIC example

From the cloned repository root:

~~~powershell
# Windows PowerShell: avoid legacy console encoding errors
$env:PYTHONUTF8 = '1'
python --version
python evals/make_demo.py C:\Temp\rn-v02-synthetic
python scripts/validate_state.py C:\Temp\rn-v02-synthetic
python scripts/build_dashboard.py C:\Temp\rn-v02-synthetic
start C:\Temp\rn-v02-synthetic\research\canvas\index.html
~~~

The resulting cards, evidence and results are *SYNTHETIC fixtures*, not verified literature or real experiments. The older `research/dashboard/index.html` remains a compatible readonly fallback. The Canvas supports drag/zoom/filter/export and browsing archived states. A standalone offline HTML file does **not** write research meaning.

To submit genuine user-approved semantic changes on a **private single-user machine**, start:

~~~powershell
python scripts/local_editor.py serve C:\Temp\rn-v02-synthetic
~~~

Open the printed private localhost URL → **Open interactive Research Canvas**. Create a draft Branch or scientific Milestone, preview before/after and impact, then queue a proposal. In a second interactive terminal:

~~~powershell
python scripts/local_editor.py inspect C:\Temp\rn-v02-synthetic PROPOSAL_ID
python scripts/local_editor.py approve C:\Temp\rn-v02-synthetic PROPOSAL_ID
~~~

Type the exact confirmation phrase; refresh the Canvas to see the committed result. `202 Accepted` on a browser proposal means pending, not a scientific write.

To archive a weak negative idea, choose `archive-route` and explicitly record failure scope and revival triggers; the authorizer reviews the tombstone. Viewing this historical inspiration does not start work. A new derived candidate needs **two distinct** proposals/terminal approvals: `begin-revival-review`, then `approve-revival-candidate`. The original and its failed Result are never rewritten. SessionRef references can be registered/linked by the same proposal process. They store session IDs and roles only; no raw Agent conversation data.

### Existing v0.1 workspace migration (do not skip backup)

~~~powershell
python scripts/migrate_state.py preview C:\Path\To\ExistingProject
python scripts/migrate_state.py apply C:\Path\To\ExistingProject
python scripts/validate_state.py C:\Path\To\ExistingProject
~~~

Keep the ZIP in `research/backups/`, version-control the original files if possible and do not overwrite real experiments with demo fixtures. If a pending journal blocks reads, stop writes and run `python scripts/migrate_state.py recover PROJECT_ROOT`. No automatic migration during read-only operations.

## Data locations and boundaries

| Location | Purpose | Writable from Canvas? |
|---|---|---|
| `research/state/project.json`, `items.json`, `relations.json`, `sources.json` | Canonical scientific state | Only by separately approved, validated terminal commit |
| `research/state/session_refs.json`, `evidence_links.json` | External session and evidence metadata | Same approval guard |
| `research/state/events.jsonl` | Research change/audit history | Append via canonical state engine only |
| `research/canvas/index.html` | Fully offline, embedded graph snapshot | No |
| `research/dashboard/index.html` | Classic offline SVG fallback | No |
| `research/canvas/views.json` | Named visual layouts | Yes via explicit `canvas_views.py save`, no scientific meaning |
| `research/canvas/proposals/` | Pending browser drafts | Browser can enqueue only; not canonical research state |
| `research/backups/` | Migration backup ZIPs | Controlled migration only |

A **GitHub native Milestone** groups repository issues. A scientific **Research Navigator Milestone** is an entity inside `items.json` with scientific acceptance criteria. These must never be conflated.

## Release acceptance matrix (parent #1)

| Requirement | Evidence | Status |
|---|---|---|
| Legacy v0.1 → v0.2 migration preserves IDs, events and archive records | `test_v02.py`, `test_canvas.py`, `test_v02_end_to_end.py` | Automated passed |
| A/B/C research routes share one Baseline, preserve layout and scientific gates | Graph, Canvas, 10-card Chromium drag/refresh and integrated fixture | Automated passed |
| Negative A parked by explicit approval; planning excludes A and Milestone flags review; B continues | `test_canvas_lifecycle.py` and `test_v02_end_to_end.py` | Automated passed; human consent is synthetic in tests |
| Read-only historical inspiration != revival; separate approved two-phase process creates new hypothesis | Lifecycle tests, audit trail | Automated passed; human identity not authenticated |
| SessionRef many-to-many, roles, provider filtering and manual copy fallback; no transcripts | `test_canvas_sessions.py`, `browser_check_canvas_sessions.py` | Automated passed; real client navigation unverified |
| Invalid/stale/browser-only changes cannot silently rewrite canon | HTTP security tests, proposal regression and Chromium | Automated passed |
| Old CLI, static fallback and Unicode-safe native Windows runner | `.github/workflows/validate-v02.yml`, Windows native job | Automated passed |
| Real owner Windows/Codex client installation, actual Session ID discovery and manual navigation | [Windows/Codex manual checklist](../references/windows-codex-qa.md) | **UNVERIFIED — OWNER ACTION REQUIRED** |
| Native GitHub issue Milestone `v0.2 — Integrated Research Canvas & Session Linking` | [GitHub Milestones](https://github.com/dykuang/research-navigator/milestones) | **NOT CONFIRMED — OWNER ACTION REQUIRED** |
| Public stable tag / reviewed merge to main | No tag/merge attempted | **NOT RELEASED** |

### Automated evidence and screenshots

See the [verified Chromium screenshot artifact run #45038688124](https://github.com/dykuang/research-navigator/actions/runs/45038688124) (Artifacts → `research-canvas-synthetic-screenshot`) and the latest [v0.2 CI runs](https://github.com/dykuang/research-navigator/actions/workflows/validate-v02.yml): Python 3.10/3.12 unit+integration, native Windows runner and Linux Chromium UI/security smokes. The browser job captures **an actual Chromium screenshot of a SYNTHETIC project** to the workflow artifact `research-canvas-synthetic-screenshot` (30-day retention), downloadable from the run's Artifacts section. This is **not a screenshot of a user's real research**. Screenshots are provided as reproducible CI artifacts rather than embedding a fictional image.

## Release checklist

- [x] All v0.2 feature logic tracked and implemented in #2–#12.
- [x] Unit/integration, offline HTML, browser interaction and native Windows CI jobs provided.
- [x] Migration, explicit backups, recovery, and state engine documentation.
- [x] Read-only vs connected Canvas and manual approval limitations explained.
- [x] SessionRef provider/client support matrix and no fabricated Codex deep links.
- [x] Changelog, synthetic quickstart and reproducible Chromium screenshot artifact workflow.
- [ ] Real owner Windows/Codex smoke executed and recorded, including actual client version and screenshots/redacted logs.
- [ ] Native GitHub Milestone created and issue associations confirmed where required.
- [ ] Reviewer approves merge/release tag; avoid publishing a `v0.2.0` tag until all release gates are met.

## Next versions and excluded functionality

**v0.3:** full Conversation Provenance and Decision Replay, cross-session timeline and provenance reasoning. **v0.4:** decision-support recommendations, with human gating. **v0.5:** research-to-publication artifact pipelines. v0.2 does not include these, and it does not authenticate mentor identity, verify research literature automatically, or execute experiments autonomously.

**Final rule:** Close parent issue #1 and announce a stable v0.2 release **only when all mandatory acceptance items above have evidence**. A green CI run is necessary but not sufficient for real Codex integration or a human research authorization gate.
