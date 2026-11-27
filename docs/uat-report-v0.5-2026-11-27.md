# v0.5 synthetic CI evidence and release blockers

Baseline tested: `01044b3a734740256260ac4ac2f1aa528b4dc6f0` on PR #66.

All five legacy CI workflows completed successfully:
- v0.2: https://github.com/dykuang/research-navigator/actions/runs/46024314889
- v0.3: https://github.com/dykuang/research-navigator/actions/runs/46024314704
- v0.4: https://github.com/dykuang/research-navigator/actions/runs/46024314708
- v0.4.1: https://github.com/dykuang/research-navigator/actions/runs/46024314803
- v0.4.2: https://github.com/dykuang/research-navigator/actions/runs/46024314665

Ubuntu Python 3.12 log explicitly reports 204 tests, including new Harness adapter, installer, cross-process handoff, and DeepSeek SessionRef tests. Ubuntu 3.10 and Windows 3.12 jobs passed. Chromium SessionRef/semantic editor checks and existing synthetic user journeys passed. Interview UAT reports synthetic project and generated HTML removed.

Follow-up code review: installed CLI generates Python bytecode caches, so strict original manifest comparison could incorrectly block normal uninstall. Add narrowly scoped cache recognition for tracked Python sources and a regression that runs the installed CLI before uninstall, refuses unknown cache files, then verifies project state survives. This follow-up requires its own CI run; baseline green does not certify it.

## Actual-client release gates (not performed)
1. Use a temporary synthetic workspace; install both skills in a real DSH environment, verify both are listed and explicitly load them.
2. Start a real interview and exercise blocking ask_user_question with a fixed choice, Other, supplement, deliberate skip, and normal chat fallback with tool unavailable. Confirm that no skipped or pending response becomes a confirmed answer.
3. Move to an independent Codex session and back to DSH, using the same project root and explicit skill activation; verify persisted answers/frontier, stale revision rejection and explicit exit.
4. Register actual session IDs and verify canvas filters and no invented deep links. Verify sandbox, remote model data and logging policy using synthetic content only.
5. Uninstall and remove only the synthetic fixture after reviewing paths; retain the actual research project and user files. Record client versions, environment and results.

No actual DSH UI or user computer was accessible in this run. No release or merge until the release gate is satisfied.
