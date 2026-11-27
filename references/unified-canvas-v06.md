# v0.6 Unified Research Node Editor — Contract and Operator Guide

Development status: feature branch only. The v0.5 Multi-Harness source has been integrated **in this feature branch**, but PR #66 has NOT been merged or released into main.

## Authoritative stores

| Content | Authority | Unified rendering |
|---|---|---|
| Scientific entities, sources, evidence, ExperimentRuns, Milestones, SessionRefs | research/state/* | item:, source:, evidence:, session: |
| Grilling interview, questions, accepted answers, supplementary text and audit | research/interviews/current.json | interview:, question:, answer: |
| Milestone criteria and criterion evidence | Canonical Milestone metadata | derived criterion: nodes |
| Context-only cross-domain references | research/canvas/context-links.json | context: edges |
| Layout, camera, collapsed groups and named views | research/canvas/views.json | canvas-layout-v1 |

Research context edges are contextual **references only**: a linked interview answer, source or result does not automatically validate a Claim or satisfy a scientific Milestone. The existing canonical research state remains authoritative. Negative experimental observations and archived ideas are preserved historically.

## Typed links and port compatibility

- question → scientific item: addresses / references-route.
- confirmed or pending answer → scientific item: motivates. This is conversational motivation, not evidence.
- source / evidence / actual Result or ExperimentRun → MilestoneCriterion: context-for.
- Claim, Result, ExperimentRun, Hypothesis → MilestoneCriterion: informs (not automatic criterion acceptance).
- provider-scoped SessionRef → interview/question/answer: discussed-in-session, without raw transcript ingestion.
- item → item: existing controlled depends-on / member-of / contributes-to relation through the canonical proposal engine.

The projector enforces stable namespaced IDs, no missing endpoints, typed directions, provenance, project identity, context revision and scientific revision. New links to archived entities are forbidden; previously approved historical links stay visible after archival. Evidence supports/contradicts and Milestone approval still require their existing domain-specific workflows.

## Open the canvas

Run: python scripts/build_dashboard.py PROJECT_ROOT

Open PROJECT_ROOT/research/canvas/index.html for the classic v0.2+ Canvas or PROJECT_ROOT/research/canvas/unified.html for the unified editor. Both are self-contained offline files; offline wire connections only generate proposals for export. The classic SVG dashboard remains unchanged.

To enable safeguarded proposals, run: python scripts/local_editor.py serve PROJECT_ROOT

Use the private loopback URL and navigate to /unified#token=CAPABILITY. The public HTML shell embeds no project data; /api/unified-graph requires the same token and local-origin security guards as /api/graph. Never publish the token or a full research project.

Drag from the **right-side output socket** to a compatible **left-side input socket**, or select output and then input by keyboard. The editor prepares a canonical add-relation or context-only link-context proposal. You must preview its before/after/impact, queue it, and explicitly approve it from an interactive terminal:

  python scripts/local_editor.py inspect PROJECT_ROOT PROPOSAL_ID
  python scripts/local_editor.py approve PROJECT_ROOT PROPOSAL_ID

There is NO HTTP approval endpoint. A queued proposal is pending, not applied. Removing context edges similarly requires an unlink-context preview and separate terminal approval. Stale, cross-project, archived or unauthorized links fail closed. Context-only edits do not change research/state scientific revision or events; the context-links sidecar increments its independent revision and records proposal ID and justification.

## Grilling and SessionRefs

Interview question/answer status, typed choices, Other input, supplements and explicit exit are projected from the interview sidecar. A user confirming an interview answer does not confirm the scientific truth of the response. If native Codex UI is unavailable, normal chat questions retain Other and optional supplementary explanations; an async 'accepted' delivery acknowledgment is not an answer.

SessionRef nodes show provider, workspace, session ID and verified-link status. On the v0.6 feature branch, the v0.5 provider contract adds DeepSeek alongside Codex and other existing providers. A session can reference many scientific items and a research node can reference multiple sessions. No full chat transcript is stored, and unverified links do not open automatically.

## Layout, privacy and release gate

Pan/zoom, card dragging, minimap, node collapsing and named layouts are presentation-only. The existing canvas-layout-v1 format accepts the new interview/criterion namespaces; browser localStorage stores views for the current origin and exported JSON can be imported through canvas_views.py. Corrupt or cross-project views are rejected. A merged scientific claim remains under canonical review rules, never a side effect of dragging a wire.

Real Codex/DeepSeek clients, native question popups and deep linking require owner-device testing. v0.6 must pass Linux/Windows and Chromium regressions, three synthetic researcher journeys with temporary fixture cleanup, review of v0.5 PR #66 integration, and explicit human approval before any merge/release.
