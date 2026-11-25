# Research Navigator · Session Handoff

> 只写与下次会话有关的摘要，不复制完整 JSON 状态。

- 项目根目录：`<path>`
- 上次会话日期：`<date>`
- 当前焦点模块：`<module>`
- 当前研究问题及实体 ID：`<question> / <ID>`
- 新确认的用户决定：`<item IDs / decision IDs>`
- 等待用户回答的 frontier：`<2–5 independent questions>`
- 未经验证的关键主张：`<IDs + required action>`
- 阻塞/归档的方案：`<IDs + reasons>`
- 下一步工具命令/动作：`<command>`
- 离线看板：`research/dashboard/index.html`

## v0.4.1 Grilling 访谈恢复补充

- 持久访谈状态路径：`research/interviews/current.json`（如尚未显式开始则不存在）
- 访谈 ID、状态、修订、待回答问题：用 `python scripts/interview.py PROJECT_ROOT handoff` **只读**取得，不复制整个聊天记录。
- 新的 Codex Session 必须显式调用 Research Navigator 或依赖用户主动安装的项目 `AGENTS.md` 引导；不会自动继承原会话的 Skill 激活。
- 若状态是 `completed`：普通科研对话继续，不自动恢复密集 Grilling。
