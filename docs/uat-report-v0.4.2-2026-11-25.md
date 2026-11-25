# v0.4.2 Grilling Interactive Questions — Synthetic UAT (2026-11-25)

## Scope

Fictional user journeys and deterministic interface/CLI testing, not real scientific studies, authenticated user identity, or a live Codex desktop popup. New multi-round fixtures use Python `tempfile.TemporaryDirectory`; test data, generated HTML and synthetic logs are removed on exit.

## End-to-end seven-round researcher journey

| Round | Researcher/Agent action | Expected behavior |
|---|---|---|
| 1 | Start interview, present typed A/B choices | Stable IDs and visible Other, not automatic acceptance |
| 2 | Pick Other for a new research objective | Original custom text saved, not coerced to Agent recommendation |
| 3 | Answer dependent question using a listed choice | Only unlock after prerequisite confirmation |
| 4 | Pause, switch context and recover from project | Handoff retains accepted choice or original custom answer |
| 5 | Revise earlier confirmed answer | Invalidate previously confirmed dependent decisions |
| 6 | Reject premature exit, then specify another choice | Grilling continues and no Agent self-approval |
| 7 | Explicitly approve consensus, build offline Canvas | Normal state after exit; no scientific-state modification |

Dedicated `evals/uat_v042_multiround.py` validates all seven fictional rounds, and asserts temporary project directory cleanup.

## Additional automated validations

- Legacy v0.4.1 sidecars without typed fields remain readable.
- Typed-only new questions, stable option IDs, duplicate/invalid IDs, recommended ID, long/blank Other, mutually exclusive answer modes, revision and dependency handling.
- Native blocking `request_user_input` 2–3 option payload with recommended-first label and no manually supplied Other; read-only response-to-choice resolver rejects ambiguity.
- Native nonblocking `request_user_input_async` payload with title and string options. Its `accepted=true` tool acknowledgement never counts as a human answer; subsequent user text is resolved separately and must be confirmed.
- Text fallback for more than three options and for legacy string-only questions.
- Offline Chromium radio cards, Other textarea and copyable unsaved draft; hidden input and XSS escaping, mobile viewport, old interview view regression.
- Full existing v0.1–v0.4.1 Python, Chromium and six earlier synthetic research journeys.

## CI evidence

- [Green pre-async UI/choice build](https://github.com/dykuang/research-navigator/actions/runs/45644563189): all four GitHub Actions jobs succeeded (Linux 3.10/3.12, native Windows 3.12 and Chromium); 179 Python tests/platform and multi-round UAT passed.
- Subsequent changes added v0.4.2 async adapter and recovery coverage. **The final current-head CI result must be checked separately before marking the release gate complete.**
- [Workflow](../.github/workflows/validate-v042.yml): no real client tools invoked by CLI, only deterministic previews. Windows Codex UI may differ from browser CI.

## Cleanup and limitations

No synthetic research project or generated dashboard is committed. Reusable fixtures/test scripts and this report are committed intentionally. Browser UI is an offline draft tool; it cannot submit answers. Real Codex `request_user_input` or `request_user_input_async` rendering depends on the user's mode, client version, and tool availability; printed JSON is **not** proof of a native picker.

## Modal unavailable/failure protection — final additional UAT

Added Issue [#56](https://github.com/dykuang/research-navigator/issues/56) to guarantee the **ordinary chat** fallback if Codex native question UI is missing, errors, is cancelled/timed out, or does not return an actual user answer. `interview.py ROOT present --question Q-ID` always supplies a complete `fallback_text` containing listed choices, `其他／自定义` and `补充说明（可选）`. Native candidates are only generated with explicitly declared runtime capability; CLI does not itself invoke a popup. Sync/async tool failures and async delivery acknowledgement are not user confirmations.

Supplementary explanations via `answer --choice ID --supplement '...'` and `answer --choice other --custom-answer '...' --supplement '...'` are stored separately from the selected option / Other original text, appear in handoff and are cleared for invalidated downstream questions. Offline Canvas offers an additional input even with a preset choice; it only creates an **unsaved** draft. Regression includes missing tool, error, timeout, cancellation, no answer, >3 options, legacy questions, async acknowledgement, cross-session supplement retention, and browser UI. User-visible native Codex on the owner's machine is not proven by CI.
