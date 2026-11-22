"""Issue #10 — bounded, canonical-state simulation for canvas proposals.

All changes are applied to an *in-memory copy* for previews. The same function
is executed under the research workspace lock for terminal-approved commits.
No changes to the scientific epistemic status are inferred or auto-approved.
"""
from __future__ import annotations

import copy

from rn_core import (ResearchError, RELATIONS, OUTCOME, WORKFLOW, ARCHIVED, FAILURE,
                     item_by_id, new_item, now, propagate, require, validate_state)
from rn_v02 import (STANCES, EVIDENCE_QUALITIES, SESSION_PROVIDERS, SESSION_ROLES)
from urllib.parse import urlsplit

SAFE_RELATIONS = ("depends-on", "member-of", "contributes-to", "tests", "implements")
SAFE_STATUSES = ("to-be-determined", "ready-for-agent", "to-be-implemented", "in-progress")
CANVAS_OPERATIONS = (
    "add-item", "add-relation", "unlink-relation", "set-status",
    "add-branch", "add-milestone", "revise-criterion", "attach-milestone-evidence",
    "link-evidence",
    "archive-route", "begin-revival-review", "approve-revival-candidate",
    "reject-revival-review",
    "register-session", "link-session", "unlink-session",
)


def _text(value, key, limit=4000):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ResearchError(f"invalid or missing {key}")
    return value.strip()


def _strings(value, key, limit=10):
    if not isinstance(value, list) or not 1 <= len(value) <= limit:
        raise ResearchError(f"{key} must be a non-empty list")
    return [_text(t, key, 500) for t in value]


def validate_extra(operation, args):
    """Reject unexpected or scientific-status override keys at the HTTP boundary."""
    allowed = {
        "add-branch": {"title", "goal", "stop_conditions", "module", "next_action"},
        "add-milestone": {"title", "criteria", "module"},
        "unlink-relation": {"source", "target", "relation"},
        "revise-criterion": {"milestone_id", "criterion_id", "text"},
        "attach-milestone-evidence": {"milestone_id", "criterion_id", "evidence_id"},
        "link-evidence": {"claim_id", "evidence_id", "stance", "scope", "quality", "locator", "note"},
        "archive-route": {"item_id", "lifecycle", "failure_scope", "failure_category",
                          "revival_triggers", "confidence", "lesson", "cost", "evidence_refs"},
        "begin-revival-review": {"item_id", "question", "new_conditions"},
        "approve-revival-candidate": {"item_id", "title", "new_conditions",
                                     "approval_note"},
        "reject-revival-review": {"item_id", "decision_note"},
        "register-session": {"provider", "workspace_id", "session_id", "url"},
        "link-session": {"session_ref_id", "entity_id", "role"},
        "unlink-session": {"session_ref_id", "entity_id"},
    }
    if operation not in allowed:
        raise ResearchError("unsupported canvas semantic operation")
    if set(args) - allowed[operation]:
        raise ResearchError("unsupported semantic field")
    if operation == "add-branch":
        _text(args.get("title"), "branch title", 250)
        _text(args.get("goal"), "branch goal")
        _strings(args.get("stop_conditions"), "stop conditions")
        _text(args.get("module", "topic"), "module", 40)
        if args.get("next_action", ""):
            _text(args["next_action"], "next action")
    elif operation == "add-milestone":
        _text(args.get("title"), "milestone title", 250)
        _strings(args.get("criteria"), "milestone criteria")
        _text(args.get("module", "experiment"), "module", 40)
    elif operation == "unlink-relation":
        if set(args) != {"source", "target", "relation"}:
            raise ResearchError("unlink requires exact relation identity")
        for key in args:
            _text(args[key], key, 120)
        if args["relation"] not in SAFE_RELATIONS:
            raise ResearchError("cannot remove protected/archive provenance relations")
    elif operation == "revise-criterion":
        if set(args) != {"milestone_id", "criterion_id", "text"}:
            raise ResearchError("criterion edit requires milestone, criterion and text")
        _text(args["milestone_id"], "milestone", 120)
        _text(args["criterion_id"], "criterion", 120)
        _text(args["text"], "criterion text", 500)
    elif operation == "attach-milestone-evidence":
        if set(args) != {"milestone_id", "criterion_id", "evidence_id"}:
            raise ResearchError("evidence attachment requires milestone, criterion and evidence")
        for key in args:
            _text(args[key], key, 120)
    elif operation == "archive-route":
        _text(args.get("item_id"), "archived item", 120)
        if args.get("lifecycle") not in ARCHIVED:
            raise ResearchError("archive lifecycle must be parked/quarantined/retired")
        _text(args.get("failure_scope"), "negative evidence limitation")
        _text(args.get("revival_triggers"), "revival triggers")
        if args.get("failure_category", "unknown") not in FAILURE:
            raise ResearchError("invalid failure category")
        for key in ("confidence", "lesson", "cost"):
            if key in args and args[key]:
                _text(args[key], key, 1000)
        refs=args.get("evidence_refs",[])
        if not isinstance(refs,list) or len(refs)>30 or any(not isinstance(i,str) or len(i)>120 for i in refs):
            raise ResearchError("invalid archive evidence references")
    elif operation == "begin-revival-review":
        _text(args.get("item_id"), "archived item", 120)
        _text(args.get("question"), "review question")
        _text(args.get("new_conditions"), "changed circumstances")
    elif operation == "approve-revival-candidate":
        _text(args.get("item_id"), "reviewed item", 120)
        _text(args.get("title"), "candidate title", 250)
        _text(args.get("new_conditions"), "new conditions")
        _text(args.get("approval_note"), "second explicit human authorization")
    elif operation == "reject-revival-review":
        _text(args.get("item_id"), "reviewed item", 120)
        _text(args.get("decision_note"), "review rejection rationale")
    elif operation == "register-session":
        if args.get("provider") not in SESSION_PROVIDERS:
            raise ResearchError("unsupported session provider")
        _text(args.get("workspace_id"), "session workspace", 200)
        _text(args.get("session_id"), "external session id", 300)
        url = args.get("url", "")
        if not isinstance(url, str) or len(url)>1000:
            raise ResearchError("invalid external session URL")
        if url:
            parsed=urlsplit(url)
            if (parsed.scheme!="https" or not parsed.hostname or parsed.username
                or parsed.password or parsed.query or parsed.fragment):
                raise ResearchError("unverified external link must be clean HTTPS")
    elif operation == "link-session":
        for key in ("session_ref_id","entity_id"):
            _text(args.get(key), key, 200)
        if args.get("role") not in SESSION_ROLES:
            raise ResearchError("invalid session role")
    elif operation == "unlink-session":
        if set(args)!={"session_ref_id","entity_id"}:
            raise ResearchError("unlink-session requires exact session/entity pair")
        for key in ("session_ref_id","entity_id"):
            _text(args[key], key, 200)
    elif operation == "link-evidence":
        for key in ("claim_id", "evidence_id", "stance", "scope"):
            _text(args.get(key), key, 1000)
        if args["stance"] not in STANCES:
            raise ResearchError("invalid evidence stance")
        if args.get("quality", "unverified") not in EVIDENCE_QUALITIES:
            raise ResearchError("invalid evidence quality")
        for key in ("quality", "locator", "note"):
            if args.get(key) is not None and (not isinstance(args.get(key), str) or len(args[key]) > 1500):
                raise ResearchError(f"invalid {key}")


def _event(action, item_id, proposal_id, reason, after, before=None):
    event = {"action": action, "item_id": item_id, "actor": "user",
             "proposal_id": proposal_id, "reason": reason, "after": copy.deepcopy(after)}
    if before is not None:
        event["before"] = copy.deepcopy(before)
    return event


def _active(item):
    if item["lifecycle_status"] != "active":
        raise ResearchError("archived/revival-review entity needs formal lifecycle review")
    return item


def _touch(item):
    item["revision"] += 1
    item["updated_at"] = now()


def _milestone(state, ident, *, editable=True):
    item = item_by_id(state, ident)
    if item["type"] != "Milestone":
        raise ResearchError("target must be Milestone")
    _active(item)
    if editable and item["milestone"].get("accepted"):
        raise ResearchError("accepted Milestone cannot be silently edited; use formal review")
    return item


def _criterion(mile, ident):
    return next((c for c in mile["milestone"]["criteria"] if c["id"] == ident), None)


def apply_to_state(state, clean, proposal_id="preview"):
    """Mutate a private state copy; return (result, canonical audit events).

    Caller decides whether to validate only or to commit via rn_core.write().
    """
    op, args, reason = clean["operation"], clean["params"], clean["reason"]
    events = []
    result = {}
    if op == "add-item":
        row = new_item(state, args["type"], args["title"], args["module"],
                       description=args.get("description", ""),
                       next_action=args.get("next_action", ""), actor="user")
        result = {"id": row["id"], "type": row["type"]}
        events.append(_event("item-created", row["id"], proposal_id, reason, row))
    elif op in ("add-relation", "unlink-relation"):
        a, b, t = args["source"], args["target"], args["relation"]
        if t not in SAFE_RELATIONS:
            raise ResearchError("relation must use the controlled lifecycle/evidence workflow")
        first, second = _active(item_by_id(state, a)), _active(item_by_id(state, b))
        row = {"from": a, "to": b, "type": t}
        if op == "add-relation":
            if a == b or row in state["relations"]:
                raise ResearchError("self or duplicate relation")
            if t == "member-of" and second["type"] != "ResearchBranch":
                raise ResearchError("member-of must target ResearchBranch")
            if t == "contributes-to" and second["type"] != "Milestone":
                raise ResearchError("contributes-to must target Milestone")
            state["relations"].append(row)
            if t == "depends-on":
                first["depends_on"].append(b)
            action = "relation-added"
        else:
            if row not in state["relations"]:
                raise ResearchError("relation not found")
            state["relations"].remove(row)
            if t == "depends-on":
                first["depends_on"].remove(b)
            action = "relation-unlinked"
        result = row
        events.append(_event(action, a, proposal_id, reason, row))
    elif op == "set-status":
        item = _active(item_by_id(state, args["item_id"]))
        field, value = args["field"], args["value"]
        if field == "workflow_status":
            if value not in SAFE_STATUSES:
                raise ResearchError("completion/retirement requires primary workflow")
            require(value, WORKFLOW, field)
        elif field == "outcome":
            require(value, OUTCOME, field)
            if item["type"] in ("Result", "Claim", "Milestone"):
                raise ResearchError("scientific result/claim outcomes require evidence workflow")
        else:
            raise ResearchError("review, lifecycle and epistemic changes require main workflow")
        before = item[field]
        if before == value:
            raise ResearchError("no-op status update is not recorded")
        item[field] = value
        _touch(item)
        result = {"id": item["id"], "field": field, "value": value}
        events.append(_event("status-changed", item["id"], proposal_id, reason,
                             {field: value}, {field: before}))
        if field == "outcome":
            events += propagate(state, item["id"], "user", reason)
    elif op == "add-branch":
        row = new_item(state, "ResearchBranch", args["title"],
                       args.get("module", "topic"), actor="user",
                       next_action=args.get("next_action", ""))
        row["branch"] = {"goal": args["goal"], "stop_conditions": args["stop_conditions"],
                         "created_at": now()}
        result = {"id": row["id"], "type": "ResearchBranch"}
        events.append(_event("branch-created", row["id"], proposal_id, reason, row))
    elif op == "add-milestone":
        row = new_item(state, "Milestone", args["title"],
                       args.get("module", "experiment"), actor="user")
        row["milestone"] = {
            "criteria": [{"id":f"C-{n+1:03d}","text":criterion,
                          "evidence_refs":[],"reviewed":False}
                         for n, criterion in enumerate(args["criteria"])],
            "accepted":False, "approval_note":""}
        result = {"id":row["id"], "type":"Milestone"}
        events.append(_event("milestone-created", row["id"], proposal_id, reason, row))
    elif op == "revise-criterion":
        mile = _milestone(state, args["milestone_id"])
        criterion = _criterion(mile, args["criterion_id"])
        if criterion is None:
            raise ResearchError("milestone criterion not found")
        old = criterion["text"]
        if old == args["text"]:
            raise ResearchError("no-op criterion change")
        criterion["text"] = args["text"]
        criterion["reviewed"] = False
        mile["review_status"] = "needs-user-confirmation"
        mile["impact_status"] = "needs-review"
        _touch(mile)
        result = {"id":mile["id"], "criterion_id":criterion["id"], "text":criterion["text"]}
        events.append(_event("milestone-criterion-revised", mile["id"], proposal_id, reason,
                             result, {"criterion_id":criterion["id"], "text":old}))
        events += propagate(state, mile["id"], "user", "criterion requires review")
    elif op == "attach-milestone-evidence":
        mile = _milestone(state, args["milestone_id"])
        criterion = _criterion(mile, args["criterion_id"])
        if criterion is None:
            raise ResearchError("milestone criterion not found")
        evidence_id = args["evidence_id"]
        if evidence_id not in {e["id"] for e in state["sources"]}:
            item_by_id(state, evidence_id)
        if evidence_id in criterion["evidence_refs"]:
            raise ResearchError("duplicate milestone evidence")
        criterion["evidence_refs"].append(evidence_id)
        criterion["reviewed"] = False
        mile["impact_status"] = "needs-review"
        _touch(mile)
        result = {"id":mile["id"],"criterion_id":criterion["id"],"evidence_id":evidence_id}
        events.append(_event("milestone-evidence-attached", mile["id"], proposal_id, reason, result))
    elif op == "link-evidence":
        claim = _active(item_by_id(state, args["claim_id"]))
        if claim["type"] != "Claim":
            raise ResearchError("evidence link requires Claim")
        evidence_id = args["evidence_id"]
        src = next((s for s in state["sources"] if s["id"] == evidence_id), None)
        obj = src if src is not None else item_by_id(state, evidence_id)
        quality = args.get("quality", "unverified")
        if quality == "source-checked" and (src is None or
                src["verification_status"] != "primary-inspected"):
            raise ResearchError("source-checked requires inspected primary source")
        if quality == "experiment-observed" and (obj.get("type") != "Result" or
                not obj.get("observation") or not obj.get("artifact_path")):
            raise ResearchError("experiment-observed requires documented Result artifact")
        if any(x["claim_id"] == claim["id"] and x["evidence_id"] == evidence_id and
               x["stance"] == args["stance"] and x["scope"] == args["scope"]
               for x in state["evidence_links"]):
            raise ResearchError("duplicate evidence link")
        used = {x["id"] for x in state["evidence_links"]}
        i = 1
        while f"EVL-{i:04d}" in used:
            i += 1
        link = {
            "id":f"EVL-{i:04d}","claim_id":claim["id"],"evidence_id":evidence_id,
            "stance":args["stance"],"quality":quality,"scope":args["scope"],
            "locator":args.get("locator",""),"note":args.get("note",""),
            "created_at":now(),"recorded_by":"user"}
        state["evidence_links"].append(link)
        result = {"id":link["id"],"claim_id":claim["id"],"evidence_id":evidence_id}
        events.append(_event("evidence-linked", link["id"], proposal_id, reason, link))
        if args["stance"] == "contradicts":
            before = claim["impact_status"]
            claim["impact_status"] = "needs-review"
            _touch(claim)
            events.append(_event("impact-propagated",claim["id"],proposal_id,reason,
                                 {"impact_status":"needs-review"},{"impact_status":before}))
            events += propagate(state,claim["id"],"user","contradictory evidence")
    elif op == "archive-route":
        item = item_by_id(state, args["item_id"])
        if item["type"] not in ("ResearchQuestion","Idea","Method","Hypothesis",
                                "ExperimentPath","Baseline","Experiment","ResearchBranch"):
            raise ResearchError("this entity cannot be archived as a research route")
        old=item["lifecycle_status"]
        if old=="under-revival-review":
            raise ResearchError("finish formal revival review before archiving")
        if old == args["lifecycle"]:
            raise ResearchError("archive state unchanged")
        refs=args.get("evidence_refs",item.get("evidence_refs",[]))
        known={x["id"] for x in state["items"]+state["sources"]}
        if any(ref not in known for ref in refs):
            raise ResearchError("unknown archive evidence reference")
        if item.get("archive"):
            item.setdefault("archive_history",[]).append(copy.deepcopy(item["archive"]))
        item["archive"]={"reason":reason,"failure_category":args.get("failure_category","unknown"),
            "failure_scope":args["failure_scope"],"diagnostic_confidence":args.get("confidence","uncertain"),
            "revival_triggers":args["revival_triggers"],"lesson":args.get("lesson",""),
            "cost":args.get("cost",""),"decided_by":"user","decided_at":now(),
            "evidence_refs":refs,"previous_state":old}
        item["revival"]=None
        item["lifecycle_status"]=args["lifecycle"]
        _touch(item)
        result={"id":item["id"],"lifecycle_status":item["lifecycle_status"],
                "archive":copy.deepcopy(item["archive"])}
        events.append(_event("status-changed",item["id"],proposal_id,reason,
                             {"lifecycle_status":args["lifecycle"]},{"lifecycle_status":old}))
        events+=propagate(state,item["id"],"user",reason,
                          block=args["lifecycle"] in ("quarantined","retired"))
    elif op == "begin-revival-review":
        item=item_by_id(state,args["item_id"])
        if item["lifecycle_status"] not in ARCHIVED or not item.get("archive"):
            raise ResearchError("only archived entities enter formal revival review")
        old=item["lifecycle_status"]
        item["revival"]={"original_lifecycle":old,"question":args["question"],
            "new_conditions":args["new_conditions"],"requested_by":"user",
            "requested_at":now(),"approved_candidate":None}
        item["lifecycle_status"]="under-revival-review"
        _touch(item)
        result={"id":item["id"],"lifecycle_status":"under-revival-review"}
        events.append(_event("status-changed",item["id"],proposal_id,reason,
            result,{"lifecycle_status":old}))
        events+=propagate(state,item["id"],"user","archived route under formal review")
    elif op == "approve-revival-candidate":
        old=item_by_id(state,args["item_id"])
        if old["lifecycle_status"]!="under-revival-review" or not old.get("revival"):
            raise ResearchError("first formal revival review approval is required")
        if args["new_conditions"].strip()==old["archive"].get("failure_scope","").strip():
            raise ResearchError("candidate must describe changed conditions, not repeat known failure")
        previous=old["revival"]["original_lifecycle"]
        candidate=new_item(state,old["type"],args["title"],old["module"],
            description=f"由 {old['id']} 派生；变化：{args['new_conditions']}；待验证：{reason}",
            actor="user",workflow="to-be-determined",epistemic="hypothesis",
            review="needs-user-confirmation",next_action="设计最低成本证伪/复现实验",
            derived_from=old["id"])
        for kind in ("derived-from","revives"):
            state["relations"].append({"from":candidate["id"],"to":old["id"],"type":kind})
        old["lifecycle_status"]=previous
        old["revival"]=None
        _touch(old)
        result={"id":candidate["id"],"type":candidate["type"],
                "derived_from":old["id"],"original_lifecycle":previous}
        events.append(_event("revival-candidate-created",candidate["id"],proposal_id,reason,
            {**result,"new_conditions":args["new_conditions"],
             "approval_note":args["approval_note"]},
            {"original_lifecycle":"under-revival-review","parent_id":old["id"]}))
    elif op == "reject-revival-review":
        old=item_by_id(state,args["item_id"])
        if old["lifecycle_status"]!="under-revival-review" or not old.get("revival"):
            raise ResearchError("not under formal revival review")
        previous=old["revival"]["original_lifecycle"]
        old["revival"]=None
        old["lifecycle_status"]=previous
        _touch(old)
        result={"id":old["id"],"lifecycle_status":previous}
        events.append(_event("revival-review-rejected",old["id"],proposal_id,
                             args["decision_note"],result))
    elif op == "register-session":
        provider,workspace,sid=args["provider"],args["workspace_id"],args["session_id"]
        if any(x["provider"]==provider and x["workspace_id"]==workspace
               and x["session_id"]==sid for x in state["session_refs"]):
            raise ResearchError("duplicate external SessionRef")
        taken={x["id"] for x in state["session_refs"]}
        counter=1
        while f"SESS-{counter:04d}" in taken:
            counter+=1
        row={"id":f"SESS-{counter:04d}","provider":provider,
             "workspace_id":workspace,"session_id":sid,"url":args.get("url",""),
             "url_verified":False,"entity_ids":[],"roles":{},
             "recorded_by":"user","recorded_at":now()}
        state["session_refs"].append(row)
        result={"id":row["id"],"provider":provider,"workspace_id":workspace}
        events.append(_event("session-registered",row["id"],proposal_id,reason,row))
    elif op in ("link-session","unlink-session"):
        ref=next((s for s in state["session_refs"] if s["id"]==args["session_ref_id"]),None)
        if ref is None:
            raise ResearchError("SessionRef not found")
        entity=item_by_id(state,args["entity_id"])
        if op=="link-session":
            if entity["id"] in ref["entity_ids"]:
                raise ResearchError("duplicate SessionRef entity link")
            ref["entity_ids"].append(entity["id"])
            ref["roles"][entity["id"]]=args["role"]
            action="session-entity-linked"
        else:
            if entity["id"] not in ref["entity_ids"]:
                raise ResearchError("SessionRef link not found")
            ref["entity_ids"].remove(entity["id"])
            ref["roles"].pop(entity["id"])
            action="session-entity-unlinked"
        result={"session_ref_id":ref["id"],"entity_id":entity["id"],
                "role":args.get("role", "removed")}
        events.append(_event(action,ref["id"],proposal_id,reason,result))
    else:
        raise ResearchError("unknown semantic operation")
    # Must use same canonical validator before previewing or committing.
    validate_state(state, strict=True)
    return result, events


def preview_from_state(original, clean):
    """Preview changes without touching state files or event log."""
    revision=original["project"]["revision"]
    if revision != clean["expected_revision"]:
        raise ResearchError("stale proposal; refresh graph and retry")
    before = copy.deepcopy(original)
    after = copy.deepcopy(original)
    result, events = apply_to_state(after, clean)
    previous = {x["id"]:x for x in before["items"]}
    changed = []
    for item in after["items"]:
        prior = previous.get(item["id"])
        if prior != item:
            changed.append({
                "id": item["id"],
                "before": ({"type":prior["type"],"lifecycle":prior["lifecycle_status"],
                            "epistemic":prior["epistemic_status"],
                            "impact":prior["impact_status"],"revision":prior["revision"]}
                           if prior else None),
                "after": {"type":item["type"],"lifecycle":item["lifecycle_status"],
                          "epistemic":item["epistemic_status"],
                          "impact":item["impact_status"],"revision":item["revision"]}})
    return {
        "project_revision":revision,
        "operation":clean["operation"],
        "result":result,
        "impact":changed,
        "changes": [{"action":e["action"],"item_id":e.get("item_id"),
                     "before":e.get("before"),"after":e.get("after")} for e in events],
        "accepted":False,
        "scientifically_validated":False,
        "requires_terminal_approval":True,
        "message":"Preview only; no project files or research claims have been approved",
    }
