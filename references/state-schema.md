# State and schema contract (v0.1)

`research/state/` has `project.json`, `items.json`, `relations.json`, `sources.json`, and append-only `events.jsonl`. All files are UTF-8. **No shared skill-level student data.** A project lives entirely at the user-given project root.

## Entity contract

`items.json = {"items":[...]}`. Each item has: `id`, `type`, `title`, `module`, `description`, `workflow_status`, `epistemic_status`, `review_status`, `outcome`, `lifecycle_status`, `impact_status`, `owner`, `created_by`, `evidence_refs`, `depends_on`, `acceptance_criteria`, `next_action`, `observation`, `artifact_path`, `completion_note`, `revision`, `created_at`, `updated_at`, `archive`, `revival`, `derived_from`.

ID prefixes vary with type (`IDEA-0001`, `HYP-0001`, `EXP-0001`, etc.). `depends_on` mirrors the `depends-on` relation edges and is validated for consistency. Relations are exact stable-ID edges `{from, to, type}`. Types: `depends-on`, `supports`, `contradicts`, `tests`, `implements`, `supersedes`, `derived-from`, `revives`, `blocks`. Dependency cycles and dangling edges are rejected.

Status dimensions are **orthogonal**. Workflow: `to-be-determined`, `ready-for-agent`, `to-be-implemented`, `in-progress`, `blocked`, `done`, `no-further-considered`. Epistemic: `uncertain`, `hypothesis`, `source-backed`, `experimentally-supported`, `contradicted`, `not-applicable`. Review: `needs-user-confirmation`, `user-confirmed`, `not-required`, `rejected`. Outcome: `unknown`, `positive`, `mixed`, `negative`, `inconclusive`. Lifecycle: `active`, `parked`, `quarantined`, `retired`, `under-revival-review`. Impact: `current`, `needs-review`, `stale`, `blocked`.

`source-backed` requires references to a source with `verification_status=primary-inspected`. That only indicates an inspected original document, not a proof of truth. `experimentally-supported` requires observations and an artifact path (the Agent must verify the artifact actually exists before claiming the level). A `Result` item must likewise hold an observation and artifact path. The validator checks structure, not scientific correctness.

## Source contract

`sources.json = {"sources":[...]}`. Each entry: stable ID; title, authors, year, URL/DOI/local locator; `access_level` (`full-text`, `abstract`, `secondary`, `user-provided`, `unavailable`); `verification_status` (`unverified`, `metadata-checked`, `primary-inspected`); verification action note, summary, and access date. All missing facts stay missing; never fabricate bibliographic metadata. Format-validated DOI is **not** existence-verified DOI.

## Events

JSONL events record UTC time, random event ID, action, actor, changed ID, reason, old/new values. The log is appended to; application state is stored in JSON. The engine uses an OS advisory lock and atomically replaces individual JSON files. This is not a crash-safe cross-file database transaction nor tamper-evident audit log; keep the project under Git/versioned backups for stronger durability.
