# Interactive research grilling protocol

## Decision frontier

Build a dependency tree of research decisions. Do not ask dependent downstream questions until prerequisites are resolved. Each round typically has **2–5 independent high-impact questions** (fewer if the frontier is small). Questions are student-friendly and avoid reciting a large checklist.

For each question provide: (1) why its answer matters, (2) realistic options and trade-offs, (3) your recommended answer labeled as *source-backed*, *reasoned suggestion*, or *preference*, (4) the lowest-cost validation activity if the student cannot decide.

Never ask users to look up accessible facts you could verify yourself with authorized tools. The researcher, not the agent, chooses objectives, major trade-offs, final claims and expensive experiments. One question may branch into many later questions; do not silently assume branches are resolved.

## Conversation round

1. Read the project and recent events. Identify confirmed decisions, unresolved claims, approval needs, current limitations and stale dependents.
2. Select a coherent module focus. Optional modules may work in parallel; distinguish prerequisites from nice-to-have tasks.
3. Propose 2–5 frontier questions. Challenge overloaded terminology with examples and counterexamples; recommend precise operational definitions.
4. After answers, record confirmed definitions in `CONTEXT.md` (glossary only) and state using CLI. User assertions are labeled user-provided, not experiments. If there is an evidence ambiguity, write `uncertain` and mark human review.
5. Only create an ADR if (a) costly to reverse (b) surprising later (c) a real trade-off. Otherwise log a Decision item/event.
6. Validate and build dashboard; summarize in at most five short updates, each anchored to actual files or IDs. If you did not write files, say so.

## High-priority challenge prompts

- "可提升效果" → 哪项明确指标、哪套数据、哪种基线、提升多少才有意义？
- "创新" → 是任务创新、方法创新、数据、理论解释或应用？已有文献是否覆盖？
- "公平对照" → 训练预算、样本分割、预处理和指标是否一致？
- "实验失败" → 是工程未运行、观测到负面结果，还是重复次数不足？
- "回收旧思路" → 只读借鉴、开立复审，还是批准一个全新待验证候选？不能混淆。

## Avoid re-asking

Query existing items + relevant files first. If the student says "继续昨天的工作", summarize 2–3 established facts, 1–2 pending decisions, then resume the frontier, rather than asking the complete onboarding questions again.

## v0.4.1 Persistent Grilling rounds and stop handshake

This protocol applies **while** `research/interviews/current.json` reports `active` or `consensus-review`. It is not a globally sticky prompt. The user must explicitly invoke the Research Navigator Skill in a newly independent Agent/Codex chat, or opt into project-local `AGENTS.md` guidance; the file alone cannot activate a model or a Skill.

1. On entry, inspect the project and run `scripts/interview.py PROJECT_ROOT status` and `next`. If no sidecar and user requested Grilling, explicitly `start` after checking the project root. Otherwise do normal research work or help, without implicit start.
2. Present only the highest-value independent frontier questions (1–5), each with why it matters, alternatives and costs, reasoned recommendation, and a cheap way to decide. Persist unanswered questions with the CLI rather than repeating them on every turn.
3. After a user replies, **confirm or qualify** the answer before persisting it. Confirmed answer → `answered`; needs information → `deferred`; unresolved contradiction → `unresolved`. Never silently promote user assertions to peer-reviewed evidence; use normal research state commands for evidence.
4. Use the CLI's dependency DAG and `next` to select new questions. Do not advance an unconfirmed dependent question; do not re-ask a settled question unless a premise changed. Changes to confirmed premises require `--revise`, which marks downstream confirmed answers unresolved.
5. Periodically synthesize agreed definitions, assumptions, constraints, open scientific risks and the proposed next validation step. Even if no questions remain, ask for explicit exit confirmation.
6. Exit only via `request-exit` → review summary with user → `confirm-exit` by user/mentor, naming each accepted open issue. If they disagree, `reject-exit` and continue. On `completed`, normal assistant mode resumes; restart only by explicit `reopen` or a new interview after archiving the old record.

Cross-session handoff: use `scripts/interview.py PROJECT_ROOT handoff` (read-only) and pass the actual project location in the new session. This restores research interview state, not the prior chat text or implicit Skill activation. See `references/interview-v041.md`.

## v0.4.2 Question UX contract

Every high-value Grilling question must allow user-generated alternatives or a direct answer. Prefer 2–3 structured choices and a reasoned default, but always explain the Other/free-form route. Do not infer agreement because a recommended item was shown.

If an actual Codex `request_user_input` tool is available to this Agent in its current mode, call that real tool only with its documented 2–3 options per question and wait for the response; the native Codex UI supplies Other. The `native-request` CLI emits *only a preview JSON*, and must never be described as an actual popup. With no tool, a legacy question, or more than 3 choices, show a text fallback with all alternatives and explicit Other. Resolve the response to a stable option ID or exact custom text, ask for confirmation, and persist using `interview.py answer`. Preserve original answers and never convert a suggestion into scientific evidence.

