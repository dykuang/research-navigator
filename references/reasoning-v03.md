# Research Navigator v0.3 · Experiment runs, claim review, decision replay

This is an **additive** v0.3 feature layer on a canonical project whose
`research/state/project.json.schema_version` remains `0.2.0`.
There is **no silent migration**. Use the existing v0.1→v0.2
`migrate_state.py preview/apply/recover` before v0.3 commands if necessary.
Existing project backups and journal recovery continue to apply.

## 1. Work from an existing project root

```bash
python scripts/validate_state.py PROJECT_ROOT
python scripts/v03_project.py --help
```

Do not run `init` over existing state. Use the user's real project root, not
the Skill installation directory. The v0.3 commands use the same
`workspace_lock` / rollback journal as the canonical v0.2 state.

## 2. Record a real experiment attempt

Create an Experiment first via the existing v0.2 or v0.1 CLI. Next:

```bash
python scripts/v03_project.py run-plan PROJECT_ROOT \
  --experiment EXP-0001 --title "Control trial / attempt 1" --attempt 1
```

**Planning does not launch or confirm an experiment.** Only after an experiment
actually ran and the user has verified a *project-local* artifact:

```bash
python scripts/v03_project.py run-record PROJECT_ROOT \
  --run RUN-0001 --dataset "Dataset-A, version 2026-11" \
  --protocol "registered protocol v1; fixed split" \
  --code-revision "actual Git commit SHA or documented revision" \
  --seed 42 --artifact research/03-experiments/run-0001.log \
  --observation "actual observed experimental measurements, including limitations" \
  --outcome inconclusive --metric 'F1=0.620:ratio:higher' \
  --started-at 2026-11-23T10:00:00+08:00 \
  --ended-at 2026-11-23T11:00:00+08:00
```

The command checks that the file exists, resolves within `PROJECT_ROOT`,
computes SHA-256, creates a separate Result entity and links it to
`ExperimentRun`. The record does **not** assert statistical significance,
human signoff or source correctness. The `--synthetic` switch is required
for intentionally fabricated **test fixtures**, and is not a license to
fabricate results in a real research project.

List runs:

```bash
python scripts/v03_project.py run-list PROJECT_ROOT --experiment EXP-0001
```

If the evaluation protocol later proves invalid, preserve old observations:

```bash
python scripts/v03_project.py run-invalidate PROJECT_ROOT \
  --run RUN-0001 \
  --reason "Evaluation leakage discovered; protocol not valid"
```

This marks the Run and Result unusable for positive claims, and flags
downstream claims `blocked`; original observed values and artifacts remain.

## 3. Review scoped claim evidence

Create and link scoped evidence using the existing v0.2
`scripts/v02_project.py evidence-link`. Then:

```bash
python scripts/v03_project.py claim-analyze PROJECT_ROOT --claim CLAIM-0001
```

The report lists evidence stance, quality, scope, locator and invalidation flag.
`possible_conflict=true` only indicates that support and contradiction were
both recorded. Different scopes may make them compatible. No AI-generated
"confidence score" or automatic true/false promotion is provided.

## 4. Trace research decisions without hallucinating history

Register actual Decision items and SessionRef IDs using existing commands.
Then optionally attach *existing* append-only event IDs to a DecisionTrace:

```bash
python scripts/v03_project.py trace-create PROJECT_ROOT \
  --decision DEC-0001 --title "Why route B was preferred" \
  --scope "Target domain X under fixed compute" \
  --option "Run additional A ablation" \
  --option "Pilot B" --selected "Pilot B" \
  --rationale "B may distinguish two hypotheses at lower cost; still unverified" \
  --run-id RUN-0001 --claim-id CLAIM-0001 \
  --event-id ACTUAL_EXISTING_EVENT_UUID \
  --session-ref ACTUAL_REGISTERED_SREF_ID
```

All references must already exist. You may omit the optional `--event-id`
or `--session-ref` when unknown; **never invent them**. The caller can only
add an `--approval-event-id` if that existing event documents a
human-attributed approval. The resulting trace is not automatically
`user-confirmed`.

```bash
python scripts/v03_project.py trace-replay PROJECT_ROOT --trace TRACE-0001
```

Output includes actual listed event records and SessionRef pointer metadata.
Missing messages, citations, session pages and historical states are **not**
synthesized.

## 5. Inspect the graph

```bash
python scripts/graph_projection.py PROJECT_ROOT --view reasoning
python scripts/build_dashboard.py PROJECT_ROOT
```

Open the generated Research Canvas and select **科学推理 · Reasoning**.
The inspector exposes typed run metadata and trace references, but no
direct `run-record` or `trace-create` browser writeback is implemented in
this version. The v0.2 local proposal bridge's terminal approval constraints
remain in place for previously supported operations.

## Limitations and ethics

- No built-in experiment executor, cloud study tracker or live academic source verifier.
- CLI `--actor` is an audit declaration, not identity authentication.
- Local artifact existence/SHA-256 confirms file bytes at recording time,
  not scientific truth, experimental quality or research ethics compliance.
- Timezone-aware timestamps, protocol versions, dataset identifiers and
  code revisions must reflect genuine work; fields cannot auto-verify them.
- Cross-platform CI runs synthetic exercises, **not** a real Windows Codex
  client session or a physical experiment.
