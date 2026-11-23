"""v0.4 deterministic research decision intelligence.

Read-only projections over v0.3 canonical state: NO automatic decisions,
invented success probabilities, false evidence certification, or silent revival.
"""
from __future__ import annotations

from collections import defaultdict
from rn_core import ResearchError, load, validate_state

ACTIVE = "active"
UNSAFE_IMPACTS = {"blocked", "stale", "needs-review"}
UNREADY_RUNS = {"planned", "running"}
COSTS = {"unknown", "low", "medium", "high"}
VALUES = {"uncertain", "potentially-informative", "high-if-discriminating"}
MODES = {"experiment", "literature", "topic", "pivot", "synthesis"}

def _items(state):
    return {x["id"]: x for x in state["items"]}

def _ref(state, ident):
    items = _items(state)
    sources = {x["id"]: x for x in state["sources"]}
    return items.get(ident) or sources.get(ident)

def _safe_active(x):
    return (x.get("lifecycle_status") == ACTIVE
            and x.get("impact_status") == "current"
            and x.get("workflow_status") not in
            ("blocked", "done", "no-further-considered")
            and x.get("review_status") != "rejected")

def _gap(code, item, description, severity="review", refs=None, evidence=None):
    return {"code": code, "subject_id": item["id"],
            "title": item["title"], "module": item["module"],
            "description": description, "severity": severity,
            "related_ids": list(refs or []),
            "evidence_links": list(evidence or []),
            "resolution_status": "requires-review",
            "claim_is_scientifically_proven": False}

def gaps(state):
    """Deterministically report missing references and unresolved decisions.

    Does not infer overlap of evidence scopes or experimental causality.
    """
    validate_state(state, strict=True)
    out = []
    items = _items(state)
    links = defaultdict(list)
    for e in state.get("evidence_links", []):
        links[e["claim_id"]].append(e)
    source_ids = {s["id"] for s in state["sources"]}
    for x in sorted(state["items"], key=lambda i: i["id"]):
        typ = x["type"]
        # Archived research is historical evidence, not an active task queue.
        # Formal revival review remains visible until a person resolves it.
        lifecycle=x.get("lifecycle_status")
        if lifecycle not in (ACTIVE, "under-revival-review"):
            continue
        if x.get("impact_status") != "current":
            out.append(_gap("DEPENDENCY_NEEDS_REVIEW", x,
                "上游前提或来源状态改变：复核相关决定和实验范围。", "blocker"))
        if x.get("review_status") == "needs-user-confirmation":
            out.append(_gap("HUMAN_REVIEW_PENDING", x,
                "需要用户/导师确认；批准不等于科学上得到验证。"))
        if lifecycle != ACTIVE:
            continue
        if typ == "Claim":
            valid = [e for e in links[x["id"]] if
                     (not items.get(e["evidence_id"]) or
                      (items[e["evidence_id"]].get("impact_status") == "current"
                       and items[e["evidence_id"]].get("lifecycle_status") == ACTIVE))]
            if not valid:
                out.append(_gap("CLAIM_MISSING_EVIDENCE", x,
                    "没有可用的分范围证据关联；不能当作已证明结论。", "blocker"))
            else:
                states = {e["stance"] for e in valid}
                if {"supports", "contradicts"} <= states:
                    out.append(_gap("CLAIM_CONFLICTING_EVIDENCE", x,
                        "存在支持与反对证据；需人工核对是否同一实验条件，不能自动判定冲突。",
                        "review", [e["evidence_id"] for e in valid],
                        [e["id"] for e in valid]))
                if not any(e["stance"] == "supports" and e["quality"] != "unverified"
                           for e in valid):
                    out.append(_gap("CLAIM_SUPPORT_UNVERIFIED", x,
                        "尚无经过来源核对或实验观察的支持证据；无证据不代表已证伪。"))
        if typ == "Experiment":
            runs = [r for r in state["items"] if
                    r["type"] == "ExperimentRun" and
                    r.get("run", {}).get("experiment_id") == x["id"]]
            # A negative, mixed or inconclusive *recorded* Run needs
            # diagnosis in its original context. Invalidated logs are excluded.
            questionable=[r for r in runs if
                r.get("run", {}).get("status")=="recorded" and
                r.get("outcome") in ("negative","inconclusive","mixed")]
            if questionable:
                out.append(_gap("EXPERIMENT_NEEDS_NEGATIVE_INTERPRETATION",x,
                    "存在负面/混合/无结论的实际运行记录；先检查样本、对照、条件和失效可能，不能直接断言方法普遍无效。",
                    "review", [r["id"] for r in questionable],
                    [r["run"].get("result_id") for r in questionable if r["run"].get("result_id")]))
            if not runs:
                out.append(_gap("EXPERIMENT_NO_REGISTERED_RUN", x,
                    "实验已有方案，但没有登记任何运行；计划不等于执行。", "review"))
            elif all(r["run"]["status"] in UNREADY_RUNS for r in runs):
                out.append(_gap("EXPERIMENT_ONLY_PLANNED_RUNS", x,
                    "仅有 planned/running 记录；尚没有经过本机工件校验的结果。"))
            elif all(r["run"]["status"] == "invalidated" for r in runs
                     if r["run"]["status"] not in UNREADY_RUNS):
                out.append(_gap("EXPERIMENT_RUNS_INVALIDATED", x,
                    "现有已记录运行均失效，需要新证据或新的最小实验。", "blocker"))
        if typ == "Hypothesis" and not any(
                r["type"] == "tests" and r["to"] == x["id"]
                for r in state["relations"]):
            out.append(_gap("HYPOTHESIS_NOT_TESTED", x,
                "当前假设没有显式实验测试关系；先设计可证伪观察。"))
        if typ == "Milestone":
            meta = x.get("milestone", {})
            if meta.get("accepted"):
                continue
            for c in meta.get("criteria", []):
                missing = not c.get("evidence_refs")
                weak = [ref for ref in c.get("evidence_refs", [])
                        if ref in source_ids and
                        next((s.get("verification_status") for s in state["sources"]
                              if s["id"] == ref), "") != "primary-inspected"]
                if missing or weak or not c.get("reviewed"):
                    reason = ("尚无关联证据" if missing else
                              "包含尚未核对全文的一手来源" if weak else
                              "尚未获人工确认")
                    out.append(_gap("MILESTONE_GATE_PENDING", x,
                        "验收项 " + str(c.get("id")) + "：" + reason,
                        "review", c.get("evidence_refs", [])))
    return out

def opportunities(state, cost="unknown"):
    """Advisory experiment ideas, not forecasts or automatically runnable tasks."""
    if cost not in COSTS:
        raise ResearchError("invalid qualitative cost")
    problems = gaps(state)
    items = _items(state)
    answer = []
    mapping = {
        "HYPOTHESIS_NOT_TESTED": ("制定最小可证伪实验",
            "若观察支持/反对假设，将怎样更新路线？",
            "experiment", "比较至少一个对照与一个可能推翻假设的观察"),
        "CLAIM_CONFLICTING_EVIDENCE": ("复核矛盾证据的条件",
            "不同证据是否在同一数据、指标、协议和范围内比较？",
            "literature", "先检查证据范围、质量和重复性；不要直接求平均"),
        "CLAIM_MISSING_EVIDENCE": ("寻找可核验的一手证据",
            "哪种观察能区分主张与竞争解释？",
            "literature", "优先读原始来源或设计最小对照"),
        "EXPERIMENT_NO_REGISTERED_RUN": ("检查最小实验是否可执行",
            "若失败，如何区分工程错误和科研假设错误？",
            "experiment", "先审查实验计划与资源，再决定是否提交运行申请"),
        "EXPERIMENT_ONLY_PLANNED_RUNS": ("检查实验运行工件",
            "当前证据是运行计划还是实际观察？",
            "experiment", "按协议核对日志、指标和结果，不伪造执行"),
        "EXPERIMENT_RUNS_INVALIDATED": ("设计修正后的最小复现实验",
            "如何在修正失效原因后验证原观察？",
            "experiment", "记录失效原因、改变条件并重新检查"),
        "EXPERIMENT_NEEDS_NEGATIVE_INTERPRETATION": ("诊断负面或不确定实验结果",
            "如何区分实现故障、评价条件差异、统计不充分和真正无收益？",
            "experiment", "先检查原始运行日志、协议与样本；必要时提出最低成本复核，不能自动重跑"),
        "MILESTONE_GATE_PENDING": ("补充验收条件所需证据",
            "什么观察才足以达到此项里程碑标准？",
            "synthesis", "先完成证据收集，再交给人类审阅"),
    }
    for g in problems:
        if g["code"] not in mapping:
            continue
        x = items[g["subject_id"]]
        if not _safe_active(x):
            continue
        title, distinction, mode, check = mapping[g["code"]]
        answer.append({
            "id": "OPP-" + str(len(answer)+1).zfill(4),
            "subject_id": x["id"], "title": title,
            "goal": "缩小研究不确定性，而非追求任务完成数",
            "gap_code": g["code"], "evidence_ids": g["related_ids"],
            "expected_discriminating_observation": distinction,
            "proposed_minimum_check": check,
            "module": mode, "estimated_cost": cost,
            "expected_information_value": "uncertain",
            "confidence": "proposal-not-validated",
            "assumptions": ["需要检查可用资源", "需要学生定义成功与否的阈值"],
            "human_review_required": True,
            "execution_approved": False,
            "origin": "deterministic-gap-to-heuristic-proposal",
            "is_canonical_state": False,
        })
    return answer

def archive_watchlist(state):
    validate_state(state, strict=True)
    result = []
    for x in sorted(state["items"], key=lambda i: i["id"]):
        if x.get("lifecycle_status") not in (
                "parked", "quarantined", "retired", "under-revival-review"):
            continue
        archive = x.get("archive") or {}
        if not archive:
            continue
        result.append({
            "id": x["id"], "title": x["title"],
            "lifecycle_status": x["lifecycle_status"],
            "archival_reason": archive.get("reason", ""),
            "failure_scope": archive.get("failure_scope", ""),
            "revival_conditions": archive.get("revival_triggers", ""),
            "evidence_ids": archive.get("evidence_refs", []),
            "evidence_strength": archive.get("diagnostic_confidence", "uncertain"),
            "review_requested": x["lifecycle_status"] == "under-revival-review",
            "trigger_verified": False,
            "read_only": True,
            "recommended_next_action": "询问用户是否只读复查、正式复审，或保持搁置",
            "automatic_reactivation": False,
        })
    return result

def mentor_brief(state):
    validate_state(state, strict=True)
    problems = gaps(state)
    candidate = opportunities(state)
    byseverity = {"blocker": 0, "review": 1}
    ordered = sorted(problems, key=lambda x:
                     (byseverity.get(x["severity"], 2), x["subject_id"], x["code"]))
    milestones=[]
    for x in sorted(state["items"], key=lambda i:i["id"]):
        if x["type"] == "Milestone":
            m=x.get("milestone",{})
            milestones.append({
                "id":x["id"],"title":x["title"],
                "accepted":bool(m.get("accepted")),
                "human_review_status":x["review_status"],
                "criteria":[{"id":c["id"],"text":c["text"],
                             "evidence_ids":c["evidence_refs"],
                             "reviewed":c["reviewed"]} for c in m["criteria"]],
                "scientific_truth_certified":False})
    return {"schema":"research-decision-v0.4",
            "project_id":state["project"]["project_id"],
            "revision":state["project"]["revision"],
            "project_name":state["project"]["name"],
            "research_question":state["project"].get("research_question",""),
            "next_decision":state["project"].get("next_decision",""),
            "milestones":milestones,
            "pending_gaps":ordered,
            "proposed_next_checks":candidate[:12],
            "archive_review_watchlist":archive_watchlist(state),
            "warnings":["Advisory only. Costs, probabilities and scientific truth are not inferred.",
                        "Human confirmation is separate from evidence verification.",
                        "Archived ideas are not eligible for normal execution."]}

def markdown_brief(report):
    parts=["# Research Navigator v0.4 · 导师决策摘要", "",
           "**研究主题：** "+report["project_name"],
           "**研究问题：** "+report["research_question"], "",
           "## 需要决策", report["next_decision"] or "尚未填写", "",
           "## 里程碑科学验收（不等于 GitHub Milestone）"]
    for m in report["milestones"]:
        parts.append("- "+m["id"]+" "+m["title"]+
                     (" · 已有人类验收" if m["accepted"] else " · 待验收"))
        for c in m["criteria"]:
            parts.append("  - "+c["id"]+" "+c["text"]+"；证据："+", ".join(c["evidence_ids"]))
    parts += ["", "## 证据缺口与风险"]
    for g in report["pending_gaps"][:20]:
        parts.append("- "+g["subject_id"]+" / "+g["code"]+" — "+g["description"])
    parts += ["", "## 下一步最小区分性检查（未获执行许可）"]
    for o in report["proposed_next_checks"][:12]:
        parts.append("- "+o["subject_id"]+"："+o["title"]+" — "+
                     o["proposed_minimum_check"]+"；费用：未知；需人工审阅")
    parts += ["", "## 历史路线复审候选（默认隔离）"]
    for a in report["archive_review_watchlist"]:
        parts.append("- "+a["id"]+" ("+a["lifecycle_status"]+")："+a["revival_conditions"])
    parts += ["", "> 这些是待复核的建议，不是自动批准、实验执行或已证实的科学结论。"]
    return "\n".join(parts)+"\n"

def summarize(root, mode="brief"):
    state=load(root)
    if mode=="gaps": return gaps(state)
    if mode=="opportunities":return opportunities(state)
    if mode=="archive":return archive_watchlist(state)
    if mode=="brief":return mentor_brief(state)
    raise ResearchError("unknown report mode")
