# Changelog

## Unreleased — v0.4.2 Interactive Grilling Choices

- Typed question choices with stable IDs, per-question free-form Other and legacy interview schema support.
- Strict native Codex request_user_input preview, response-to-ID resolver and explicit text fallback for unsupported clients/modes or larger choices.
- Offline interview Canvas radios and custom draft (no writeback or automatic confirmation).
- Linux/Windows/Chromium and synthetic multiround regression workflow; no stable tag or Release yet.


## Unreleased — v0.4.1 Persistent Research Grilling

- Added durable interview sidecar and question frontier DAG with confirmation, deferral, revision propagation and explicit consensus exit.
- Added project-local read-only handoff and offline HTML interview Canvas page.
- Added opt-in AGENTS.md project guidance; **does not cause fresh independent Codex sessions to automatically inherit Skill invocation**.
- Added Python Linux/Windows and Chromium multi-round tests. No canonical scientific state migration.
- No v0.4.1 official tag/release yet; PR review required.


## Unreleased — v0.3 Scientific Reasoning Graph

- Added canonical `ExperimentRun` and `DecisionTrace` entities without replacing the v0.2 storage schema.
- Added project-local artifact verification + SHA-256, explicit run attempts and Result lineage; invalidation propagates evidence-review impact without deleting negative history.
- Added scoped Claim–Evidence advisory conflict reports and event/SessionRef-based decision provenance replay. No inferred transcript or automatic scientific validation.
- Added `reasoning` graph projection view, typed links and read-only Canvas node inspector; existing protected proposal bridge remains unchanged.
- Added v0.3 CLI, synthetic regression tests, and cross-platform CI release gate.
- Milestone: [v0.3 Scientific Reasoning Graph](https://github.com/dykuang/research-navigator/milestone/1); target draft PR remains unmerged until review.


All notable Research Navigator changes are recorded here. Development changes live on `v0.2`; the default `main` branch remains the v0.1 line unless reviewed and merged separately.

## [0.2.0-rc] — 2026-11-22 (release candidate, **not tagged or merged**)

### Added

- Explicit, idempotent schema 0.1 → 0.2 migration with backup ZIP, journal recovery, project revision guards and stale-write refusal (**#2**).
- Stable ResearchBranch and scientific Milestone entities with goal/stop conditions, acceptance criteria, shared Baselines and downstream dependency impact (**#3**).
- Scoped Claim–Evidence relationships, quality rules and preserved uncertainty; contradiction and revised Result propagation (**#4**).
- Lightweight many-to-many Agent SessionRef references with provider, workspace, role and recording metadata; no chat transcript ingestion (**#5**).
- Localhost-only capability-protected proposal queue; terminal-only independent confirmation, audit events, version checks and no HTTP approve endpoint (**#6**).
- Canonical read-only graph projection, provenance edges, focus/filters and deterministic paging (**#7**).
- Native HTML/SVG infinite Canvas: zoom/pan/drag/keyboard navigation, minimap, inspector, filters and SVG export; legacy SVG retained (**#8**).
- Separate named view persistence and portable layout JSON; no scientific data mutation from UI layout changes (**#9**).
- Semantic Canvas proposal previews, queued edits and refresh after terminal approval; Branch, Milestone, Idea, evidence and typed relations (**#10**).
- Formal archive, failure-scope tombstones, dependency review and *two independently approved* revival phases, creating a distinct hypothesis-level candidate while preserving original failures (**#11**).
- SessionRef inspector, provider/workspace filters, role labels, copy ID and guarded register/link/unlink proposals (**#12**).
- Synthetic end-to-end regression; native Windows GitHub Actions tests; Chromium UI and security smokes; screenshot artifact and documented real-Codex manual tests (**#13**).
- Updated user/Agent documentation, schema, optional Ask Research Navigator guidance, migration/Windows troubleshooting and release gates (**#14**).

### Safety and compatibility

- `research/state` is the only canonical scientific state. `research/canvas/views.json` and local browser layouts hold presentation metadata only; pending proposals do not imply approved writes.
- Previously archived or negative results are never relabeled as validated/positive merely by browsing, dragging or referencing a SessionRef.
- v0.1 projects require explicit `migrate_state.py preview` then `apply` to accept v0.2 writes. Restore from verified backup or `recover` for interrupted local transactions.
- Windows CP1252/locale-specific Python output can fail for Chinese research metadata; the Windows workflow uses `PYTHONUTF8=1` and `PYTHONIOENCODING=utf-8`. Local PowerShell users should set `$env:PYTHONUTF8='1'`.

### Known limitations (release blockers / out of scope)

- Real Codex local application/CLI session-ID discovery and actual navigation on the owner's Windows PC are **not verified**. There is **no automatically verified Codex deep-link adapter** in v0.2; users can copy Session IDs and navigate manually.
- Native GitHub issue Milestone setup has not been confirmed, because the available GitHub connection cannot create/list native Milestones. GitHub Milestones are **not** Research Navigator's scientific Milestone research entities.
- The local terminal `actor=user` / `confirmed=True` gate is not cryptographic human identity verification. No cloud multi-user collaboration.
- Generated Canvas HTML contains a snapshot of research metadata. Treat it as private project data. No automatic publisher or research-paper truth checker.
- Conversation provenance timeline and decision replay are planned for **v0.3**, not v0.2.
- This is a **release candidate**; do not claim `v0.2` has shipped on `main` or that a formal GitHub Release/tag exists until it is explicitly created and verified.

See [v0.2 release checklist](docs/release-v0.2.md), [Canvas guide](references/canvas-guide.md), and [Windows/Codex test matrix](references/windows-codex-qa.md).

## v0.4.0 — Research Decision Intelligence (2026-11-23)

- Read-only evidence-gap, minimal discriminating-check proposals and scoped risk advisories atop v0.3 state.
- Archive review watchlist never activates archived routes or bypasses human review.
- Mentor decision brief with scientific Milestone evidence gates.
- Offline Research Canvas decision report and cross-platform CI.
- Canonical project schema 0.2.0 and v0.3 approvals remain unchanged. Six synthetic multi-round researcher UAT scenarios (24 rounds) and cross-platform CI passed; see docs/uat-report-v0.4-2026-11-23.md.
