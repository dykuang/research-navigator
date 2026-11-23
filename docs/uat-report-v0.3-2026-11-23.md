# v0.3 Multi-Round Researcher UAT — 2026-11-23

**Scope:** fictional/synthetic research scenarios; **not** real client installation, real paper validation, real experiment execution, or human identity verification. Five isolated projects under Python `tempfile.TemporaryDirectory`; each project and any generated HTML/log files were deleted automatically after its scenario. No fixture projects were checked into the repository.

## Five simulated researcher journeys

| Persona and rounds | Expected behavior | Verified |
|---|---|---|
| New student (4) | vague question → unverified abstract → planned Run does not imply completed experiment → negative toy result remains uncertain | PASS |
| Branch exploration (4) | shared Baseline and A/B routes → weak negative in A → park A → refuse additional Run under A while B/Baseline remain usable | PASS after #29 fix |
| Supervisor (4) | review scoped support+contradiction → no scientific auto-proof → invalidate leaky Run → Result retained, dependent Claim blocked | PASS |
| Decision provenance (4) | SessionRef pointer → genuine event-linked trace → fabricated event and false approval rejected → graph read-only | PASS |
| Offline Canvas (2) | HTML generation and escaping → read-only reinspection → no approval or scientific mutation | PASS |

### Finding #29: archived ResearchBranch did not block Run attempts

Initial synthetic multi-round UAT: **4/5 passed**, archive Round 4 allowed an invalid `ExperimentRun` because the v0.3 registry only checked the immediate Experiment's own lifecycle/impact, not its `member-of` ResearchBranch.

- Failing CI evidence: [run #45122942631](https://github.com/dykuang/research-navigator/actions/runs/45122942631).
- Tracked in [Issue #29](https://github.com/dykuang/research-navigator/issues/29).
- Fixed in `scripts/rn_reasoning.py` by following direct/transitive `member-of` branch ancestry and refusing an archived, stale or blocked route. Check runs both when planning and when recording, including plans created before a route was parked.
- Three additional dedicated regression tests cover direct archive, pre-planned run followed by archive, and nested branch quarantine. Shared Baseline/independent B remain unchanged.

### Final executed verification

- [v0.3 CI #45123098505](https://github.com/dykuang/research-navigator/actions/runs/45123098505) **SUCCESS**: 126 Python tests each on Linux 3.10, Linux 3.12 and native Windows 3.12; five multi-round journeys passed in every configured platform; real Chromium v0.3 reasoning inspector passed.
- [v0.2 CI #45123098575](https://github.com/dykuang/research-navigator/actions/runs/45123098575) **SUCCESS**: existing v0.1/v0.2 Linux/Windows Python regressions, Chromium canvas/semantic/session checks and seven prior synthetic UAT journeys.
- Test content, logs, paper references, run metrics and sessions are explicitly **SYNTHETIC FIXTURE**, not real scientific evidence.

### Remaining non-code limitation

Actual owner Windows/Codex Skill discovery and real provider SessionRef deep-link behavior cannot be inferred from GitHub Actions or fictional sessions; see existing [#15](https://github.com/dykuang/research-navigator/issues/15). CLI `--actor` is a declared actor, not an authenticated user. Scientific validity still needs genuine evidence and researcher judgment.

### Cleanup

- Each v0.3 journey uses a `TemporaryDirectory` and asserts its path no longer exists when the context exits.
- Transient CI workspaces are disposed by GitHub Actions, and generated screenshots/artifacts from existing v0.2 CI remain confined to GitHub Actions' expiring test artifacts; no demo research project, invented experiment log, real transcript or simulated approval was committed to the repository.
- The persistent `evals/uat_v03_multiround.py` script and `evals/test_v03.py` regressions are intentionally retained as reproducible quality guards.
