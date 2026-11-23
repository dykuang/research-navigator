# v0.2 domain operations — ResearchBranch / Milestone / EvidenceLink / SessionRef

Use this from repository root. /PROJECT/ROOT means a student project, not the Skill directory.

## #2 — Inspect, migrate, recover

~~~bash
python scripts/migrate_state.py preview /PROJECT/ROOT
python scripts/migrate_state.py apply /PROJECT/ROOT
python scripts/validate_state.py /PROJECT/ROOT
# Only if a transaction was interrupted:
python scripts/migrate_state.py recover /PROJECT/ROOT
~~~

- preview is read-only and reports version, record counts and sidecars.
- apply migrates v0.1 to v0.2 once, makes a ZIP backup in research/backups/, records an audit event, and does not duplicate a second time.
- recover rolls back a pending transaction; do not delete the pending journal manually.
- The old CLI remains; legacy v0.1 projects must migrate before semantic mutations.
- Advisory locking + revision checks protect local state; this is not a network-wide ACID database.

## #3 — ResearchBranch and scientific Milestone

~~~bash
python scripts/v02_project.py branch-create /PROJECT/ROOT --title "Approach A" --goal "Improve transfer" --stop-condition "No repeatable gain" --stop-condition "Cost exceeds budget"
python scripts/v02_project.py branch-create /PROJECT/ROOT --title "Approach B" --goal "Improve calibration" --stop-condition "Unfair baseline comparison"
python scripts/v02_project.py milestone-create /PROJECT/ROOT --title "Choose reproducible direction" --criterion "Baseline comparison established" --criterion "At least one reliable experiment recorded"

python scripts/update_project.py link /PROJECT/ROOT BASE-0001 BR-0001 --relation member-of
python scripts/update_project.py link /PROJECT/ROOT BASE-0001 BR-0002 --relation member-of
python scripts/update_project.py link /PROJECT/ROOT BR-0001 MILE-0001 --relation contributes-to

python scripts/v02_project.py milestone-evidence /PROJECT/ROOT --milestone MILE-0001 --criterion C-001 --evidence-id RES-0001 --reason "Experiment artifact reviewed"
python scripts/v02_project.py milestone-accept /PROJECT/ROOT --milestone MILE-0001 --approval-note "Human reviewed all criterion evidence" --actor mentor
~~~

A shared Baseline links to multiple ResearchBranches without copying its scientific record. A Milestone requires explicit human acceptance and evidence for each criterion. A completed task never automatically validates a scientific claim. Actor CLI flags are declarations, not authentication.

## #4 — Claim–Evidence links

~~~bash
python scripts/v02_project.py evidence-link /PROJECT/ROOT --claim CLAIM-0001 --evidence-id SRC-0001 --stance qualifies --quality unverified --scope "Author claim in abstract only" --locator "Abstract"
python scripts/v02_project.py evidence-link /PROJECT/ROOT --claim CLAIM-0001 --evidence-id RES-0001 --stance contradicts --quality experiment-observed --scope "Toy data n=2" --locator "research/03-experiments/logs/toy.txt"
python scripts/v02_project.py evidence-show /PROJECT/ROOT --claim CLAIM-0001
~~~

source-checked requires an original source explicitly inspected; experiment-observed requires a Result with observation and artifact path, but software cannot guarantee the underlying experiment was valid. Contradiction marks affected claims and downstream entities for review. No automatic upgrading of epistemic truth.

## #5 — External SessionRef records, no chat ingestion

~~~bash
python scripts/v02_project.py session-create /PROJECT/ROOT --provider codex --workspace "project-A" --session-id "actual-session-id"
python scripts/v02_project.py session-link /PROJECT/ROOT --session-ref SESS-0001 --entity-id IDEA-0001 --role idea-origin
python scripts/v02_project.py session-link /PROJECT/ROOT --session-ref SESS-0001 --entity-id CLAIM-0001 --role decision
python scripts/v02_project.py session-list /PROJECT/ROOT
python scripts/v02_project.py session-unlink /PROJECT/ROOT --session-ref SESS-0001 --entity-id CLAIM-0001
~~~

One SessionRef may point to several entities, and one entity may link to multiple sessions. Session identifiers are not full chat contents. HTTPS URL syntax does not mean a provider deep link is known to work; until verified, show/copy IDs, do not auto-open links.

## Tests

~~~bash
python -m unittest discover -s evals -p 'test_*.py' -v
python evals/make_demo.py /tmp/research-navigator-demo
python scripts/validate_state.py /tmp/research-navigator-demo
~~~

Canvas UX and approved browser writeback are later issues (#6–#12). This CLI is not an interactive graphical editor.
