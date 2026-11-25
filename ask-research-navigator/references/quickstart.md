# Research Navigator 快速开始（学生版）

## 不需要学习命令：直接对话

1. **告诉 Agent 你的研究起点**：例如「使用 ask-research-navigator，我只知道大概想研究小样本视觉泛化，你推荐从哪个模块开始？不要建立文件。」
2. **确定研究项目位置并启动**：当你愿意保存进度时说「使用 research-navigator，在我的项目目录中开始选题访谈。先检查已有文件、询问我再初始化。」Agent 会逐轮追问，并保留已确定和仍不确定的区分。
3. **继续或调整**：之后说「使用 research-navigator，读取当前状态，告诉我接下来最重要的一个问题」；或者「实验结果不好，请先分析原因，暂时不要归档」。

## 导航命令（自然语言优先）

- `ask-research-navigator`: 用法帮助、选择模块、解释状态、使用边界。
- `research-navigator`: 开始和继续科研工作；保持术语、证据、决策和实验记录。

用户端快捷入口由具体 Agent 支持情况决定；在 Codex 等支持 Skills 的环境可尝试显式调用 `$ask-research-navigator` 或自然语言“使用 ask-research-navigator”。不同客户端的斜杠命令不一定相同，不要保证任何客户端都支持 `/ask-research-navigator`。

## 六个可以直接复制的问题

1. 「我刚接触 Research Navigator，请用学生能理解的方式介绍我最应该知道的三件事。」
2. 「我只有一个模糊科研想法，帮我决定应该从哪里开始，暂时不要创建文件。」
3. 「我的项目已经有文献和实验记录了，我该从哪个模块继续？先只读查看。」
4. 「我已经选了 Baseline，但不知道实验协议怎样才公平。」
5. 「当前方法失败了，我可以如何搁置它，而不影响未来的回收？」
6. 「我下周需要做组会汇报，Research Navigator 能整理哪些可信的内容？」

## 重要提醒

- 是否实际写盘取决于 Agent 是否获得项目根目录和用户授权。
- 默认不会“通过对话自动验证”论文、实验效果或学术创新性；要留下可追踪的来源和复核步骤。
- 已搁置的方法不会默认回到正向规划，但历史负结果仍会用于风险检查。

## v0.2 画布快捷步骤（合成演示项目）

~~~powershell
$env:PYTHONUTF8='1'
python evals/make_demo.py C:\\Temp\\rn-synthetic
python scripts/build_dashboard.py C:\\Temp\\rn-synthetic
# 打开 C:\\Temp\\rn-synthetic\\research\\canvas\\index.html
~~~

这是**合成研究数据**，不代表真实学术论文或实验验证。离线画布只能移动和导出布局/提案草稿；如需受控科研变更，运行 `python scripts/local_editor.py serve PROJECT_ROOT` 并在交互终端逐条审查批准。Codex SessionRef 目前只支持会话 ID 关联、筛选和复制，不承诺自动打开会话。

## v0.4.1 在一个或多个会话中持续 Grilling

**同一对话中**：说「使用 research-navigator，在我的项目中启动持续科研 Grilling，逐轮追问直到我明确确认退出」，然后直接回答每一轮问题。Agent 应记录共识与待回答问题。

**换一个完全独立的对话**：再次明确调用 `$research-navigator`，提供**同一项目根目录**，说「请读取持久访谈进度，不要重新从头问」。新对话不会天然继承此前的 Skill 上下文；存档让恢复成为可能，但不是自动激活。

**退出**：Agent 先汇总已解决、未解决和需要进一步实验的事项并请求审核；你明确同意后才进入普通科研助手模式。完整命令见 `research-navigator/references/interview-v041.md`。
