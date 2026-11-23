# v0.2 independent simulated user acceptance report — 2026-11-23

**Scope:** current `v0.2` branch; independent use-case simulations with synthetic projects, actual Chromium browser and actual protected local HTTP Bridge. No owner's Windows/Codex installation was accessed. No real research data, academic claims, or user chats were imported.

**Reproducible evidence:** [GitHub Actions #45104666074](https://github.com/dykuang/research-navigator/actions/runs/45104666074), `browser` job → `Seven simulated user journeys (diagnostic)`; [download UAT JSON and desktop/mobile Chromium screenshots](https://github.com/dykuang/research-navigator/actions/runs/45104666074/artifacts/14786927497). Script: `python evals/uat_user_journeys.py`, optionally `--strict` to fail when user-visible defects are found.

## Outcome

| # | Synthetic user journey | Result | Evidence / notes |
|---|---|---|---|
| 01 | Novice creates Chinese project, views offline Canvas, exports a new Branch draft | PASS | Browser export JSON correct; controls are read-only; canonical state unchanged |
| 02 | Researcher shares Baseline across A/B/C, parks weak negative Idea A, runs two distinct revival approvals | PASS | Old negative Result untouched; independent B remains current; Milestone needs review; new candidate hypothetical |
| 03 | Agent user registers two SessionRefs; one session links to two entities and one Idea links to two sessions | PASS | Role display, workspace, provider filtering, manual ID fallback, no invented link or transcript |
| 04 | Two concurrent drafts submitted against the same revision, first approved | PASS | Second terminal approval rejected as stale; no silent overwrite; user must refresh and resubmit |
| 05 | Advisor revives an *archived ResearchBranch* into Branch v2 | **DEFECT** | Preview rejects `BR-0002: ResearchBranch must define a goal`, old remains safely in review; [#17](https://github.com/dykuang/research-navigator/issues/17) |
| 06 | Desktop user follows `返回经典工作台` from live `/canvas` | **DEFECT** | Link resolves to unsupported localhost `/dashboard/index.html`, HTTP 404; [#18](https://github.com/dykuang/research-navigator/issues/18) |
| 07 | Mobile 390×844 browser attempts to inspect node/SessionRef/semantic proposals | **DEFECT** | `#inspector` hidden by CSS `@media(max-width:680px)`; [#19](https://github.com/dykuang/research-navigator/issues/19) |

**Summary: 4/7 passed, 3 reproducible defects.**

### Severity / fix order

1. **P0 #17 — Science-domain workflow functionality:** restore complete Branch metadata only via *explicitly reviewed* new goal and stop conditions during second-stage revival. Do not alter original archived Branch/negative evidence; keep schema validation intact.
2. **P1 #18 — Broken navigation:** live Bridge Canvas should have a safe, functioning route back to classic dashboard, or should explicitly offer an offline-file workflow. Token-protect any route exposing research metadata.
3. **P1 #19 — Mobile accessibility:** implement a responsive detail/SessionRef panel or clearly identify desktop-only editing, with usable read-only details on mobile.

### Interpretation of other CI green checks

The same workflow has passing unit/regression jobs on Linux Python 3.10, 3.12 and native Windows Python 3.12, plus three existing browser-smoke jobs. **These automated results do not mean UAT passed.** The UAT script runs in *diagnostic* mode (exit 0 after emitting and storing observed defects), so its seven scenario outcomes must be read from the job logs or JSON artifact; `--strict` intentionally fails when any UAT defect remains.

### Notes and limits

- The terminal approvals in these isolated synthetic fixtures are deliberately simulated with `confirmed=True`; no real human authentication is claimed.
- The mobile viewport test asserts actual computed CSS, not whether the simulated user could install an Agent on a phone.
- The classic dashboard 404 is reproduced against localhost Bridge, not the independent offline HTML file (offline navigation remains covered by prior regressions).
- Real Codex provider deep links/owner's Windows client stay unverified under [#15](https://github.com/dykuang/research-navigator/issues/15).
- The initial `git clone` attempt in this execution environment could not resolve github.com; actual executable tests therefore ran on GitHub Actions against the current branch, and logs/artifacts were independently inspected via the GitHub connection. Do not claim the repo was installed locally in the user's machine.
- No fixes to the product code are included in this diagnostic UAT pass; defects are tracked separately in #17–#19.
