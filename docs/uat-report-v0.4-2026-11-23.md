# Research Navigator v0.4 — Owner-like Multi-Round Researcher UAT (2026-11-23)

## Scope and boundaries

- **Simulated research**, not real paper retrieval, real measurements, genuine user/mentor authentication, or a test of physical Windows Codex installation.
- Dedicated script: `evals/uat_v04_researcher_rounds.py` — six independent multi-round scenarios, each in `tempfile.TemporaryDirectory`. The scenario asserts the temporary project directory is absent after exit. Only reusable test source code, not fixture research records, remains committed.
- Existing `evals/uat_v04_multiround.py` and five v0.3 multi-round scenarios also run in CI. Browser test uses ephemeral Chromium fixture for desktop/mobile and the existing v0.3 inspector regression.
- Test results are **structural/behavioral** safety and UX invariants, not evidence of scientific validity.

## Six additional journeys

| Persona / conversation | Rounds | Verified |
|---|---:|---|
| New researcher: vague idea → abstract-only source → evidence-gap check → optional experiment proposal | 4 | PASS |
| Branch explorer: shared baseline A/B → one negative Run → park A → read-only archive exploration | 4 | PASS |
| Supervisor: scoped support/contradiction → invalidate affected toy Run → retain historical negative Result | 3 | PASS |
| Student + mentor: milestone scientific criteria → reject missing evidence → link partial evidence → read-only brief | 4 | PASS |
| Returning researcher: archive → inspect → formally review → explicitly approve derivative → HTML render | 5 | PASS |
| Security-oriented user: adversarial source title → reject agent self-approval → reopen state → HTML injection escaping | 4 | PASS |

**24 turns, 6/6 scenario journeys passed** on all configured Python/OS CI runners. Prior v0.3 five-scenario UAT and v0.4 one-scenario UAT also passed. All generated project artifacts are temporary, and fixture cleanup was checked.

## Findings and fixes

1. **Negative Run omitted from v0.4 decision opportunities:** recorded `negative`, `mixed`, or `inconclusive` outcomes could remain hidden once a Run existed. Added `EXPERIMENT_NEEDS_NEGATIVE_INTERPRETATION` with a scope-aware check and explicit human approval; invalidated runs do not generate active-run advice.
2. **Archive contamination of pending advisory queue:** parked/retired/quarantined items were included in ordinary pending human-review/impact warnings, creating redundant current-action noise. Split archival context from active decision gaps. Formal `under-revival-review` still appears in the review watchlist, and archived work remains excluded from positive opportunities.

Both fixes are in `scripts/rn_decision.py`. Regression script covers normal and adversarial cases, and no new canonical research truth state was added.

## Final CI evidence before release

- **Final feature-branch [v0.4 CI #45148465929](https://github.com/dykuang/research-navigator/actions/runs/45148465929)**: SUCCESS.
- Linux Python 3.10: 139 Python unit tests PASS + v0.3/v0.4 synthetic multi-round suites PASS.
- Linux Python 3.12: 139 Python unit tests PASS + v0.3/v0.4 synthetic multi-round suites PASS.
- Native Windows Python 3.12: 139 Python unit tests PASS + v0.3/v0.4 synthetic multi-round suites PASS.
- Chromium offline v0.4 decision board: PASS (filter, archive isolation, responsive layout, JS errors); v0.3 Canvas inspector regression: PASS.
- Pre-existing [v0.3 validation](https://github.com/dykuang/research-navigator/actions/runs/45137595432) and [v0.2 validation](https://github.com/dykuang/research-navigator/actions/runs/45137595374) on prior PR head: SUCCESS. Updated v0.4 branch retained these regression tests within full unit suite.

## Cleanup and limitations

- Python `TemporaryDirectory` removes simulated projects, fabricated experiments, archived routes and generated dashboards at end of each case. Both dedicated scripts explicitly check/print cleanup. GitHub-hosted runner workspaces are discarded after CI.
- No synthetic research artifacts, fake papers or mock study datasets are committed to repository; executable tests and this report are intentional permanent audit assets.
- CLI `--actor` and recorded decision metadata do not cryptographically authenticate humans. Browser decision view is read-only; actual semantic edits still pass through protected proposal + terminal approval flow.
- Physical owner's Codex/Windows setup and provider-dependent SessionRef deep links remain a separate real-client acceptance task [#15](https://github.com/dykuang/research-navigator/issues/15). CI does not claim to verify it.
