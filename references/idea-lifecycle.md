# Research Idea Lifecycle · 搁置—隔离—回收

## Filter policies are enforced in `scripts/rn_core.py::query`

| Query mode | Positive candidates | Archived ideas | Authorization |
|---|---|---|---|
| `planning` / `recommendation` / `task-generation` | Only active eligible entities | Excluded | No special auth |
| `risk-check` / `novelty-check` / `failure-avoidance` | Present with caution | Present **only as historical risk** | Read-only |
| `synthesis` | May use as claims if evidence supports | Negative history remains visible | Read-only |
| `archive-exploration` / `creative-recombination` | Not the target | Archived inspiration, explicitly unvalidated | User explicitly asks for historical ideas (`--user-authorized`) |
| `revival-review` | Not the target | Historical review candidate only | User requests review (`--user-authorized`) |

No archive/revival result is automatically a to-do list. Agent output must carry the `usage` annotation and the original ID. A historical result cannot be relabeled as positive support by prompting alone. Single negative experiment → evidence `negative` or `inconclusive`; it does **not** imply `quarantined`.

## Archive procedure

1. Distinguish theory / implementation / dataset / evaluation / resource failure and number of replications; document uncertainty in the explanation. Ask user to choose among continue, narrow, pivot, park, quarantine, retire, or re-test.
2. If user approves, update lifecycle with `--reason --failure-category --failure-scope --confidence --revival-triggers`, optionally `--lesson --cost --evidence-ref`. The engine writes `archive` metadata and an event. `build_dashboard.py` creates `research/archive/cards/IDEA-xxxx.md` and an index **only when records exist**.
3. Explain affected dependents and new review queue. Previous negatives remain in Result items and synthesis mode. No physical deletion or silent rewrite.

## Revival procedure

A user who says "看看旧 IDEA-0001 能否启发方法 B" approves **only archive exploration**. Run `--mode archive-exploration --user-authorized`; report original failure conditions, available evidence, and what is only a creative inference. No state change.

If they explicitly ask for a formal review:

1. Show old archive card including scope, uncertainty, affected dependencies and triggers.
2. Ask which old assumptions changed, what new data/constraints are available, and what a cheap falsification test could be.
3. With consent set old lifecycle `under-revival-review` and include `--revival-question` and `--new-conditions`.
4. **With a second explicit approval** call `revive` to create an unconfirmed `hypothesis`-level new candidate. The old record returns to its original archived lifecycle, never to active.
5. New version gets fresh stable ID, `derived-from` and `revives` edges. Run relevant module protocols again. Its result is unknown; old results never become positive. Avoid re-running the original exact failure without an explainable new condition.
6. If review is rejected, return to the previous archived lifecycle with reason; keep review result in an event or research note.

**Security limit**: CLI `--actor user|mentor` is not proof of identity. The calling Agent must actually present the choice and receive authorization. A fully local unattended script cannot substitute for this policy.

## #11 Canvas lifecycle approvals (v0.2)

The connected localhost Canvas offers explicit **archive-route**, **begin-revival-review** (first approval), **approve-revival-candidate** (second independent approval) and **reject-revival-review** proposals. These do not bypass the terminal approval gate: each phase is a separate proposal, with a unique project revision and explicit typed terminal confirmation. A mere click on an archived node never mutates its state.

`archive-route` requires a documented failure scope, reason and future revival triggers, plus optionally evidence IDs, diagnostic confidence, category and lesson. It stores an immutable historical tombstone and flags affected downstream routes/Milestones for review. Negative experiments are **not automatically** generalized to broad scientific failure. Shared Baselines and unrelated branches remain active.

A formal review only marks the original `under-revival-review`. The second explicit approved proposal creates a **new** hypothesis-level candidate with `derived-from` and `revives` edges and returns the original to its archived state. Its old ID, negative experiment results, archive tombstone and historical events are preserved. Rejecting a review returns the original to its previous archived status without creating a candidate.

Archive cards are visible in the Canvas inspector with their scope, uncertainty, revival conditions, original evidence and bounded decision events. Planning mode excludes inactive nodes; archive/risk/synthesis exploration remains read-only. The local operator's typed approval is a workflow gate, **not cryptographic identification** of a mentor.

Use `python scripts/local_editor.py serve PROJECT_ROOT` and then the connected Canvas. The standalone offline HTML remains a read-only snapshot with exportable draft proposals.
