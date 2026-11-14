# Research Navigator v0.1 · Build & Verification Report

Build context: 2026-11-13 (UTC date, environment clock); Skill is standalone and uses Python standard library. Research example is explicitly **SYNTHETIC FIXTURE**.

## Delivered capabilities

- Valid SKILL.md frontmatter and lazy-loaded references for five interconnected modules.
- Research decision frontier / glossary / evidence review and human-in-the-loop protocols.
- Durable project JSON state, stable entity IDs, validated dependency edges, event log, advisory file lock and atomic JSON replacement.
- Orthogonal workflow/epistemic/review/outcome/lifecycle/impact fields; CLI guards against unsupported `done`, fake source-backed full-text reading, and agent self-approval.
- Lifecycle/archive policy: active, parked, quarantined, retired, under-revival-review; source-level negative outcomes remain distinct from lifecycle.
- Query isolation enforced by programmatic mode: planning excludes archived, stale, needs-review and done; archive exploration needs declared user authorization; synthesis retains negative history.
- Human-approved two-stage revival generates a distinct unvalidated new candidate with `derived-from` and `revives` relationships, while preserving old archive/history.
- Cross-module propagation for explicit dependency changes, contradictory sources and blocked relations; no blanket upstream deletion.
- Local self-contained HTML dashboard with role views, search/filter, archive cards, experiment results, SVG relation graph, entity drawer and audit history. This is a static **read-only** snapshot and has a clear timestamp.
- Small, demonstrable synthetic end-to-end project with recorded negative/inconclusive result, archived route, an under-review legacy idea, a new active direction and affected synthesis claim.

## Executed checks

- `python -m unittest discover -s evals -p 'test_*.py' -q` — **26 passed** (including archival isolation, human approval boundaries, DOI/abstract hygiene, dependency and contradiction propagation, negative≠quarantine, done≠verified, duplicate/cycle detection, state restore, archive history, HTML escaping).
- `python scripts/validate_state.py /mnt/data/research-navigator-demo` — **passed**, 11 items, 8 relations, 1 synthetic unverified source, 31 events at time of build.
- Chromium + Playwright loaded exact generated HTML via `page.set_content`, exercised 5 counters, entity search, lifecycle filter, drawer, archive search, SVG graph, history and mentor view, with **no JavaScript page errors**.
- Direct `file://` browser navigation in this sandbox returned `ERR_BLOCKED_BY_ADMINISTRATOR` (environment policy). **Not counted as passed**; page is designed with embedded JSON and no external assets for standalone use.
- `archify` executable not found on PATH; deliberately used native SVG without guessing a third-party schema.

## Explicitly not tested or not implemented

- No real paper lookups, DOI existence validation, external research connectors, actual experiment execution or claimed real result quality.
- No end-to-end live LLM interviewing/advisor approval test; 15 human/agent scenarios in `evals/agent-scenarios.md` remain for real deployment evaluation.
- No browser writeback, logged-in roles, online collaboration, human identity authentication or cross-file database transaction guarantee. CLI `--actor` is only a declaration. No cryptographic audit guarantees.
- Metadata validity and an artifact path do not prove a true scientific conclusion. Agent still must inspect evidence and logs, ask humans at authorization boundaries, and avoid adding unsupported claims.

## Next recommended milestones

1. Run the 15 Agent eval scenarios with actual students/advisors and real repository content.
2. Add optional schema validation for logged experiment artifacts and research provenance when the user's experiment tracker is known.
3. Integrate reference-manager and experiment-runner adapters only after real APIs, permissions, and project context are available.
4. Add server-mediated approval/writeback only if students truly need browser editing; the offline read-only principle should stay the safe default.
