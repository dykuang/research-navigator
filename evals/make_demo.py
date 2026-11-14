#!/usr/bin/env python3
"""Create a clearly labeled synthetic fixture. Never use it as academic evidence."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from rn_core import init_project,add_item,add_source,add_relation,change_status,set_project
from build_dashboard import build

def main():
    ap=argparse.ArgumentParser();ap.add_argument("root");a=ap.parse_args()
    root=Path(a.root).resolve()
    init_project(root,"SYNTHETIC FIXTURE · 跨域检索探索","在统一数据划分和预算下，动态特征融合能否提高跨域检索 F1？（演示问题，非真实项目）")
    log=root/"research"/"03-experiments"/"logs"/"synthetic-run.txt"
    log.parent.mkdir(parents=True,exist_ok=True)
    log.write_text("SYNTHETIC FIXTURE / NOT A REAL EXPERIMENT\nDataset: fabricated toy example\n2 toy runs: A=0.61; Baseline=0.63 (fictional F1)\nThis text only tests application state transitions.\n",encoding="utf-8")
    src=add_source(root,"SYNTHETIC FIXTURE · 虚构相关工作，仅演示摘要访问级别",locator="local/synthetic-placeholder",access_level="abstract",verification_status="unverified",summary="演示：假定与创新点存在相似研究。未检索，不可作为真实文献引用")
    q=add_item(root,kind="ResearchQuestion",title="跨域泛化是否改善？",module="topic",description="固定数据划分与算力下检验 F1；仍需明确差异是否显著",next_action="与导师确认提升阈值")
    idea_a=add_item(root,kind="Idea",title="方法 A：动态特征融合",module="topic",description="合成假设：融合多层特征提高泛化",next_action="检查实验负结果的样本量与泄漏风险")
    hyp=add_item(root,kind="Hypothesis",title="动态融合优于简单拼接",module="topic",description="未验证假设，有限模拟测试负面结果",next_action="基于独立样本重新测试")
    prior=add_item(root,kind="PriorWork",title="近似前人工作（仅模拟摘要）",module="literature",description="演示如何保留无法验证的创新性冲突",evidence_refs=[src["id"]],next_action="真实项目中查验论文原文与代码")
    baseline=add_item(root,kind="Baseline",title="Baseline B：特征拼接",module="literature",description="合成数据上的简单基线；并非真实 SOTA",next_action="确认使用相同划分和资源")
    exp=add_item(root,kind="Experiment",title="EXP-A：双次模拟对照",module="experiment",description="SYNTHETIC FIXTURE：n=2，无法推断真正统计显著性",acceptance_criteria="记录 toy 两次运行和比较值",next_action="补充现实数据的多重复验证")
    result=add_item(root,kind="Result",title="融合方法 A 的初步负面结果",module="experiment",description="SYNTHETIC FIXTURE；不可作为真实学术证据",observation="合成数值：F1 A=0.61，Baseline B=0.63；仅 2 次模拟运行",artifact_path="research/03-experiments/logs/synthetic-run.txt",outcome="negative",acceptance_criteria="toy log created",completion_note="synthetic-run.txt exists",workflow="done")
    claim=add_item(root,kind="Claim",title="方法 A 可能改善泛化（现有证据不支持）",module="synthesis",description="旧主张受到负结果与有限样本约束",next_action="撤回未验证的强论断或增加测试")
    idea_b=add_item(root,kind="Idea",title="方法 B：更严格的数据对齐",module="pivot",description="建议研究方向，尚需确定对照指标",next_action="设计低成本对齐消融")
    task=add_item(root,kind="Task",title="整理消融实验协议",module="experiment",workflow="ready-for-agent",description="仅做计划，不运行昂贵任务",next_action="编写数据划分和重复次数协议")
    idea_c=add_item(root,kind="Method",title="旧路线 C：复杂对抗分支",module="pivot",description="SYNTHETIC FIXTURE：计算资源超限，原方案先搁置",next_action="如有资源改善可申请复审")
    add_relation(root,hyp["id"],idea_a["id"],"depends-on")
    add_relation(root,exp["id"],hyp["id"],"tests")
    add_relation(root,exp["id"],baseline["id"],"depends-on")
    add_relation(root,result["id"],exp["id"],"depends-on")
    add_relation(root,claim["id"],idea_a["id"],"depends-on")
    add_relation(root,result["id"],claim["id"],"contradicts")
    add_relation(root,task["id"],idea_b["id"],"depends-on")
    add_relation(root,prior["id"],claim["id"],"contradicts")
    change_status(root,exp["id"],"workflow_status","done","模拟实验已保存日志（非真实运行）",completion_note="synthetic-run.txt saved")
    change_status(root,exp["id"],"outcome","inconclusive","两次模拟运行不足以判断科学主张")
    change_status(root,idea_a["id"],"lifecycle_status","parked","虚构测试没有得到稳定收益，先探索 B",actor="user",failure_category="unknown",failure_scope="仅 synthetic toy data，n=2；不能推广到真实任务",confidence="low",revival_triggers="取得真实数据、新策略与足够重复次数",lesson="勿将有限负结果当成普遍反证",cost="toy runs",evidence_refs=[result["id"]])
    change_status(root,idea_c["id"],"lifecycle_status","parked","虚构项目算力预算不足",actor="mentor",failure_category="resources",failure_scope="模拟单 GPU 与一周预算",revival_triggers="能提供资源或用更小模型")
    change_status(root,idea_c["id"],"lifecycle_status","under-revival-review","用户希望检查分支可否轻量化",actor="user",revival_question="可以缩小对抗分支为门控层吗？",new_conditions="仅限低成本消融，尚未批准执行")
    set_project(root,focus_module="pivot",next_decision="确认下一轮继续 B，还是提出 A 的低成本复验",actor="user",reason="模拟演示科研路线变更")
    (root/"CONTEXT.md").write_text("# 规范术语（SYNTHETIC FIXTURE）\n\n- **跨域泛化**：模型在事先分离的目标领域样本上的性能，需注明数据分割协议。\n- **负结果**：在指定条件下观察不到预期收益，不代表普遍证伪。\n",encoding="utf-8")
    note=root/"research"/"04-iterations"/"failure-analysis.md"
    note.parent.mkdir(parents=True,exist_ok=True)
    note.write_text(f"# SYNTHETIC FIXTURE · Failure Analysis\n\n- 旧思路：{idea_a['id']}。\n- 实验：{exp['id']}；结果：{result['id']}。\n- 模拟负结果范围：toy data、n=2。\n- 原因：尚无足够样本判别实现错误和方法无效。\n- 决定：搁置旧方案，探索新 {idea_b['id']}。\n- 重要：以下数值皆为模拟，不是研究发现。\n",encoding="utf-8")
    synth=root/"research"/"05-synthesis"/"project-summary.md"
    synth.parent.mkdir(parents=True,exist_ok=True)
    synth.write_text(f"# SYNTHETIC FIXTURE · 项目总结\n\n- 研究问题：{q['id']}。\n- 负结果 {result['id']} 仅对 toy 条件有效。\n- 原 {idea_a['id']} 已搁置，不能默认继续执行。\n- {claim['id']} 因上游变化被标记待复查。\n- 可能方向：{idea_b['id']}，未经科学验证。\n",encoding="utf-8")
    path=build(root)
    print(f"SYNTHETIC FIXTURE created: {root}\nDashboard: {path}")
if __name__=="__main__":main()
