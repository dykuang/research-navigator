# Research Navigator · v0.4.0 Research Decision Intelligence

> v0.4.0 is the release target. Scientific decision outputs are read-only advisory projections, not automatic experiment execution or scientific verification. See [v0.4 UAT](docs/uat-report-v0.4-2026-11-23.md).

科研项目的交互式规划 + 可追溯状态 + 原生离线 HTML 工作台。面向五个互相联动的模块：选题、文献与基线、实验、路线调整、总结。核心能力是 `active / parked / quarantined / retired / under-revival-review` 的受控研究记忆，以及明确定义的证据/人审/结果状态。

## 安装

将整个 `research-navigator/` 文件夹解压到你的 Agent Skill 目录（例如 Codex 的 skills 目录）中，或在支持本地 Skill 的 Agent 中登记此目录。Skill 应读取根目录的 `SKILL.md`；不同 Agent 的安装路径和发现机制可能不同，本 ZIP 不会自动安装到你的账号/IDE。

## v0.2 已实现的数据与命令能力（Issues #2–#5）

当前开发分支在旧功能上新增了显式 schema 迁移/备份/恢复、版本冲突检查、ResearchBranch、科学验收型 Milestone、Claim–Evidence 关联，以及轻量 SessionRef（不读取聊天正文）。**#2–#5 的范围是数据层；后续 #6–#12 已在本开发分支实现受控提案 Bridge、交互画布、研究归档回收与 SessionRef UI。** 独立离线 HTML 仍为只读快照。

- 升级已存在项目：先运行 `python scripts/migrate_state.py preview PROJECT_ROOT`，确认无误后运行 `python scripts/migrate_state.py apply PROJECT_ROOT`；出现事务残留时运行 `python scripts/migrate_state.py recover PROJECT_ROOT`。
- 创建和管理分支/里程碑、证据链、Agent SessionRef：使用 `python scripts/v02_project.py --help`，参考 [v0.2 操作示例](references/v02-operations.md) 和 [schema 契约](references/state-schema.md)。
- Agent/CLI 的人类授权要求未改变。 `--actor` 只记录声明，不是身份认证；URL 符合 HTTPS 不代表已验证 Codex 可跳转。

开发质量门槛：`python -m unittest discover -s evals -p 'test_*.py' -v`，GitHub Actions 在 Python 3.10/3.12 上运行相同套件。历史 v0.1 项目保留原始记录，不会静默迁移。

## v0.2 本地提案写回（#6）

新增可选的 **localhost-only proposal bridge**，只允许浏览器提交待确认的科研提案：`python scripts/local_editor.py serve PROJECT_ROOT`。它绑定 `127.0.0.1`，在终端打印一次性启动用的随机访问令牌 URL。浏览器仅能排队提案，不能直接批准或修改科研状态。

在**另一交互终端**运行 `python scripts/local_editor.py inspect PROJECT_ROOT PROPOSAL_ID`，确认具体内容，再通过 `approve` 或 `reject` 子命令逐条处理。审批要求交互 TTY 和完整确认字符串；提案的 revision 不匹配会被拒绝。详见 [安全与操作说明](references/local-bridge-security.md)。这是本机工作流防护，不是身份认证或云端多人协作服务。

现有 `research/dashboard/index.html` 依然完全离线、只读；正在规划的无限画布 #8/#10 尚未实现。

## v0.2 无限科研画布（#7–#9）

已新增不依赖 CDN 或外部 JS 的**无限研究画布**。在项目根目录运行 `python scripts/build_dashboard.py PROJECT_ROOT` 后，会同时生成经典只读 SVG 工作台和 `research/canvas/index.html`。后者提供自由平移/缩放、拖动卡片、迷你地图、研究路线/证据/成果切换、过滤与详情检查，并能导出只读 SVG。

节点位置、视口、折叠和固定模块组只属于**视图层**。浏览器“保存布局”存储在当前浏览器；可导出 JSON，再通过 `python scripts/canvas_views.py save PROJECT_ROOT LAYOUT_FILE --name default` 写入 `research/canvas/views.json`，重新生成画布即可跨设备或版本恢复布局。这**不会修改科学证据、研究状态或审批历史**。

具体操作、离线兼容说明和限制见 [Canvas 使用指南](references/canvas-guide.md)。真正的画布语义编辑与 #6 提案接口整合仍计划在 #10，实现前不会出现虚假审批或“保存科研成果”按钮。

## v0.2 画布语义提案与人工审批（#10）

在 `python scripts/local_editor.py serve PROJECT_ROOT` 打印的私有本机地址打开服务首页，点击 **Open interactive Research Canvas**。这与之前独立的只读 HTML 画布不同：本机画布从受令牌保护的 `/api/graph` 读取**当前权威科研状态**，支持创建 Idea/Hypothesis/Task、ResearchBranch、科学 Milestone，安全建立/撤销关系，添加证据引用和修改待确认的验收条件。

任何修改都须 **模拟预览（显示变更前后与影响）→ 提交待审批提案 → 本机交互终端逐条审阅并批准/拒绝 → 刷新科研图**。浏览器无直接批准或执行科研实验的能力。修改真实状态的审批命令为 `python scripts/local_editor.py approve PROJECT_ROOT PROPOSAL_ID`，必须在交互终端输入完整确认文本；旧修订版本、非法归档操作和无效证据会被拒绝。

不启动服务时，`research/canvas/index.html` 仍是自包含、离线、只读 HTML，允许**导出提案草案 JSON**而不是虚假的“保存科研结果”。详见 [画布指南](references/canvas-guide.md) 与 [本机写回安全说明](references/local-bridge-security.md)。**终端确认不是身份认证，人工批准也不等于科学验证**。

## v0.2 完整能力与发布边界（#11–#14）

- **#11**：可从连接本机 Bridge 的画布提出 archive/park/quarantine/retire，正式双阶段回收复审，保留旧失败范围与 Result，产生新 `hypothesis` 派生候选（不是直接恢复旧研究路线）。
- **#12**：SessionRef 多对多关联、Provider/Workspace 筛选、复制真实 Session ID；**真实 Codex 自动深链接尚未验证**，不会凭空构造 URL 或导入聊天正文。
- **#13**：自动化合成数据回归与原生 Windows CI；真实用户电脑上的 Codex 安装与导航必须按 [Windows/Codex 验收清单](references/windows-codex-qa.md) 手动验证。
- **#14**：完整发布检查见 [Release checklist](docs/release-v0.2.md) 和 [CHANGELOG](CHANGELOG.md)。GitHub 项目管理 Milestone 与科研实体 `Milestone` 是两回事。

**安全原则**：画布里的科研修改只有经过 preview → pending proposal → 交互终端独立审批 → 刷新后才生效；`actor=user` / `confirmed=True` 不是身份认证；学术证据仍需独立核验。Windows PowerShell 运行含中文科研元数据的 CLI 时推荐先运行 `$env:PYTHONUTF8='1'`。

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

## v0.4 Research Decision Intelligence

v0.4.0 在已有 v0.3 科学推理图上新增只读决策辅助，正式发布前需完成合并和发布检查。在 v0.3 的可验证 Run、Scoped Evidence、DecisionTrace 基础上，新增只读决策分析：

- `python scripts/v04_project.py PROJECT_ROOT gaps` — 依赖、证据、里程碑验收缺口；
- `python scripts/v04_project.py PROJECT_ROOT opportunities` — 与可证伪观察相关的最低成本检查草案（**成本未知，不保证有效或获准执行**）；
- `python scripts/v04_project.py PROJECT_ROOT archive` — 已搁置/隔离/退休研究路线的复审条件看板（**不自动重启**）；
- `python scripts/v04_project.py PROJECT_ROOT brief --format markdown --output advisor.md` — 导师决策摘要；
- `python scripts/build_dashboard.py PROJECT_ROOT` — 保留原工作台与画布，额外生成 `research/canvas/decisions.html` 离线只读决策页（非实时审批 UI）。

架构约束：当前项目状态 schema 仍为 `0.2.0`，v0.4 为派生分析层，不另建权威科学数据库。新建议不改变 `workflow / epistemic / review / outcome / lifecycle`，不自动将负结果视作科学证伪，也不基于未经验证的来源宣称有文献共识。详见 `references/decision-v04.md`、`docs/roadmap/v0.4.md`。

## v0.4.1 · Persistent Research Grilling（开发分支）

本版本针对「在新会话回答后，Research Navigator 会不会继续追问」的问题增加**显式启动、持续访谈、跨会话状态恢复、用户确认退出**的生命周期。它不让一个新独立 Codex Session 自动继承旧的 Skill 调用，恢复仍需显式 `$research-navigator` 或用户主动安装项目级 `AGENTS.md` 指引。

- `scripts/rn_interview.py` — `research/interviews/current.json` 持久化状态机，独立于科学状态、锁和原子写入、修订检查、审计记录。
- `scripts/interview.py` — `start`、`add-questions`、`answer`、`next`、`pause`、`resume`、`request-exit`、`reject-exit`、`confirm-exit`、`handoff`。
- `scripts/install_interview_guidance.py PROJECT_ROOT` 先只读预览，`--apply` 才在项目根目录追加 `AGENTS.md` 指引；不改全局设置。
- `scripts/build_dashboard.py PROJECT_ROOT` 为已有访谈生成 `research/canvas/interview.html` 离线只读快照，不改变任何研究状态。
- 完整状态转换、数据模型、CLI 示例、Agent/Windows 限制见 [访谈协议](references/interview-v041.md) 和 [v0.4.1 Roadmap](docs/roadmap/v0.4.1.md)。

**最简单的使用方式：** 已安装 Skill 的 Codex 中明确说「在这个研究项目使用 research-navigator 开始 Grilling，多轮追问直到我确认结束；下次继续之前读取 `interview.py status/next`」。若更换全新对话，会再次显式引用 Skill；**记录持久不代表 Skill 永远自动激活**。

v0.4.1 的 Agent 长会话行为与用户 Windows/Codex 环境仍需要人工验收，CLI 的 `--actor user` 不是身份认证。Release 发布以 GitHub 上正式 tag 为准，开发分支不代表稳定版本。
