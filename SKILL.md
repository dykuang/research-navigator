---
name: research-navigator
description: Use when a student or advisor wants to initiate, scope, investigate, plan, revise, archive, revive, or synthesize a research project; interview rigorously, track uncertainty and evidence, preserve failed ideas, coordinate five research modules, and produce an offline research dashboard. Also use when returning to an existing Research Navigator workspace to resume decisions or check research status.
---

# Research Navigator · 有状态科研规划与研究记忆

面向学生和导师的交互式科研工作流 Skill。**五个研究模块共享一个状态与证据系统**，可并行、回退、跨会话恢复；不要把它当作五次孤立问答。默认使用中文，保留学术术语的英文原文。

## v0.2 开发分支新增能力（#2–#5）

读现有项目时先检查 `research/state/project.json` 的 schema 版本。旧版 v0.1 项目可只读访问，任何修改之前须经用户同意运行 `python scripts/migrate_state.py preview PROJECT_ROOT` 然后 `apply`，生成备份；事务异常时停止操作并运行 `recover`。不能跳过校验手动写 JSON。

- `ResearchBranch` 与科学 Milestone：多研究路线共享数据和 Baseline，里程碑验收需逐条附证据、人类确认，不等于实验科学结论成立。
- `EvidenceLink`：细粒度支持/反驳/限定、适用范围、具体定位；不把摘要冒充全文，也不自动提升 epistemic status。
- `SessionRef`：只保存 Codex/Agent 会话 ID 与研究节点的多对多关联，不读取聊天正文。无经验证的 provider 深链接时仅展示/复制会话 ID，不能声称自动跳转。
- CLI 用法和安全边界见 `references/v02-operations.md`；新功能的源代码位于 `scripts/rn_domain.py` 和 `scripts/v02_project.py`，项目状态仍由 `rn_core.py` 校验并审计。
- 该段只描述 #2–#5 的基础范围；**#6–#12 已在 v0.2 分支实现本机受控提案、无限画布和 SessionRef UI**。独立生成的离线 HTML 仍为只读快照。

## 完整 v0.2 归档回收和会话导航规则（#11–#12）

- 如需归档 ResearchBranch/Idea，使用 `archive-route` 提案，说明失败/限制范围、诊断信心、回收条件，并经独立终端审阅批准；单个负结果不是全面失败证明。
- 回收必须先用 `begin-revival-review` 获得第一独立批准，然后 `approve-revival-candidate` 第二次授权创建新的待验证候选；旧状态、负结果、历史事件、`derived-from` 与 `revives` 关系不得覆盖。仅参考已归档想法属于只读操作。
- SessionRef 提案只处理 provider/workspace/session 元数据和多对多关联；Canvas 可复制 ID 与显示角色，不会自动抓取对话正文，也**不承诺尚未验证的 Codex 自动跳转**。详见 `references/canvas-guide.md`。
- 完整 release/Windows/Codex 验收按 `docs/release-v0.2.md`、`references/windows-codex-qa.md`，不能把 CI 模拟人审视为真实身份认证或安装测试。

## v0.3 科研推理图扩展（当前开发分支）

如用户要求追踪真实实验尝试、检查同一 Claim 的冲突证据、或根据明确记录的历史事件回放研究决策，按需读取 `references/reasoning-v03.md`，使用 `scripts/v03_project.py`。该扩展在 v0.2 规范状态库中增加 `ExperimentRun` 与 `DecisionTrace`，**不自动修改已有记录或提升科学证据等级**。真实实验工件必须存在于项目目录且经过 SHA-256 检查，合成示例必须显式标记；决策回放只显示已有事件与 SessionRef，不推测缺失聊天正文。

科研推理画布的 `reasoning` 视图与节点详情为只读；v0.2 受保护的本机提案桥仍负责既有语义写入。不得把 CLI 中的 `--actor` 当作真实身份认证，也不得声称 v0.3 已发布稳定版。

## v0.4.1 · Grilling 访谈模式（生命周期，而非一次性问答）

**只在用户明确要求开启或继续密集访谈时进入。**用户只问使用方法时先解释，不初始化或修改研究数据。使用 `scripts/interview.py PROJECT_ROOT start --topic ...` 显式开启持久访谈；有 `research/interviews/current.json` 时先运行 `status`、`next`，不能重复 start 或假定空白项目。

- **每一轮都要继续使用本 Skill 访谈协议**：先检查状态及依赖，选择 1–5 个重要且彼此独立的前沿问题（推荐 2–5，边界少可更少）；问清楚 WHY、选项与权衡、建议及最低成本验证，使用 `add-questions` 保存问题（JSON 字段见 `references/interview-v041.md`）。不要仅靠模型短期聊天记忆来保存持续模式。
- 用户回答后，用 `answer --question Q-0001 --text '...' --actor user` 记录**明确确认**的答案；暂缓/有争议的回答分别标记 `deferred` / `unresolved`，前置问题未确认就不能推进依赖问题。真正科学证据的确认仍走原科研状态系统，访谈答案不等于实验验证。
- 如果用户对已确认答案提出修正，需 `--revise` 并重新检查受影响的下游问题。不能悄悄把用户回答改成 Agent 结论。
- 会话停止时可以 `pause`，更换新 Codex Session 时用户需**重新明确调用** `$research-navigator` 或通过显式启用的项目 `AGENTS.md` 引导恢复。同一个项目根目录中用 `status`、`next`、`handoff` 恢复；新会话不会自动继承之前的 Skill 调用，不能向用户保证后台长期持续激活。
- 达成较多共识时 Agent 提议 `request-exit --reason '共识摘要及仍未解决的问题'`，**不要自行退出 Grilling**。用户可以 `reject-exit` 继续，或 `confirm-exit` 明确确认；未解决的每个问题必须分别通过 `--accept-open Q-NNNN` 被明确接受。在 `completed` 后回到普通科研助手模式，不再强制 Grilling，除非用户请求 `reopen`。
- 不得用 `--actor user` 冒充真实身份。CLI 的 actor 是记载来源的声明，不是安全的身份验证。助手只能在用户实际明确授权之后调用对应人类确认命令。
- 生成 Dashboard 时若项目已有访谈，`research/canvas/interview.html` 展示**只读访谈快照**。网页不会审批、自动进入访谈或创建提案；访谈 sidecar 与 `research/state/*.json` 的权威科学状态分离。

按需参考 `references/interview-v041.md`、`references/interaction-protocol.md`；新用户帮助由 `ask-research-navigator` 提供。项目本地可选的 AGENTS.md 引导仅在用户明确执行 `python scripts/install_interview_guidance.py PROJECT_ROOT --apply` 后写入，不自动修改全局 Agent 行为。


## v0.4.2 · 结构化问答、Other 自由输入和 Codex 原生交互降级

Grilling 每道题必须允许用户拒绝已有备选项并给出**其他／自定义**答案；不要把推荐选项当作自动确认结果。建议创建 `choices`（稳定 ID、显示标签、利弊说明）和可选 `recommended_choice_id`，优先 2–3 项；旧版仅含 `options` 字符串的问题继续支持完整自由回答。详见 `references/interview-v042.md`。

在 Codex 运行时**实际提供** `request_user_input` 工具的模式中，可以优先调用真实工具，以 1–3 个问题和每题 2–3 个选项展示原生选择器。**不得手工插入 Other 到 native options**：支持的客户端自行添加输入框。调用前可用 `python scripts/interview.py PROJECT_ROOT native-request --question Q-0001` 获得只读建议参数，但该 CLI **没有**真正显示 UI，返回 `tool_called=false`。检查工具实际可用性，不支持时改用 `prompt --question Q-0001` 文本展示 A/B/C/其他。四个以上选项也须完整文本展示，不能静默截断。

用户选定固定项后，在实际确认基础上使用 `answer --question Q-0001 --choice CHOICE_ID --actor user`；用户选 Other 时用 `--choice other --custom-answer '用户原话'`；旧版 `--text` 仍可使用。Codex 原生回包可以先用 `resolve-native --response-json` 只读解释，未知选项应追问，不能静默写入状态。受影响下游问题仍必须在 `--revise` 后重新确认。离线 HTML 提供选项控件但只能生成可复制的回答草案，**不保存、不代替授权**。


## 先做什么

1. 找到用户指定的**科研项目根目录**（不是本 Skill 安装目录）。检查 `RESEARCH.md`、`CONTEXT.md`、`research/state/`、现有研究记录、Git 状态；现有内容优先，不得无故覆盖。
2. 如果已有 `research/state/project.json`，读取项目状态：
   ```bash
   python /PATH/TO/research-navigator/scripts/validate_state.py /PROJECT/ROOT
   python /PATH/TO/research-navigator/scripts/update_project.py summary /PROJECT/ROOT
   python /PATH/TO/research-navigator/scripts/query_research_items.py /PROJECT/ROOT --mode planning
   ```
   同时读取近期 `research/state/events.jsonl`、当前相关实体、归档历史和用户已确认的术语。不要重新询问已回答且可验证的问题。
3. 如果项目尚未初始化，在取得项目根目录和用户的写入意图后：
   ```bash
   python /PATH/TO/research-navigator/scripts/update_project.py init /PROJECT/ROOT --name '研究项目名称' --question '初始研究想法（可留空）'
   ```
4. 根据用户当前需要，选择模块参考文档 `references/modules/*.md`，同时使用 `references/interaction-protocol.md` 与 `references/evidence-policy.md`。**按需加载**；不要把五模块全塞进一次长访谈。
5. 维护决策树 **frontier**：根据已解决前提挑选每轮 2–5 个相互独立、高价值的问题；每个问题说清原因、选项及取舍、Agent 推荐与依据、不确定时最便宜的验证方式。用户负责最终决策；Agent 负责可独立调查的事实。
6. 用户确认具体定义后立即更新 `CONTEXT.md`（**只存规范术语定义**），并记录相应实体/决策/来源；对昂贵、难逆转、具有真实权衡的决定才创建 ADR。
7. 每次重要决策或观察都经脚本持久化；运行验证、更新 HTML。报告「新确定｜仍不确定｜等待用户确认｜Agent 能自行做｜建议下一步」，最多五项。只读问答无需写盘，不得谎称已经保存。

## 强制的状态模型与隔离边界

阅读 `references/state-schema.md`、`references/status-transitions.md` 与 `references/idea-lifecycle.md`，理解 **workflow / epistemic / review / outcome / lifecycle / impact** 六个独立维度。

- `done` 仅代表动作完成；不代表科学结论得到验证。
- `source-backed` 需要核实的一手来源；只看摘要不能声称读过全文。
- `user-confirmed` 仅代表人类批准，不代表证据真实。
- 单次 `negative` 不自动使方法 `quarantined` 或 `retired`。
- 所有被 `parked` / `quarantined` / `retired` 的对象有保留理由、范围、负面证据和回收条件的归档卡。
- **正向规划必须调用** `query_research_items.py --mode planning`，使用程序筛选的 `active` 候选。风险与负结果检索用 `--mode risk-check`；总结用 `--mode synthesis`，保留失败历史。
- 用户说「参考旧想法」只授权只读档案探索：`--mode archive-exploration --user-authorized`。**绝不等于授权执行或恢复状态**。
- 如需恢复：先 human-approved `under-revival-review`，再 human-approved `revive` **创建新的待验证候选**，保留旧失败记录。具体协议见 `references/idea-lifecycle.md`。
- 状态图发生上游变化时下游自动标为 `needs-review` 或 `blocked`；不要自动废弃独立有效的来源/数据集。

## 五个跨模块的业务入口

| 触发 | 参考文件 | 产物（按需创建） |
|---|---|---|
| 模糊想法、可行性、创新路径 | `references/modules/topic.md` | `research/01-topic/{topic-brief,research-questions,feasibility}.md` |
| 查相关工作、判断创新空间、选 Baseline | `references/modules/literature.md` | `research/02-literature/{search-strategy,baseline-shortlist,gap-map}.md`，文献矩阵 |
| 构建可证伪实验、比较方案 | `references/modules/experiment.md` | `research/03-experiments/experiment-plan.md`、协议与实验登记 |
| 实验失败、复现偏差、调整方向、搁置回收 | `references/modules/pivot.md` | `research/04-iterations/{failure-analysis,pivot-log}.md`、归档复审记录 |
| 组会、论文、交接、整合结果 | `references/modules/synthesis.md` | `research/05-synthesis/{claim-evidence-matrix,project-summary}.md` |

成果总结不要求所有其他模块结束。**结构化状态文件是唯一权威源**；Markdown 文字材料和 HTML 是可复核的工作文档/派生视图，不应相互矛盾。

## 可选本机提案接口（#6）

`scripts/local_editor.py serve PROJECT_ROOT` 可在本机启动只接受 `127.0.0.1` 请求的受限提案服务；浏览器只允许**排队待审批提案**，不能直接写科研状态、确认/回收科研方向或假装完成科学验证。用户必须在**交互终端**执行 `inspect` 后逐条 `approve` 或 `reject`，服务端再次校验项目 revision 和全部状态约束，成功时写入事件记录。若服务未运行，原离线 HTML 仍为只读。安全边界和命令见 `references/local-bridge-security.md`。

## v0.2 交互式无限画布与布局（#7–#9）

`scripts/graph_projection.py` 从权威科研状态只读生成稳定节点/带来源关系。运行 `scripts/build_dashboard.py PROJECT_ROOT` 会生成两种离线只读工作台：原有 `research/dashboard/index.html`（经典 SVG 回退）和 `research/canvas/index.html`（无限可视画布）。画布可拖动节点、缩放、筛选、展开分支与检查详细证据，**所有交互均不自动更改任何研究真值或项目状态**。

布局用独立 `research/canvas/views.json` 管理，保存/导入导出方式见 `references/canvas-guide.md` 和 `scripts/canvas_views.py`。文件只含坐标、缩放、折叠、视图名称/作者/修订，不允许存储审批或科学验证结果。用户要进行语义编辑时仍使用现有 CLI 或 #6 本机受控提案流程；未来浏览器的正式接入归 #10。

## v0.2 画布语义编辑流程（#10）

浏览器科研画布本身不得修改权威状态。若用户希望从画布**提出**科研新节点、路线、里程碑验收条件或证据关系，启动 `scripts/local_editor.py serve PROJECT_ROOT` 并在受保护的本机 Canvas 中按“模拟预览 → 提案入队 → 终端人工确认 → 刷新”操作。服务的 `/api/preview` 仅在内存中调用与正式审批相同的语义校验；`/api/proposals` 只写待审批草案；**不存在 HTTP 批准入口**。审批时终端再次展示影响并校验项目修订号，只有通过权威状态引擎才产生科研事件。

归档和正式 revival、科学真实性确认、昂贵实验的执行依旧不能靠普通画布改标签绕过。脱机画布可导出草案，但**不得暗示写回成功**。操作和安全范围参见 `references/local-bridge-security.md`、`references/canvas-guide.md`。

## 常用命令与工具

所有 CLI 都使用 Python 标准库，无网络要求。详细 CLI 例子见 `references/cli-recipes.md`。

```bash
python scripts/update_project.py add-item /PROJECT/ROOT --type Idea --title '候选 A' --module topic --next-action '访谈后确定可证伪假设'
python scripts/update_project.py add-source /PROJECT/ROOT --title '原始论文标题' --url 'https://...' --access-level abstract
python scripts/update_project.py link /PROJECT/ROOT EXP-0001 HYP-0001 --relation tests
python scripts/query_research_items.py /PROJECT/ROOT --mode risk-check
python scripts/validate_state.py /PROJECT/ROOT
python scripts/build_dashboard.py /PROJECT/ROOT
```

以上 `scripts/` 路径在本 Skill 根目录执行，或者改为绝对路径。`update_project.py` 的**成功变更默认自动重建看板**。浏览器打开项目下 `research/dashboard/index.html`；它是内嵌当前数据的**离线只读 HTML 快照**，不是具有写入/审批后端的实时应用。当前默认图为本地 SVG；仅检测或明确验证 Archify 支持的 schema 后才能改用它，不得猜测 API。

## 合作与安全

- 不要虚构论文 DOI、实验指标、外部来源或已执行的操作。没有工具时标注 `uncertain`、给出待验证操作，别伪装为已查证。
- 重要科研路线变更、昂贵实验、外部共享/发布、覆盖已有研究资产，需人类明确批准。CLI 的 `--actor` 是审计声明，**不构成身份认证**；调用它的 Agent 必须先取得实际授权。
- 不要把提示词生成的实验假设写成真实观察；演示项目必须标明 **synthetic fixture**。
- 不直接修改 `events.jsonl`，不手动将 `epistemic_status` 提升为已证实，避免绕过 CLI 校验和决策记录。
- 与生物医学、人类被试、敏感数据相关的项目，提醒符合适用的伦理审查及数据安全要求。

## 质量门槛与继续会话

更新后运行 `validate_state.py`，如失败先修复而不是继续推荐；在关键变化后重建看板。若现有文献与定义矛盾，应优先指出冲突并问用户如何解决。会话结束可按 `templates/session-handoff.md` 的格式留下下次执行概要，索引已落盘的实体与决策，不复制整套状态。完整能力与未实现功能见 `README.md`。

## v0.4 · 科研决策智能辅助（只读建议，未获实验执行许可）

当用户询问“下一步做什么、证据不足在哪里、哪条实验最有信息价值、导师需要审核什么”时，优先运行 `python scripts/v04_project.py PROJECT_ROOT brief` 或 `gaps / opportunities / archive`。按需参考 `references/decision-v04.md`，不必开始新项目或回到初始访谈。报告读取 v0.3 权威状态，不写入项目状态、批准实验或解除归档隔离。**任何建议只是用于讨论的假设；信息价值和成本默认为未知，无法用虚构概率/评分替代证据。**

无限画布离线导出后，打开 `research/canvas/decisions.html` 查看证据缺口、低成本区分性检查、导师审查和历史路线复审。画布的科学语义编辑仍需 v0.2 本机提案 → 人工终端批准；不得让代理把离线建议伪装成通过审批的待执行任务。

**默认模式的异步交互补充（v0.4.2）：**部分 Codex 客户端仅提供 `request_user_input_async`，参数为 `questions:[{title,options:[文字选项]}]`，可以从 `interview.py PROJECT_ROOT async-request --question Q-0001` 生成**只读**建议。该工具返回的 `{"accepted":true}` **只表示发送请求成功，不表示用户选择或授权**。Agent 必须等待实际的新用户消息，并在确认后记录；必要时用 `resolve-async --question Q-0001 --text '用户原话'` 将回答解释为固定选项或 Other。异步卡片未显示、被关闭或无法取得回答时，立即提供明确文本选项降级。不得在仅收到 accepted 时推进依赖问题。

