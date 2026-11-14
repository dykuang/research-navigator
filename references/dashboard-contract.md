# Offline HTML workbench contract

`python scripts/build_dashboard.py /PROJECT/ROOT` rebuilds `research/dashboard/index.html`. It embeds the state JSON into HTML, escapes `<`, `>`, `&` and U+2028/2029, and has no third-party JS/CSS dependencies; it can open via `file://` without JSON fetch. It is a **read-only** generated snapshot, not a live data source.

It displays: current research question and module focus; next decision; module item distributions (not fake scientific % completion); pending user confirmations and stale/blocked items; live-in-this-file search/filter over entities; experiment outcome including negative/inconclusive; archive cards with failure scope and revival triggers; an SVG ID-based relationship graph; source verification and event history; and student/mentor focus switch.

Clicking an entity opens a drawer with six status dimensions, observation/log, evidence sources and relations. The archive "copy instruction" asks for **read-only** review: it never changes state. For real state changes, return to the Agent / CLI and rerender. The UI must always show generation time, project revision, offline/readonly label. Do not write approval buttons that silently do nothing.

Archify optional: only if available and its current schema/API is actually inspected and validated. Do not invoke a guessed Archify command. The native SVG is the supported portable default and never blocks research workflow.
