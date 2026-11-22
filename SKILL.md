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
- 原生 HTML 仍为离线只读快照。无限画布、浏览器受控写回不在 #2–#5 交付范围，属于后续 Issues。

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
