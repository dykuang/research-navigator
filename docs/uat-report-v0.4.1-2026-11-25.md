# v0.4.1 Synthetic Multi-Round Grilling & Recovery UAT — 2026-11-25

Scope: automated state/CLI/HTML validation of **fictional** research interview processes, not actual LLM interviewing quality, real Codex Skill activation inheritance, real scientific studies or authenticated human approval.

## Scenario: seven turns across a simulated independent Session

| Round | Researcher behavior | Required behavior | Observed |
|---|---|---|---|
| 1 | Explicitly start interview, define ambiguous research topic | Start persisted `active` interview, ask high-value independent questions | PASS |
| 2 | Answer first question, defer metric | Persist confirmation + deferral, keep dependent question blocked | PASS |
| 3 | Pause, then resume from the same project in a new context | Reload previous confirmed answer and frontier, no re-initialization | PASS |
| 4 | Clarify metric and propose minimal experiment | Unblock dependent question only after confirming prerequisite | PASS |
| 5 | Agent suggests ending and researcher disagrees | Enter `consensus-review`, refuse implicit exit, return to `active` | PASS |
| 6 | Clarify budget and explicitly accept consensus | Record human-attributed confirmation, mark `completed` | PASS |
| 7 | Generate Canvas/HTML and continue normal mode | No open grilling queue, no canonical scientific state write, no false evidence status | PASS |

Additional Python tests cover versioned writes, cross-process CLI handoff, changing confirmed premises, accepted open questions, project isolation, corrupt sidecar failure, no accidental overwrite, AGENTS.md opt-in/non-overwrite, prompt-injection-like strings, browser HTML escaping, and no implicit project initialization.

All simulated project directories, experimental materials and generated HTML are created inside `tempfile.TemporaryDirectory` and removed after the tests. The test code remains versioned for reproducibility. The dedicated multi-round script explicitly asserts the fixture path is absent after exit.

## Security and conceptual checks

- **Skill activation vs state persistence:** new independent Codex chats do not inherit a Skill invocation by guarantee. CLI `handoff` reads the persisted interview; `AGENTS.md` is optional and installed only after `--apply`.
- **Scientific truth:** confirmed conversational answers are not promoted to `research/state` as verified scientific evidence; interview sidecar is separate.
- **Human review:** exit requires `request-exit` and user/mentor `confirm-exit` with explicit acceptance of every unresolved item; CLI actor is not cryptographic identity verification.
- **Post-exit:** completed or abandoned interviews report an empty active question frontier, even if the user accepted some unresolved questions.
- **HTML:** self-contained read-only snapshot, escaped untrusted text, no direct approval or execution behavior, mobile layout checked in Chromium.
- **No transcript duplication:** handoff includes selected confirmed answers and remaining questions, not original session message history.

## CI

- [Validation workflow](../.github/workflows/validate-v041.yml) runs Linux Python 3.10, Linux Python 3.12, native Windows Python 3.12, full legacy unit suites, existing v0.4 six-scenario synthetic UAT, new seven-round UAT, and Chromium interview/decision UI regression.
- [Latest feature CI (check current result)](https://github.com/dykuang/research-navigator/actions/workflows/validate-v041.yml).
- Previous green fully configured validation: [run #45598168864](https://github.com/dykuang/research-navigator/actions/runs/45598168864): 162 Python tests/platform, multi-round interview UAT passed, six v0.4 user journeys passed, Chromium passed.
- Later commits add cross-process recovery validation and a post-exit frontier fix; the **final** release gate must use successful CI from the final branch SHA, not the previous green run.

## Known real-client limitations

Native GitHub Windows runner verifies Python/CLI, **not** installation or live behavior on the user's own Codex desktop. No completed automatic acceptance claim for an actual Codex Skill handshake, provider SessionRef deep linking, or continuation without explicit invocation. Those must be assessed manually with the researcher's installed Codex client; `AGENTS.md` only provides project-local guidance.
