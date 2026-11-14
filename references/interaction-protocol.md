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
