# v0.2 user acceptance retest — 2026-11-23

**Status:** All seven independent synthetic user journeys passed in **strict** Chromium mode after correcting three reproducible defects, without overwriting any real user project data.

## Before / after

| Scenario | Initial result | Retest |
|---|---|---|
| Chinese project novice / offline JSON draft | PASS | PASS |
| A/B/C shared Baseline, Idea archive & two approvals | PASS | PASS |
| SessionRef many-to-many roles and no fabricated links | PASS | PASS |
| Concurrent proposal conflict refuses stale write | PASS | PASS |
| Archived ResearchBranch → new hypothesis branch | **FAIL** | **PASS**, explicit freshly reviewed goal and stop conditions required |
| Connected Canvas → classic Dashboard link | **HTTP 404** | **PASS**, actual Chromium click; anonymous shell has no project data; token-protected state API |
| Mobile 390px Canvas inspector | **Unavailable** | **PASS**, responsive drawer opens/closes; detail, SessionRef and proposals accessible after animation |

**Evidence:** [strict GitHub Actions run #45106298967](https://github.com/dykuang/research-navigator/actions/runs/45106298967), browser job `Seven simulated user journeys (strict release gate)`. The log prints `UAT_RESULTS_JSON={"pass": 7, "issue": 0}`. Download JSON, synthetic desktop screenshot and 390px mobile screenshot from the run artifact `v02-uat-user-journeys`. Initial failing evidence is preserved in [previous UAT report](uat-report-v0.2-2026-11-23.md) and [initial run](https://github.com/dykuang/research-navigator/actions/runs/45104666074).

The workflow now runs `python evals/uat_user_journeys.py --strict`, which fails CI if a scenario explicitly reports an issue or raises an exception. Existing unit and regression tests are run separately. The new branch test explicitly checks missing/blank `goal` or `stop_conditions` fail before enqueuing, while the original archived branch's scientific metadata and a shared Baseline remain untouched.

## Fixes and safety properties

- [#17](https://github.com/dykuang/research-navigator/issues/17): `approve-revival-candidate` now requires a new goal and nonempty stop conditions for `ResearchBranch`. The selected Branch's editor draft has explicit fields. The original archived Branch, historical negative Result and scientific provenance are preserved. A candidate remains a hypothesis, not a validated result.
- [#18](https://github.com/dykuang/research-navigator/issues/18): the localhost Bridge serves a **data-free** classic Dashboard HTML shell and a separately token-guarded `GET /api/dashboard`, which reads canonical state without writing it. Offline classic HTML keeps its original bundled snapshot. A browser test follows the real Canvas header link, checks rendered research title/graph and confirms anonymous API access is forbidden.
- [#19](https://github.com/dykuang/research-navigator/issues/19): the mobile Canvas has an accessible **详情 / 提案** drawer, a back-to-canvas close control, and automatic node-selection opening. Playwright waits for the 180ms CSS transition and verifies actual visibility and control operation, rather than taking an immediate first-frame screenshot as proof.

**Remaining release gate:** [#15](https://github.com/dykuang/research-navigator/issues/15) — real owner's Windows/Codex app and actual SessionRef navigation remain **unverified**. This retest used synthetic projects and Chromium in CI; it does not constitute installation on the user's computer or real Codex deeplink verification. [Draft PR #16](https://github.com/dykuang/research-navigator/pull/16) should remain draft until release authorization and those separate gates are satisfied.
