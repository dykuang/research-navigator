# State and schema contract (v0.2; backward-compatible legacy read)

`research/state/` retains `project.json`, `items.json`, `relations.json`, `sources.json`, and append-only `events.jsonl`; v0.2 adds `session_refs.json` and `evidence_links.json`. All files are UTF-8. **No shared skill-level student data.** A project lives entirely at the user-given project root.

## Entity contract

`items.json = {"items":[...]}`. Each item has: `id`, `type`, `title`, `module`, `description`, `workflow_status`, `epistemic_status`, `review_status`, `outcome`, `lifecycle_status`, `impact_status`, `owner`, `created_by`, `evidence_refs`, `depends_on`, `acceptance_criteria`, `next_action`, `observation`, `artifact_path`, `completion_note`, `revision`, `created_at`, `updated_at`, `archive`, `revival`, `derived_from`.

ID prefixes vary with type (`IDEA-0001`, `HYP-0001`, `EXP-0001`, etc.). `depends_on` mirrors the `depends-on` relation edges and is validated for consistency. Relations are exact stable-ID edges `{from, to, type}`. Types: `depends-on`, `supports`, `contradicts`, `tests`, `implements`, `supersedes`, `derived-from`, `revives`, `blocks`, `member-of`, `contributes-to`. Dependency cycles and dangling edges are rejected.

Status dimensions are **orthogonal**. Workflow: `to-be-determined`, `ready-for-agent`, `to-be-implemented`, `in-progress`, `blocked`, `done`, `no-further-considered`. Epistemic: `uncertain`, `hypothesis`, `source-backed`, `experimentally-supported`, `contradicted`, `not-applicable`. Review: `needs-user-confirmation`, `user-confirmed`, `not-required`, `rejected`. Outcome: `unknown`, `positive`, `mixed`, `negative`, `inconclusive`. Lifecycle: `active`, `parked`, `quarantined`, `retired`, `under-revival-review`. Impact: `current`, `needs-review`, `stale`, `blocked`.

`source-backed` requires references to a source with `verification_status=primary-inspected`. That only indicates an inspected original document, not a proof of truth. `experimentally-supported` requires observations and an artifact path (the Agent must verify the artifact actually exists before claiming the level). A `Result` item must likewise hold an observation and artifact path. The validator checks structure, not scientific correctness.

## Source contract

`sources.json = {"sources":[...]}`. Each entry: stable ID; title, authors, year, URL/DOI/local locator; `access_level` (`full-text`, `abstract`, `secondary`, `user-provided`, `unavailable`); `verification_status` (`unverified`, `metadata-checked`, `primary-inspected`); verification action note, summary, and access date. All missing facts stay missing; never fabricate bibliographic metadata. Format-validated DOI is **not** existence-verified DOI.

## Events

JSONL events record UTC time, random event ID, action, actor, changed ID, reason, old/new values. The log is appended to; application state is stored in JSON. The engine uses an OS advisory lock and atomically replaces individual JSON files. This is not a crash-safe cross-file database transaction nor tamper-evident audit log; keep the project under Git/versioned backups for stronger durability.

## v0.2 additive domain and migration (#2–#5)

`schema_version=0.2.0` is used for new projects. `0.1.0` remains read-only until explicit migration with `python scripts/migrate_state.py preview|apply PROJECT_ROOT`. A legacy project lacking new sidecars loads as empty arrays; it is never silently upgraded during planning. Applying migration creates a verified ZIP backup under `research/backups/`, checks validity, records one `schema-migrated` event, and increments project revision once. A second apply is a no-op without new events or backups. Original item IDs, statuses, evidence, archive history and event content are preserved.

**Transaction and concurrency guarantee:** write operations hold an advisory project lock and require current project revision to match the in-memory revision; `write(..., expected_revision=N)` optionally checks a caller-supplied optimistic version. A pre-write `pending-transaction.json` undo journal holds exact prior file text including the event log. Interrupted or partially written data is **blocked for reads** until explicit `python scripts/migrate_state.py recover PROJECT_ROOT`. Recovery rolls back to pre-write bytes. This is a crash-recoverable single-process/local filesystem design, **not** a multi-host ACID database or cryptographically immutable audit log. Restore a backup from Git/ZIP if filesystem storage itself is damaged. External integrations must not bypass the state engine or write JSON directly.

New entities in the existing `items.json`:
- `ResearchBranch` (prefix `BR-`): same orthogonal statuses as other research items plus `branch.goal` and nonempty `branch.stop_conditions[]`; never equate Git branches and research routes.
- `Milestone` (prefix `MILE-`): `milestone.criteria[]` entries with stable criterion ID, scientific description, linked evidence IDs; `accepted`, `approval_note`. Scientific completion requires linked evidence for every criterion and explicit human sign-off. Approval does not upgrade epistemic truth.
- Explicit graph relation `X member-of BR-xxxx` assigns a research item to one or more branches, without copying shared sources/Baselines. `X contributes-to MILE-xxxx` associates a branch or scientific item with a milestone. These link targets are structurally validated, and upstream changes flag downstream review.

`evidence_links.json = {"evidence_links": [...]}`:
- stable `EVL-xxxx`, `claim_id` (must be a Claim), `evidence_id` (known source/item), `stance` (`supports|contradicts|qualifies`), `quality` (`unverified|source-checked|experiment-observed`), `scope` (required), `locator` (paper section or artifact location), `note`, `created_at`, `recorded_by`.
- `source-checked` is valid only for an actually marked primary-inspected source, not an abstract. `experiment-observed` requires Result with an observation and artifact path. These are metadata safeguards, *not automatic source verification*. Contradiction marks a related Claim and downstream dependents for review, never auto-adjusts scientific truth.

`session_refs.json = {"session_refs": [...]}`:
- stable `SESS-xxxx`, `provider` (`codex|chatgpt|other`), `workspace_id`, `session_id`, optional HTTPS `url`, `url_verified=false`, `entity_ids[]` and per-entity `roles{}`, recording actor/time.
- Many-to-many association: an Agent Session may link to multiple research IDs and vice versa. No chat text is copied. URL acceptance is not verification of provider support; UI must not open it automatically unless an actual provider adapter verifies it. Unsafe URL shapes are rejected.
- Unlinking a SessionRef association preserves both the research entity and the historical SessionRef registration.

### Local interface / roadmap boundaries

CLI: `scripts/v02_project.py` for research Branch, Milestone, EvidenceLink and SessionRef actions. Existing `scripts/update_project.py` remains in place. Canvas (#7 onward) and secure localhost writeback (#6) are **not** implemented by these domain-model changes; static dashboard remains read-only. See `references/v02-operations.md` for documented commands and safe usage.

**Backups and recovery:** after `preview`, run `apply`; retain generated ZIP and project Git history. If reads report a pending transaction, stop all other tools and run `recover` with the project root. Do not delete journal manually or run edits concurrently from several machines.

## #11/#12 lifecycle and SessionRef overlay

The Canvas stores a proposal queue in `research/canvas/proposals/` (not canonical scientific data). `archive-route` writes an explicit archive tombstone with failure scope, confidence and revival triggers only after terminal approval. `begin-revival-review` and `approve-revival-candidate` are independent approved transactions and revisions; a new hypothesis-level ID links back via `derived-from` and `revives`; the old record and negative Result remain archived. Shared Baseline is never auto-archived due to failure in a dependent branch.

SessionRef records hold provider/workspace/session IDs, optional *unverified* clean HTTPS metadata URL, explicit entity IDs/roles, recording actor/time. Browser `register-session`, `link-session` and `unlink-session` are pending proposals until terminal approval. No provider session URL is marked verified by the v0.2 adapter, so SessionRef inspector provides manual ID copy rather than guessed auto-navigation.

Layout `research/canvas/views.json` contains project ID, node positions, viewport, collapsed node IDs, pinned groups and view metadata only; no scientific status fields. For Windows UTF-8 output use `PYTHONUTF8=1`. The GitHub native Milestone for issue planning is not the research `Milestone` entity inside `items.json`.

## v0.3 Additive Reasoning Records

The project schema field remains `0.2.0` for backward-compatible additive
records; this is not a destructive v0.3 migration. `ExperimentRun` and
`DecisionTrace` are new canonical `items` types with stable `RUN-` and
`TRACE-` IDs. Their nested typed `run` and `decision_trace` metadata is
validated by `rn_v03.validate_v03` after the existing core/v0.2 validators.
New data shares revision checking, file journaling and event history. The full
data contract, commands and ethical boundaries are in
[`reasoning-v03.md`](reasoning-v03.md). Neither type is a positive planning
candidate. No new unapproved browser writeback endpoint exists.
