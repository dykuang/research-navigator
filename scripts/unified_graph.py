"""v0.6 unified research graph: one read-only projection, no second truth store.

Scientific records remain in research/state; human-attributed interview answers
in research/interviews; canvas context links merely cross-reference existing
entities. Visual metadata stays in views.json. No LLM inference is made.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from rn_core import ResearchError, load, read_json, paths
from graph_projection import project_graph

SCHEMA = "unified-research-graph-v1"
CONTEXT_SCHEMA = "canvas-context-links-v1"
NAMESPACES = ("item", "source", "evidence", "session", "criterion",
              "interview", "question", "answer")
CONTEXT_RULES = {
    "addresses": (("question",), ("item",)),
    "motivates": (("answer",), ("item",)),
    "context-for": (("source", "evidence", "item"), ("criterion",)),
    "discussed-in-session": (("session",), ("interview", "question", "answer")),
    "informs": (("item",), ("criterion",)),
    "references-route": (("question", "answer"), ("item",)),
}
CONTEXT_TYPES = tuple(CONTEXT_RULES)
ID_RE = re.compile(r"^(item|source|evidence|session|criterion|interview|question|answer):[A-Za-z0-9-]{1,180}$")

def context_path(root):
    return paths(root)["root"] / "research" / "canvas" / "context-links.json"

def empty_context(project_id):
    return {"schema_version": CONTEXT_SCHEMA, "project_id": project_id,
            "revision": 0, "links": []}

def read_context(root, state=None):
    state = state if state is not None else load(root)
    path = context_path(root)
    if not path.exists():
        return empty_context(state["project"]["project_id"])
    try:
        value = read_json(path)
    except (ValueError, OSError) as exc:
        raise ResearchError("Corrupt canvas context links; restore backup") from exc
    if not isinstance(value, dict) or set(value) != {"schema_version", "project_id", "revision", "links"}:
        raise ResearchError("Invalid canvas context schema")
    if value["schema_version"] != CONTEXT_SCHEMA or value["project_id"] != state["project"]["project_id"]:
        raise ResearchError("Cross-project canvas context links forbidden")
    if type(value["revision"]) is not int or value["revision"] < 0 or not isinstance(value["links"], list) or len(value["links"]) > 10000:
        raise ResearchError("Invalid context revision/links")
    found = set()
    for link in value["links"]:
        if not isinstance(link, dict) or set(link) != {"id", "from", "to", "type", "reason", "proposal_id", "recorded_at"}:
            raise ResearchError("Invalid canvas link row")
        if not isinstance(link["id"], str) or not re.fullmatch(r"context:[0-9a-f]{24}", link["id"]):
            raise ResearchError("Invalid context link ID")
        if link["id"] in found:
            raise ResearchError("Duplicate context link ID")
        found.add(link["id"])
        validate_link_fields(link["from"], link["to"], link["type"])
        if not isinstance(link["reason"], str) or not 8 <= len(link["reason"]) <= 1000:
            raise ResearchError("Invalid context link reason")
        if not isinstance(link["proposal_id"], str) or not re.fullmatch(r"[0-9a-f]{32}", link["proposal_id"]):
            raise ResearchError("Context links require genuine proposal ID")
        if not isinstance(link["recorded_at"], str):
            raise ResearchError("Invalid link timestamp")
    return value

def validate_link_fields(source, target, relation):
    if not isinstance(source, str) or not ID_RE.fullmatch(source):
        raise ResearchError("Invalid source graph node ID")
    if not isinstance(target, str) or not ID_RE.fullmatch(target):
        raise ResearchError("Invalid target graph node ID")
    if source == target or relation not in CONTEXT_RULES:
        raise ResearchError("Invalid/self context relation")
    from_types, to_types = CONTEXT_RULES[relation]
    if source.split(":", 1)[0] not in from_types or target.split(":", 1)[0] not in to_types:
        raise ResearchError("Context relation ports are incompatible")
    return True

def _stable_edge(source, target, relation, context=""):
    raw = json.dumps([source, target, relation, context],
                     ensure_ascii=False, separators=(",", ":"))
    return "edge:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]

def _base_node(nid, entity_id, kind, type_, label, description="", *, metadata=None,
               statuses=None, module=None, actionable=False):
    return {"id": nid, "entity_id": entity_id, "kind": kind,
            "type": type_, "label": str(label), "description": str(description),
            "module": module, "statuses": statuses or {},
            "metadata": metadata or {}, "actionable": actionable}

def _view_ports(node):
    kind = node["kind"]
    inputs = sorted(t for t, (_, allowed) in CONTEXT_RULES.items() if kind in allowed)
    outputs = sorted(t for t, (allowed, _) in CONTEXT_RULES.items() if kind in allowed)
    node["ports"] = {"inputs": inputs, "outputs": outputs}
    node["truth_authority"] = ("interview" if kind in ("interview", "question", "answer")
                              else "presentation-reference" if kind == "criterion"
                              else "scientific-state")
    return node

def _interview_nodes(root, project_id, nodes, edges):
    from rn_interview import read, frontier, interview_path
    if not interview_path(root).exists():
        return {"status": "not-started", "revision": None, "questions": 0}
    try:
        document = read(root)
    except (ResearchError, ValueError, KeyError) as exc:
        # An existing corrupt/foreign interview is never silently erased.
        raise ResearchError("Cannot project corrupt/mismatched interview: " + str(exc)) from exc
    if document["project_id"] != project_id:
        raise ResearchError("Interview project mismatch")
    ident = document["interview_id"]
    iid = "interview:" + ident
    nodes[iid] = _base_node(iid, ident, "interview", "GrillingInterview",
                           document["topic"], "Interview context; not scientific proof",
                           metadata={"round": document["round"],
                                     "consensus_note": document.get("consensus_note", ""),
                                     "accepted_open_questions": document.get("accepted_open_questions", [])},
                           statuses={"interview_status": document["status"]}, module="topic")
    for q in document["questions"]:
        qid = "question:" + ident + "-" + q["id"]
        aid = "answer:" + ident + "-" + q["id"]
        question = _base_node(
            qid, q["id"], "question", "InterviewQuestion", q["text"],
            "Unanswered/deferred/confirmed question; no scientific validity inferred",
            metadata={"why": q["why"], "options": q.get("options", ""),
                      "choices": q.get("choices", []),
                      "recommended_choice_id": q.get("recommended_choice_id"),
                      "lowest_cost_check": q["lowest_cost_check"],
                      "round": q["round"], "depends_on": q["depends_on"]},
            statuses={"question_status": q["status"], "interview_status": document["status"]},
            module="topic")
        nodes[qid] = question
        nodes[aid] = _base_node(
            aid, q["id"], "answer", "InterviewAnswer",
            q["answer"] if q["status"] == "answered" else "(not confirmed)",
            "Conversation answer is NOT verified scientific evidence",
            metadata={"selected_option_id": q.get("selected_option_id"),
                      "custom_answer": q.get("custom_answer"),
                      "supplement": q.get("supplement"),
                      "confirmed_by": q.get("confirmed_by"),
                      "answer_source": q.get("answer_source", "unanswered")},
            statuses={"answer_status": q["status"], "interview_status": document["status"]},
            module="topic")
        edges.append({"id": _stable_edge(iid, qid, "contains-question"),
                      "from": iid, "to": qid, "type": "contains-question",
                      "provenance": {"collection": "research/interviews", "read_only": True}})
        edges.append({"id": _stable_edge(qid, aid, "has-answer"),
                      "from": qid, "to": aid, "type": "has-answer",
                      "provenance": {"collection": "research/interviews", "read_only": True}})
    for q in document["questions"]:
        for dep in q["depends_on"]:
            source = "question:" + ident + "-" + q["id"]
            target = "question:" + ident + "-" + dep
            edges.append({"id": _stable_edge(source, target, "depends-on"),
                          "from": source, "to": target, "type": "depends-on",
                          "provenance": {"collection": "research/interviews", "read_only": True}})
    return {"status": document["status"], "revision": document["revision"],
            "questions": len(document["questions"])}

def _criteria(state, nodes, edges):
    sources = {n["id"] for n in nodes.values()}
    for item in state["items"]:
        if item["type"] != "Milestone":
            continue
        metadata = item.get("milestone") or {}
        for criterion in metadata.get("criteria", []):
            cid = "criterion:" + item["id"] + "-" + criterion["id"]
            if cid in nodes:
                raise ResearchError("Duplicate milestone criterion ID")
            verified = bool(criterion.get("reviewed")) and bool(metadata.get("accepted"))
            nodes[cid] = _base_node(
                cid, criterion["id"], "criterion", "MilestoneCriterion", criterion["text"],
                "Linked evidence does not automatically satisfy this criterion",
                module="experiment",
                metadata={"milestone_id": item["id"],
                          "evidence_refs": criterion.get("evidence_refs", [])},
                statuses={"reviewed": bool(criterion.get("reviewed")),
                          "milestone_accepted": bool(metadata.get("accepted")),
                          "satisfied": verified})
            source = "item:" + item["id"]
            edges.append({"id": _stable_edge(source, cid, "has-criterion"),
                          "from": source, "to": cid, "type": "has-criterion",
                          "provenance": {"collection": "research/state", "read_only": True}})
            for ref in criterion.get("evidence_refs", []):
                target = "item:" + ref if "item:" + ref in sources else "source:" + ref
                if target not in nodes:
                    raise ResearchError("Dangling milestone criterion evidence")
                edges.append({"id": _stable_edge(target, cid, "cited-for-criterion"),
                              "from": target, "to": cid, "type": "cited-for-criterion",
                              "provenance": {"collection": "research/state", "read_only": True,
                                             "scientifically_verified": False}})
    return True

def validate_context_link(graph, source, target, relation):
    validate_link_fields(source, target, relation)
    nodes = {n["id"]: n for n in graph["nodes"]}
    if source not in nodes or target not in nodes:
        raise ResearchError("Context reference missing graph node")
    if nodes[source].get("statuses", {}).get("lifecycle_status") not in (None, "active"):
        raise ResearchError("Archived source cannot be edited outside formal revival")
    if nodes[target].get("statuses", {}).get("lifecycle_status") not in (None, "active"):
        raise ResearchError("Archived target cannot be edited outside formal revival")
    if relation == "informs":
        if nodes[source]["type"] not in ("Claim", "Result", "ExperimentRun", "Hypothesis"):
            raise ResearchError("Only scientific claim, result, run or hypothesis informs criterion")
    if relation == "context-for" and nodes[source]["type"] not in ("Source", "EvidenceLink", "Result", "ExperimentRun"):
        raise ResearchError("Context-for requires actual Source, EvidenceLink or Result/Run")
    return True

def unified_graph(root, *, include_context=True):
    state = load(root)
    base = project_graph(state, view="all", limit=None)
    nodes = {n["id"]: n for n in base["nodes"]}
    edges = list(base["edges"])
    _criteria(state, nodes, edges)
    interview = _interview_nodes(root, state["project"]["project_id"], nodes, edges)
    for node in nodes.values():
        _view_ports(node)
    extra = read_context(root, state) if include_context else empty_context(state["project"]["project_id"])
    # Validate stored references against the present graph, including archive gates.
    shallow = {"nodes": list(nodes.values())}
    for link in extra["links"]:
        validate_context_link(shallow, link["from"], link["to"], link["type"])
        edges.append({"id": link["id"], "from": link["from"], "to": link["to"],
                      "type": link["type"], "provenance": {
                          "collection": "research/canvas/context-links",
                          "proposal_id": link["proposal_id"],
                          "reason": link["reason"],
                          "context_only": True, "scientifically_verified": False}})
    if len({e["id"] for e in edges}) != len(edges):
        raise ResearchError("Duplicate unified graph edges")
    base.update({
        "schema_version": SCHEMA,
        "nodes": sorted(nodes.values(), key=lambda n: n["id"]),
        "edges": sorted(edges, key=lambda e: e["id"]),
        "interview": interview,
        "context_revision": extra["revision"],
        "single_scientific_authority": True,
        "no_auto_scientific_confirmation": True,
        "page": {"returned_nodes": len(nodes), "total_graph_nodes": len(nodes),
                 "total_graph_edges": len(edges)}
    })
    return base

def inspect_context_candidate(root, source, target, relation, expected_revision):
    state=load(root)
    graph=unified_graph(root)
    if state["project"]["revision"]!=expected_revision:
        raise ResearchError("stale proposal; refresh scientific graph")
    validate_context_link(graph, source, target, relation)
    if any(e["from"]==source and e["to"]==target and e["type"]==relation for e in graph["edges"]):
        raise ResearchError("Duplicate context link")
    return {"before": None, "after": {"from": source, "to": target, "type": relation},
            "impact": "Reference-only, not scientific support, approval or experiment execution",
            "context_revision": graph["context_revision"],
            "scientific_revision_unchanged": True}

def main():
    p=argparse.ArgumentParser(description="Read-only v0.6 unified research graph")
    p.add_argument("root")
    args=p.parse_args()
    print(json.dumps(unified_graph(args.root),ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
