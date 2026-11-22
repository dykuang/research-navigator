# Research Navigator v0.2 development branch (v0.1 stable on main)

科研项目的交互式规划 + 可追溯状态 + 原生离线 HTML 工作台。面向五个互相联动的模块：选题、文献与基线、实验、路线调整、总结。核心能力是 `active / parked / quarantined / retired / under-revival-review` 的受控研究记忆，以及明确定义的证据/人审/结果状态。

## 安装

将整个 `research-navigator/` 文件夹解压到你的 Agent Skill 目录（例如 Codex 的 skills 目录）中，或在支持本地 Skill 的 Agent 中登记此目录。Skill 应读取根目录的 `SKILL.md`；不同 Agent 的安装路径和发现机制可能不同，本 ZIP 不会自动安装到你的账号/IDE。

## v0.2 已实现的数据与命令能力（Issues #2–#5）

当前开发分支在旧功能上新增了显式 schema 迁移/备份/恢复、版本冲突检查、ResearchBranch、科学验收型 Milestone、Claim–Evidence 关联，以及轻量 SessionRef（不读取聊天正文）。**无限画布和本地 UI 写回仍在开发计划中**，现有 HTML Dashboard 仍为只读。

- 升级已存在项目：先运行 `python scripts/migrate_state.py preview PROJECT_ROOT`，确认无误后运行 `python scripts/migrate_state.py apply PROJECT_ROOT`；出现事务残留时运行 `python scripts/migrate_state.py recover PROJECT_ROOT`。
- 创建和管理分支/里程碑、证据链、Agent SessionRef：使用 `python scripts/v02_project.py --help`，参考 [v0.2 操作示例](references/v02-operations.md) 和 [schema 契约](references/state-schema.md)。
- Agent/CLI 的人类授权要求未改变。 `--actor` 只记录声明，不是身份认证；URL 符合 HTTPS 不代表已验证 Codex 可跳转。

开发质量门槛：`python -m unittest discover -s evals -p 'test_*.py' -v`，GitHub Actions 在 Python 3.10/3.12 上运行相同套件。历史 v0.1 项目保留原始记录，不会静默迁移。

## v0.2 本地提案写回（#6）

新增可选的 **localhost-only proposal bridge**，只允许浏览器提交待确认的科研提案：`python scripts/local_editor.py serve PROJECT_ROOT`。它绑定 `127.0.0.1`，在终端打印一次性启动用的随机访问令牌 URL。浏览器仅能排队提案，不能直接批准或修改科研状态。

在**另一交互终端**运行 `python scripts/local_editor.py inspect PROJECT_ROOT PROPOSAL_ID`，确认具体内容，再通过 `approve` 或 `reject` 子命令逐条处理。审批要求交互 TTY 和完整确认字符串；提案的 revision 不匹配会被拒绝。详见 [安全与操作说明](references/local-bridge-security.md)。这是本机工作流防护，不是身份认证或云端多人协作服务。

现有 `research/dashboard/index.html` 依然完全离线、只读；正在规划的无限画布 #8/#10 尚未实现。

## 30 秒起步

需要 Python 3.10+，不需要第三方包。以下命令从 Skill 目录执行：

```bash
python scripts/update_project.py init /tmp/my-research --name '示例项目' --question '尚待精确定义'
python scripts/update_project.py add-item /tmp/my-research --type Idea --title '初步候选方向' --module topic --next-action '定义问题、指标与资源'
python scripts/validate_state.py /tmp/my-research
python scripts/query_research_items.py /tmp/my-research --mode planning
python scripts/build_dashboard.py /tmp/my-research
```

浏览器打开 `/tmp/my-research/research/dashboard/index.html`（实际位置以你指定的项目根目录为准）。现有项目请用 `summary`/`validate_state` 恢复，**不要再次 init**。

## 文件树

- `SKILL.md` — Agent 激活与协议入口
- `references/` — 访谈、证据、跨模块、状态机制、生命周期、HTML 合同、五模块协议
- `scripts/rn_core.py` — 规范状态模型、事件与安全状态变化
- `scripts/update_project.py` — CLI 创建、修改、关联、归档、回收、项目属性
- `scripts/query_research_items.py` — planning/risk/archive/synthesis 隔离查询
- `scripts/validate_state.py` — 状态和依赖关系校验
- `scripts/build_dashboard.py` — 只读离线 HTML + 派生归档卡
- `templates/` — 文献基线、话题、实验、导师审核、交接模板
- `evals/` — 自动化单元/集成测试、人工 Agent 交互评估

学生项目文件独立放在指定根目录下，默认有 `RESEARCH.md`、`research/state`、`research/dashboard`；归档按需生成。`CONTEXT.md` 术语表由 Agent 在用户确认术语定义后创建/维护。

## 已实现与限制

**已实现**：纯 stdlib 项目初始化、稳定 ID、主要实体状态、人工审批门槛（以 Agent 取得真实同意为前提）、关系校验和循环检测、跨依赖影响标注、追加式事件、归档卡、两阶段回收、新 ID 派生、程序化检索隔离、可搜索的纯离线 HTML/SVG 看板、模拟测试。

**当前限制**：CLI 中 `--actor` 是人为声明，不是身份认证；没有在线协作同步、数据库事务、跨机器文件锁、来源真实性自动联网核验、论文搜索 API、真实实验运行器或成本估算。Markdown 研究笔记由 Agent 按模板和已有结构持续维护，而非全部由 CLI 自动生成。工作台**不能**直接在浏览器内批准或保存；每次变更由 CLI 生成新版 HTML 快照。Archify 未启用：尚未检查其完整兼容 API/schema，原生 SVG 不依赖它。审计日志是 append-only 意图，不带防篡改密码学保证；应使用版本控制/备份确保高可靠性。结果工件路径需 Agent 实际核实，不能仅凭字段存在声称实验有效。

## 测试

```bash
python -m unittest discover -s evals -p 'test_*.py' -v
```

`evals/agent-scenarios.md` 包含需要在真实 Agent 环境验证的对话/审批/工具不可用场景；这些不能由纯 Python 测试冒充已通过。

## 许可证

MIT License，见 [LICENSE](LICENSE)。
