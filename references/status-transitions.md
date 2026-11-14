# Transition rules, review authority, and impacts

| Action | Required evidence / authority | Side effect |
|---|---|---|
| Create idea/hypothesis | Mark epistemic hypothesis/uncertain | Review queue; lifecycle active, not scientifically validated |
| Promote to `source-backed` | At least one primary source actually inspected and indexed | Does not grant experimental support |
| Promote to `experimentally-supported` | Observed measurement and artifact path; verify real artifact outside schema | Does not grant human confirmation |
| `done` | Explicit acceptance criteria and completion note | Does not change epistemic status |
| `user-confirmed` | Real user or mentor consent; `--actor` is assertion, not authentication | No science-evidence promotion |
| `negative` / `inconclusive` | Observed result record and experimental conditions | No automatic lifecycle change |
| `parked` / `quarantined` / `retired` | User/mentor authorization, reason, scope, failure category, revival condition | Historical card, dependency impact scan, no positive planning candidates |
| `under-revival-review` | Archived item + explicit human request, new conditions, target question | Read/review only, no activation |
| `revive` | Existing review + human approval note | New candidate ID with `derived-from` and `revives` edges, old ID remains archived |

Propagation follows **only positive downstream dependency relations**. For `depends-on`, if `A depends-on B`, changing B flags A. For `supports` and `tests`, changing the evidence/experiment flags the supported/tested claim/hypothesis. Shared upstream datasets and prior works remain untouched. Newly impacted items receive `impact_status=needs-review` or `blocked`; they are never automatically marked `experimentally-supported`. A conflict is shown to the user, not hidden.

**Default evidence hygiene:** source titles, DOI strings, abstract summaries, paper claims, user claims, agent conjecture, and actual observed results are separate. If the agent cannot verify an external source, keep it unverified. Changes to core research question require human approval. Refusals/rejections are preserved in state/log; do not retry with cosmetic rephrasing unless context changes.
