# Offline HTML workbench contract

`python scripts/build_dashboard.py /PROJECT/ROOT` rebuilds `research/dashboard/index.html`. It embeds the state JSON into HTML, escapes `<`, `>`, `&` and U+2028/2029, and has no third-party JS/CSS dependencies; it can open via `file://` without JSON fetch. It is a **read-only** generated snapshot, not a live data source.

It displays: current research question and module focus; next decision; module item distributions (not fake scientific % completion); pending user confirmations and stale/blocked items; live-in-this-file search/filter over entities; experiment outcome including negative/inconclusive; archive cards with failure scope and revival triggers; an SVG ID-based relationship graph; source verification and event history; and student/mentor focus switch.

Clicking an entity opens a drawer with six status dimensions, observation/log, evidence sources and relations. The archive "copy instruction" asks for **read-only** review: it never changes state. For real state changes, return to the Agent / CLI and rerender. The UI must always show generation time, project revision, offline/readonly label. Do not write approval buttons that silently do nothing.

Archify optional: only if available and its current schema/API is actually inspected and validated. Do not invoke a guessed Archify command. The native SVG is the supported portable default and never blocks research workflow.

## v0.2 Canvas and optional connected bridge

`build_dashboard.py` now emits **both** `research/dashboard/index.html` (unchanged classic readonly SVG workbench) and `research/canvas/index.html` (offline interactive infinite Canvas). The Canvas supports world-coordinate pan/zoom, draggable cards, typed relation graph, metadata inspectors, archive filters, SessionRef roles, named layout, JSON/SVG export. Offline Canvas remains **read-only for scientific facts**; it can export a proposal draft, not apply a canonical research edit. The Canvas may embed sensitive research metadata, so treat generated HTML as a private local project file.

To propose semantic research edits, explicitly start `scripts/local_editor.py serve PROJECT_ROOT`. Its token-protected `/canvas` shell contains no project data; `/api/graph` reads canonical state, `/api/preview` returns in-memory before/after/impact only, `/api/proposals` creates a pending draft, and **no HTTP endpoint approves**. Terminal operator must inspect and type an approval phrase. The graph is refreshed after approval; invalid/archived/stale changes fail safely. SessionRef deep links are disabled unless a future provider adapter verifies them. No full chats or fictitious scientific evidence are imported.

View positions/zoom/collapsed groups belong to `research/canvas/views.json` or browser-local view storage, never to canonical `research/state` or experiment-event truth. Native SVG remains the offline fallback. See `references/canvas-guide.md`, `references/local-bridge-security.md` and `references/windows-codex-qa.md`.
