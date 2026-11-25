# v0.4.2 — Interactive Grilling Questions

GitHub milestone [#4](https://github.com/dykuang/research-navigator/milestone/4); dependency Issues #49–#54, release tracker #48. Base: v0.4.1 merged main.

## Structured choices

The old `options` string is retained for backwards compatibility. A question may now include a `choices` array (2–12 objects), each with a stable `id`, display `label`, and human-readable `description`, optionally a `recommended_choice_id`. The legacy `options` summary is optional when `choices` exists. Never insert ID `other` among model options: every supported surface must supply an independent Other/free-form route.

Example:
```json
{
  "text":"你希望优化什么？",
  "why":"目标决定实验指标",
  "recommendation":"优先检查跨域 F1",
  "lowest_cost_check":"固定验证集的小型对照",
  "depends_on":[],
  "choices":[
    {"id":"accuracy","label":"提高精度","description":"优化跨域 F1"},
    {"id":"cost","label":"降低成本","description":"减少 GPU 时间"}
  ],
  "recommended_choice_id":"accuracy"
}
```

## CLI usage

```bash
python scripts/interview.py PROJECT_ROOT add-questions --questions-json '[{"text":"目标？","why":"影响实验","recommendation":"先选指标","lowest_cost_check":"小测试","choices":[{"id":"a","label":"精度","description":"提高 F1"},{"id":"b","label":"成本","description":"节约 GPU"}]}]'
python scripts/interview.py PROJECT_ROOT next
python scripts/interview.py PROJECT_ROOT answer --question Q-0001 --choice a --actor user
python scripts/interview.py PROJECT_ROOT answer --question Q-0001 --choice other --custom-answer "我更关心鲁棒性" --revise --actor user
# Original 0.4.1 free-text syntax still works:
python scripts/interview.py PROJECT_ROOT answer --question Q-0001 --text "自定义" --actor user
```

The new fields `selected_option_id`, `custom_answer`, and `answer_source` are added to confirmed question answers; raw user custom text is preserved exactly after surrounding whitespace normalization. Revising a confirmed answer invalidates downstream confirmed questions. Confirmed answers still require real explicit user/mentor approval; CLI `--actor` is not identity verification. This never changes canonical science state.

## Native Codex UI — capability dependent

The agent must first determine whether the actual Codex client/mode exposes the native `request_user_input` tool. Where offered, it can submit 1–3 questions per request, with 2–3 mutually exclusive options for each; Codex supplies Other/free-form itself. This Skill **cannot activate or invoke a missing tool**, and the CLI only generates an adapter preview rather than claiming a popup appeared.

```bash
python scripts/interview.py PROJECT_ROOT native-request --question Q-0001
python scripts/interview.py PROJECT_ROOT prompt --question Q-0001
python scripts/interview.py PROJECT_ROOT resolve-native --question Q-0001 --response-json '{"answers":{"q_0001":{"selected":["Other"],"other":"新的想法"}}}'
```

`native-request` returns `tool_name` and `tool_arguments`, `tool_called=false`, `must_check_runtime_capability=true`. A live agent may use the *real* available Codex tool, then use `resolve-native` to interpret a user response into a stable choice ID, then after genuine confirmation call `answer`. Unknown, ambiguous, mismatched, or multiple options must be clarified, never invented. Recommended option appears first with a native `(Recommended)` label.

When the native tool is unavailable, when there are more than three choices, or when the question is a legacy string-only question, show `prompt` as plain text listing all options plus Other/free input. Do not claim an interactive UI has been rendered in that case.

## Offline Canvas

The `research/canvas/interview.html` view now has radio cards, a custom Other textarea, and a button to generate a draft. The generated draft is **not written to project state or confirmed**; users must paste it back into Codex for further discussion. Untrusted text uses textContent and escaped embedded JSON; mobile/keyboard flow is covered by browser tests.

## Safety and compatibility

- Existing v0.4.1 interview sidecars continue to load without migration or changes to `research/state/`.
- A new independent chat does not inherit an earlier Skill invocation. It must re-invoke the Skill or rely on user-opted-in project-local AGENTS guidance.
- A programmatically validated adapter **does not prove** actual native Codex desktop behavior. Real-client UAT remains necessary.
- No automated experiment execution, research claim promotion, silent archival revival, browser writeback or implicit Grilling exit.
- Tests use isolated synthetic projects and remove all temporary artifacts.

Native request guidance checked against public `openai/codex` source file `codex-rs/core/src/tools/handlers/request_user_input_spec.rs` (subject to client/mode changes).

## Codex Default-mode asynchronous questions

Some current Codex clients additionally expose `request_user_input_async`, with an **alternative schema** to the blocking `request_user_input`: `{"questions":[{"title":"...", "options":["A","B"]}]}`. It returns an immediate `{"accepted":true}` acknowledgement of delivery, **not a user selection or consent**. A user's answer arrives later as a separate message and must be confirmed before saving.

```bash
python scripts/interview.py PROJECT_ROOT async-request --question Q-0001
# After a real subsequent user response:
python scripts/interview.py PROJECT_ROOT resolve-async --question Q-0001 --text "新想法"
```

The agent must inspect the actual currently available tool names. Prefer a blocking picker where supported for a decision that must be answered before progressing. If only the async picker is offered, send the question, **do not continue dependent work until a real user message arrives**, and never treat `accepted=true` as an answer. If cards do not appear or remain pending unexpectedly, send the full text question via `prompt` rather than claim the UI succeeded. Native async display and reply lifecycle vary by client and OS; this adapter is a tested formatter, not an end-to-end client integration.

