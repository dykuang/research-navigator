"""Deterministic, read-only typed graph projection of Research Navigator state (#7).

Canonical research state is never edited here. All graph IDs are namespaced to
avoid collisions between item/Source/SessionRef/EvidenceLink collections.
No chat contents, experimental conclusions, or approval are inferred.
"""
from __future__ import annotations

import argparse
from collections import deque
import hashlib
import json

from rn_core import ResearchError, load, validate_state

VIEWS = ("all", "planning", "archive", "risk", "evidence", "routes", "outputs")
NODE_TYPES = ("item", "source", "evidence-link", "session-ref")
NAMESPACE = {"items": "item", "sources": "source",
             "evidence_links": "evidence", "session_refs": "session"}


def _key(collection, ident):
    return NAMESPACE[collection] + ":" + ident


def _edge_id(kind, source, target, extra=""):
    raw = json.dumps([kind, source, target, extra], ensure_ascii=False,
                     separators=(",", ":"))
    return "edge:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def _item_node(item):
    keys = ("workflow_status", "epistemic_status", "review_status",
            "outcome", "lifecycle_status", "impact_status")
    kind = item["type"]
    metadata = {
        "owner": item.get("owner", ""),
        "next_action": item.get("next_action", ""),
        "acceptance_criteria": item.get("acceptance_criteria", ""),
        "archive": item.get("archive"),
        "archive_history": item.get("archive_history", []),
        "revival": item.get("revival"),
        "archive_reason": (item.get("archive") or {}).get("reason", ""),
        "archive_scope": (item.get("archive") or {}).get("failure_scope", ""),
        "revival_triggers": (item.get("archive") or {}).get("revival_triggers", ""),
        "derived_from": item.get("derived_from"),
        "branch": item.get("branch") if kind == "ResearchBranch" else None,
        "milestone": item.get("milestone") if kind == "Milestone" else None,
        "evidence_refs": item.get("evidence_refs", []),
        "artifact_path": item.get("artifact_path", ""),
        "observation": item.get("observation", ""),
    }
    return {
        "id": _key("items", item["id"]), "entity_id": item["id"],
        "kind": "item", "type": kind, "label": item["title"],
        "description": item.get("description", ""),
        "module": item["module"], "created_at": item.get("created_at"),
        "revision": item.get("revision"),
        "statuses": {key: item.get(key) for key in keys},
        "metadata": metadata,
        "actionable": (item.get("lifecycle_status") == "active"
                       and item.get("impact_status") == "current"
                       and item.get("review_status") != "rejected"
                       and item.get("workflow_status") not in
                       ("done", "no-further-considered")),
    }


def _nodes_edges(state):
    nodes = {}
    edges = {}

    def add_node(node):
        if node["id"] in nodes:
            raise ResearchError("graph projection: duplicate stable node ID")
        nodes[node["id"]] = node

    def add_edge(source, target, edge_type, origin, locator, extra=""):
        if source not in nodes or target not in nodes:
            raise ResearchError("graph projection: dangling " + edge_type + " edge")
        eid = _edge_id(origin, source, target, edge_type + ":" + extra)
        if eid in edges:
            raise ResearchError("graph projection: duplicate edge identity")
        edges[eid] = {"id": eid, "from": source, "to": target,
                      "type": edge_type, "provenance": {
                          "collection": origin, "key": locator}}
        return eid

    # Bounded decision trail, preserving each canonical event without mutating it.
    history = {}
    for event in state.get("events", []):
        ident=event.get("item_id")
        if isinstance(ident,str):
            history.setdefault(ident,[]).append({
                "action":event.get("action"),"actor":event.get("actor"),
                "reason":event.get("reason"),"timestamp":event.get("timestamp",event.get("at")),
                "before":event.get("before"),"after":event.get("after"),
                "proposal_id":event.get("proposal_id"),
            })
    for item in state["items"]:
        node=_item_node(item)
        node["metadata"]["decision_history"]=history.get(item["id"],[])[-25:]
        add_node(node)
    for src in state["sources"]:
        add_node({
            "id": _key("sources", src["id"]), "entity_id": src["id"],
            "kind": "source", "type": "Source", "label": src["title"],
            "description": src.get("summary", ""),
            "module": "literature", "created_at": src.get("accessed_at"),
            "statuses": {"verification_status": src.get("verification_status"),
                         "access_level": src.get("access_level")},
            "metadata": {"url": src.get("url", ""), "doi": src.get("doi", ""),
                         "locator": src.get("locator", ""),
                         "verification_note": src.get("verification_note", "")},
            "actionable": False,
        })
    for link in state.get("evidence_links", []):
        add_node({
            "id": _key("evidence_links", link["id"]), "entity_id": link["id"],
            "kind": "evidence-link", "type": "EvidenceLink",
            "label": link["stance"] + " · " + link["scope"],
            "description": link.get("note", ""),
            "module": "literature", "created_at": link.get("created_at"),
            "statuses": {"stance": link["stance"],
                         "quality": link["quality"]},
            "metadata": {"scope": link["scope"],
                         "locator": link.get("locator", ""),
                         "claim_id": link["claim_id"],
                         "evidence_id": link["evidence_id"],
                         "recorded_by": link.get("recorded_by", "")},
            "actionable": False,
        })
    for session in state.get("session_refs", []):
        add_node({
            "id": _key("session_refs", session["id"]),
            "entity_id": session["id"], "kind": "session-ref",
            "type": "SessionRef",
            "label": session["provider"] + " · " + session["id"],
            "description": "External session reference; chat text not stored",
            "module": None, "created_at": session.get("recorded_at"),
            "statuses": {"url_verified": session.get("url_verified", False)},
            "metadata": {"provider": session["provider"],
                         "workspace_id": session.get("workspace_id", ""),
                         "session_id": session.get("session_id", ""),
                         "url": session.get("url", ""),
                         "recorded_by": session.get("recorded_by", "")},
            "actionable": False,
        })

    source_ids = {s["id"] for s in state["sources"]}
    item_ids = {i["id"] for i in state["items"]}
    for relation in state["relations"]:
        add_edge(_key("items", relation["from"]),
                 _key("items", relation["to"]), relation["type"],
                 "relations",
                 {"from": relation["from"], "to": relation["to"],
                  "type": relation["type"]})
    for item in state["items"]:
        # Legacy loose evidence_refs are preserved and clearly tagged as such.
        for ref in sorted(set(item.get("evidence_refs", []))):
            if ref in source_ids:
                target = _key("sources", ref)
            elif ref in item_ids:
                target = _key("items", ref)
            else:
                raise ResearchError("graph projection: missing evidence ref")
            add_edge(_key("items", item["id"]), target, "references",
                     "items.evidence_refs", {"item_id": item["id"], "ref": ref})
    for link in state.get("evidence_links", []):
        middle = _key("evidence_links", link["id"])
        add_edge(_key("items", link["claim_id"]), middle,
                 "has-evidence-link", "evidence_links",
                 {"id": link["id"], "part": "claim"})
        eid = link["evidence_id"]
        target = (_key("sources", eid) if eid in source_ids
                  else _key("items", eid))
        add_edge(middle, target, link["stance"], "evidence_links",
                 {"id": link["id"], "part": "evidence"})
    for session in state.get("session_refs", []):
        for entity_id in sorted(session["entity_ids"]):
            add_edge(_key("session_refs", session["id"]),
                     _key("items", entity_id),
                     "session:" + session["roles"][entity_id],
                     "session_refs",
                     {"id": session["id"], "entity_id": entity_id})
    return nodes, edges


def project_graph(state, *, view="all", module=None, branch=None,
                  lifecycle=None, impact=None, since=None, until=None,
                  evidence_quality=None, text=None, focus=None, depth=1,
                  offset=0, limit=250):
    """Project the supplied already-loaded state into a typed graph.

    Use limit=None to fetch all nodes (e.g. a self-contained offline Canvas).
    Otherwise page nodes deterministically by ID; edges are induced by the
    page. Full-graph traversal uses focus + depth for a coherent neighborhood.
    """
    validate_state(state, strict=True)
    if view not in VIEWS:
        raise ResearchError("invalid graph view")
    if not isinstance(offset, int) or isinstance(offset, bool) or offset < 0:
        raise ResearchError("offset must be >=0")
    if limit is not None and (not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 1000):
        raise ResearchError("limit must be 1..1000 or None")
    if not isinstance(depth, int) or isinstance(depth, bool) or not 0 <= depth <= 6:
        raise ResearchError("depth must be 0..6")
    nodes, edges = _nodes_edges(state)
    all_edges = sorted(edges.values(), key=lambda e: e["id"])
    active = set(nodes)

    if view == "planning":
        active &= {nid for nid, n in nodes.items()
                   if n["kind"] != "item" or n["actionable"]}
    elif view == "archive":
        active &= {nid for nid, n in nodes.items()
                   if n["kind"] == "item" and
                   n["statuses"].get("lifecycle_status") != "active"}
    elif view == "evidence":
        active &= {nid for nid, n in nodes.items()
                   if n["type"] in ("Claim", "Result", "Source", "EvidenceLink",
                                    "Hypothesis", "Milestone")}
    elif view == "routes":
        active &= {nid for nid, n in nodes.items()
                   if n["type"] in ("ResearchBranch", "Milestone",
                                    "ResearchQuestion", "Idea", "Hypothesis",
                                    "Experiment", "Result", "Baseline", "Task")}
    elif view == "outputs":
        active &= {nid for nid, n in nodes.items()
                   if n["type"] in ("Milestone", "Claim", "Artifact",
                                    "Result", "Decision", "Source", "EvidenceLink")}

    if module:
        active &= {nid for nid, n in nodes.items()
                   if n.get("module") == module}
    if lifecycle:
        active &= {nid for nid, n in nodes.items()
                   if n["statuses"].get("lifecycle_status") == lifecycle}
    if impact:
        active &= {nid for nid, n in nodes.items()
                   if n["statuses"].get("impact_status") == impact}
    if since:
        active &= {nid for nid, n in nodes.items()
                   if n.get("created_at") and n["created_at"] >= since}
    if until:
        active &= {nid for nid, n in nodes.items()
                   if n.get("created_at") and n["created_at"] <= until}
    if evidence_quality:
        active &= {nid for nid, n in nodes.items()
                   if n["statuses"].get("quality") == evidence_quality}
    if text:
        needle = text.casefold()
        active &= {nid for nid, n in nodes.items()
                   if needle in (n["label"] + " " + n["entity_id"] + " " +
                                 (n.get("description") or "")).casefold()}

    adjacency = {nid: set() for nid in nodes}
    for edge in all_edges:
        adjacency[edge["from"]].add(edge["to"])
        adjacency[edge["to"]].add(edge["from"])

    def resolve(query):
        if query in nodes:
            return query
        matching = [n for n in nodes if nodes[n]["entity_id"] == query]
        if len(matching) == 1:
            return matching[0]
        raise ResearchError("unknown or ambiguous graph entity ID; use namespaced ID")

    if branch:
        branch_id = resolve(branch)
        if nodes[branch_id]["type"] != "ResearchBranch":
            raise ResearchError("branch filter requires a ResearchBranch")
        # Direct member nodes + contributed milestones (no unrelated neighbors).
        related = {branch_id}
        related.update(adjacency[branch_id])
        active &= related
    if focus:
        root = resolve(focus)
        seen = {root}
        queue = deque([(root, 0)])
        while queue:
            current, distance = queue.popleft()
            if distance >= depth:
                continue
            for nxt in sorted(adjacency[current]):
                if nxt not in seen:
                    seen.add(nxt)
                    queue.append((nxt, distance + 1))
        active &= seen

    visible = sorted(active)
    total = len(visible)
    selected = visible[offset:] if limit is None else visible[offset:offset + limit]
    selected_ids = set(selected)
    induced = [e for e in all_edges
               if e["from"] in selected_ids and e["to"] in selected_ids]
    next_offset = offset + len(selected)
    return {
        "schema_version": "graph-v1",
        "project_id": state["project"]["project_id"],
        "project_revision": state["project"]["revision"],
        "view": view, "filters": {
            "module": module, "branch": branch, "lifecycle": lifecycle,
            "impact": impact, "since": since, "until": until,
            "evidence_quality": evidence_quality, "text": text,
            "focus": focus, "depth": depth,
        },
        "nodes": [nodes[nid] for nid in selected], "edges": induced,
        "page": {"offset": offset, "limit": limit,
                 "total_nodes": total, "returned_nodes": len(selected),
                 "next_offset": next_offset if next_offset < total else None,
                 "total_graph_nodes": len(nodes),
                 "total_graph_edges": len(edges)},
    }


def main():
    parser = argparse.ArgumentParser(description="Read-only typed graph export for v0.2")
    parser.add_argument("root", help="research project root")
    parser.add_argument("--view", choices=VIEWS, default="all")
    parser.add_argument("--module")
    parser.add_argument("--branch")
    parser.add_argument("--lifecycle")
    parser.add_argument("--impact")
    parser.add_argument("--since")
    parser.add_argument("--until")
    parser.add_argument("--evidence-quality")
    parser.add_argument("--text")
    parser.add_argument("--focus")
    parser.add_argument("--depth", type=int, default=1)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--limit", type=int, default=250)
    parser.add_argument("--all", action="store_true", help="no pagination")
    args = parser.parse_args()
    try:
        result = project_graph(load(args.root), view=args.view, module=args.module,
                  branch=args.branch, lifecycle=args.lifecycle, impact=args.impact,
                  since=args.since, until=args.until,
                  evidence_quality=args.evidence_quality, text=args.text,
                  focus=args.focus, depth=args.depth, offset=args.offset,
                  limit=None if args.all else args.limit)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (ResearchError, OSError, ValueError) as e:
        parser.error(str(e))


if __name__ == "__main__":
    main()
