# v0.2 Infinite Research Canvas — #7 / #8 / #9

## What is actually shipped

- `scripts/graph_projection.py`: read-only typed node/edge projection from canonical state, no parallel knowledge database; JSON export with stable namespaced IDs, provenance links, a full-graph export or deterministic pagination (max 1000 nodes/page), 4 research-oriented views plus archive/planning mode.
- `scripts/build_canvas.py`: standalone offline `research/canvas/index.html` with embedded graph JSON. The existing `build_dashboard.py` also builds both the classic SVG dashboard **and** the new interactive canvas.
- `templates/research_canvas.html`: dependency-free interactive infinite world-coordinates canvas, drag, zoom, keyboard arrow-key movement, minimap, search and filters, inspector, collapse-neighbors, route/evidence/outputs views and SVG export.
- `scripts/canvas_views.py`: separately persisted canvas views at `research/canvas/views.json` with strict layout-only schema and project ID validation. No scientific status, evidence, review or audit event changes.

## Quick start

~~~bash
python scripts/update_project.py init /PATH/PROJECT --name 'Example research'
# populate the project with real research records through the Agent/CLI
python scripts/build_dashboard.py /PATH/PROJECT
# open /PATH/PROJECT/research/canvas/index.html in a browser
# alternatively build only canvas:
python scripts/build_canvas.py /PATH/PROJECT
~~~

The legacy dashboard `research/dashboard/index.html` contains a navigation link to the new canvas. Both outputs are offline, read-only **snapshots** of a specific research revision. Editing the real project requires the controlled CLI/Agent; drag/layout actions never create scientific results.

## Canvas interaction

- Pan: drag empty canvas; keyboard focus on workspace then arrow keys.
- Zoom: wheel over canvas, toolbar +/- buttons or keyboard +/- on focused workspace.
- Drag research cards: hold and move; keyboard focus on card and use arrows (Shift for larger increments). Enter/Space opens details.
- Select a node to inspect status dimensions and explicit evidence, original source and relation provenance; no color means automatic scientific validation.
- Filters: Explore, Evidence, Research Routes, Outputs, Planning and Archive; module, lifecycle, keyword and stable ID; minimap shows the current viewport.
- Collapse/expand selected node's immediate neighbors; select and pin its module group to preserve its positions when resetting the rest.
- Export current SVG directly from the visible graph, read-only and labeled with canonical revision.

## Saved layouts and persistence — Issue #9

Canvas **presentation** state stores only node x/y, world viewport (x/y/scale), collapsed node IDs, pinned module groups, author, saved view name, source graph revision and project ID. No evidence, epistemic status or approval fields are allowed.

Click **保存布局** to save the named layout in the current browser's localStorage. This persists through a same-origin refresh but is browser/origin-specific and may be disabled on `file://` or privacy modes. **导出 JSON** always provides portable metadata independent of browser storage. Import accepts only a project-matching validated layout (2 MB limit).

To persist exported layout under project files, use the CLI:

~~~bash
python scripts/canvas_views.py save /PATH/PROJECT ~/Downloads/research-layout-default.json --name default
python scripts/canvas_views.py list /PATH/PROJECT
python scripts/build_canvas.py /PATH/PROJECT
~~~

After rebuilding, the static canvas embeds `research/canvas/views.json`, and will restore its `default` layout unless this browser already has a local override. A saved non-default layout can be loaded by entering its name then clicking 恢复布局.

To remove only a saved view:

~~~bash
python scripts/canvas_views.py delete /PATH/PROJECT 'Research Routes'
~~~

Missing/deleted node IDs in old layouts are retained as dormant coordinates in storage and ignored by the current canvas; new nodes get deterministic defaults. This preserves stable positions for unaffected records across graph revisions. If metadata is corrupt or from another project, the canvas fails safely to default positions; scientific records are unaffected.

## Offline/online safety model

- The HTML snapshots contain the project graph (including notes, linked references and metadata) **embedded**. Treat them as research files, not as public websites. Do not distribute sensitive local project snapshots without reviewing them.
- The standalone canvas requires no CDN, external script, React build chain, or localhost server. Native SVG/HTML was chosen over React Flow for offline/stdlib-first deployment and backward compatibility; React Flow can be reconsidered if later collaborative editing demands it.
- Both the old SVG view and new canvas remain read-only. They do **not** connect to `local_editor.py` yet: joining the future canvas to #6's controlled proposal queue is #10.
- SessionRef cards represent only metadata and identifiers; no full chat texts or unverified deep-link navigation.
- Layout persistence changes `research/canvas/views.json` or browser localStorage only; never `research/state/*.json` or audit events.

## Verification

~~~bash
python -m unittest discover -s evals -p 'test_*.py' -v
python evals/browser_check_canvas.py
~~~

Unit tests verify 100+ nodes, deterministic edge provenance, XSS-safe embedded JSON, portable layout import/schema validation, old dashboard availability and no canonical research mutation. The Playwright test uses a synthetic local HTTP-served project to exercise actual Chromium node drag, zoom, minimap, search, save/reload, JSON/SVG export and old dashboard fallback.

## Scope limits

No freehand drawing, real-time collaboration, automatic chat import, graph semantics editing, browser proposals or direct Codex session navigation are included in #7–#9. Those are later roadmap tasks. On projects with very large graphs, the CLI supports pagination and focus queries; the single-file canvas currently embeds the whole graph and is best for projects within normal browser memory.