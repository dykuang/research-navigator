"""Safe proposal queue and terminal-only approval for Research Navigator local editing.

HTTP is never authorized to mutate canonical research state. The operator must
explicitly approve in an interactive terminal. No broad filesystem APIs.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import secrets

from rn_core import (ResearchError, add_item, add_relation, change_status, load,
                     now, paths, read_json, workspace_lock)

PROPOSAL_OPERATIONS = ("add-item", "add-relation", "set-status")
PUBLIC_ITEM_TYPES = ("Idea", "Hypothesis", "Task", "ResearchQuestion", "Claim", "Risk",
                     "Concept", "ExperimentPath", "Experiment", "Decision")
MAX_FIELDS = 14
MAX_STRING = 4000
PROPOSAL_ID = re.compile(r"^[0-9a-f]{32}$")
REASON_MIN = 8


def _proposal_dir(root):
    p = paths(root)
    return p["root"] / "research" / "canvas" / "proposals"


def _validate_text(obj, key, required=False, maxlen=MAX_STRING):
    value = obj.get(key, "")
    if not isinstance(value, str) or len(value) > maxlen:
        raise ResearchError(f"invalid {key}")
    if required and not value.strip():
        raise ResearchError(f"missing {key}")
    return value


def validate_proposal(root, payload):
    """Pure validation, no filesystem writes."""
    if not isinstance(payload, dict) or len(payload) > 5:
        raise ResearchError("proposal must be a small JSON object")
    if set(payload) != {"operation", "params", "reason", "expected_revision"}:
        raise ResearchError("unexpected proposal fields")
    op = payload["operation"]
    if op not in PROPOSAL_OPERATIONS:
        raise ResearchError("operation not permitted")
    rev = payload["expected_revision"]
    if type(rev) is not int or rev < 0:
        raise ResearchError("expected_revision must be a nonnegative integer")
    reason = _validate_text(payload, "reason", required=True, maxlen=1000)
    if len(reason.strip()) < REASON_MIN:
        raise ResearchError("meaningful reason required")
    args = payload["params"]
    if not isinstance(args, dict) or len(args) > MAX_FIELDS:
        raise ResearchError("invalid params")

    if op == "add-item":
        expected = {"type", "title", "module", "description", "next_action"}
        if set(args) - expected:
            raise ResearchError("unsupported add-item property")
        if args.get("type") not in PUBLIC_ITEM_TYPES:
            raise ResearchError("this item type needs a dedicated domain workflow")
        for key in ("title", "module"):
            _validate_text(args, key, required=True)
        for key in ("description", "next_action"):
            _validate_text(args, key)
    elif op == "add-relation":
        if set(args) != {"source", "target", "relation"}:
            raise ResearchError("relation requires source, target and relation type")
        for key in args:
            _validate_text(args, key, required=True, maxlen=120)
    elif op == "set-status":
        if set(args) != {"item_id", "field", "value"}:
            raise ResearchError("status requires item_id, field and value")
        for key in args:
            _validate_text(args, key, required=True, maxlen=120)
        # Browser cannot request scientific truth promotions or lifecycle/review
        # decisions; these remain in the main Agent/CLI domain workflow.
        if args["field"] not in ("workflow_status", "outcome"):
            raise ResearchError("lifecycle, evidence, review and impact changes need main Agent workflow")
        if args["field"] == "workflow_status" and args["value"] in ("done", "no-further-considered"):
            raise ResearchError("completion/retirement require dedicated approval and evidence")
    return {"operation": op, "params": args, "reason": reason.strip(), "expected_revision": rev}


def queue_proposal(root, payload):
    proposal = validate_proposal(root, payload)
    # Recheck revision while holding the same workspace lock used for canonical writes.
    with workspace_lock(root):
        state = load(root)
        if state["project"]["schema_version"] != "0.2.0":
            raise ResearchError("project must migrate to v0.2 before edits")
        if state["project"]["revision"] != proposal["expected_revision"]:
            raise ResearchError("stale proposal; refresh state and retry")
        pid = secrets.token_hex(16)
        proposal.update({"id": pid, "created_at": now(),
                         "project_id": state["project"]["project_id"],
                         "status": "pending"})
        directory = _proposal_dir(root)
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        file = directory / (pid + ".json")
        # Must be new. No overwrite, no user-supplied filesystem path.
        fd = os.open(file, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as out:
                json.dump(proposal, out, ensure_ascii=False, indent=2)
                out.flush()
                os.fsync(out.fileno())
        except BaseException:
            file.unlink(missing_ok=True)
            raise
    return {"proposal_id": pid, "status": "pending", "expected_revision": proposal["expected_revision"]}


def _open_proposal(root, proposal_id):
    if not PROPOSAL_ID.fullmatch(proposal_id):
        raise ResearchError("invalid proposal identifier")
    path = _proposal_dir(root) / (proposal_id + ".json")
    if not path.is_file() or path.is_symlink():
        raise ResearchError("proposal not found")
    return path, read_json(path)


def inspect_proposal(root, proposal_id):
    _, row = _open_proposal(root, proposal_id)
    return row


def approve_proposal(root, proposal_id, *, confirmed=False):
    """Only callable by the *terminal CLI* after interactive confirmation.

    No HTTP route maps to this function. We intentionally disallow sensitive
    status changes in the browser proposal schema.
    """
    if not confirmed:
        raise ResearchError("approval requires explicit local terminal confirmation")
    # The workspace lock checks the expected revision atomically with mutation.
    # The proposal is only marked applied after a successful canonical write.
    path, p = _open_proposal(root, proposal_id)
    clean = validate_proposal(root, {k:p[k] for k in ("operation","params","reason","expected_revision")})
    if p.get("status") != "pending":
        raise ResearchError("proposal already processed")
    with workspace_lock(root):
        state = load(root)
        if state["project"]["project_id"] != p["project_id"]:
            raise ResearchError("proposal belongs to another project")
        if state["project"]["revision"] != p["expected_revision"]:
            raise ResearchError("stale proposal; no state was changed")
        # This flag is checked again under lock to avoid a duplicate approval.
        live = read_json(path)
        if live.get("status") != "pending":
            raise ResearchError("proposal already processed")
        # Delegating to rn_core's public mutators would reacquire the workspace
        # lock, potentially deadlocking. Apply to a copy and commit once below.
        import copy
        from rn_core import (new_item, item_by_id, RELATIONS, require, propagate,
                             write, WORKFLOW, OUTCOME)
        state = copy.deepcopy(state)
        args = clean["params"]
        op = clean["operation"]
        events = []
        if op == "add-item":
            row = new_item(state, args["type"], args["title"], args["module"],
                           description=args.get("description", ""),
                           next_action=args.get("next_action", ""), actor="user")
            events.append({"action":"item-created","actor":"user",
                           "item_id":row["id"],"reason":clean["reason"],
                           "proposal_id":proposal_id,"after":copy.deepcopy(row)})
            result = {"id": row["id"]}
        elif op == "add-relation":
            a,b,t = args["source"],args["target"],args["relation"]
            require(t, RELATIONS, "relation")
            item_by_id(state,a);item_by_id(state,b)
            row = {"from":a,"to":b,"type":t}
            if a == b or row in state["relations"]:
                raise ResearchError("self or duplicate relation")
            if t == "member-of" and item_by_id(state,b)["type"] != "ResearchBranch":
                raise ResearchError("member-of target must be ResearchBranch")
            if t == "contributes-to" and item_by_id(state,b)["type"] != "Milestone":
                raise ResearchError("contributes-to target must be Milestone")
            state["relations"].append(row)
            if t == "depends-on":
                item_by_id(state,a)["depends_on"].append(b)
            events.append({"action":"relation-added","actor":"user","item_id":a,
                           "reason":clean["reason"],"proposal_id":proposal_id,"after":row})
            if t in ("blocks","contradicts"):
                target = item_by_id(state,b)
                target["impact_status"] = "blocked" if t == "blocks" else "needs-review"
                target["revision"] += 1;target["updated_at"] = now()
                events.extend(propagate(state,b,"user",clean["reason"],block=t=="blocks"))
            result = row
        else:
            ident, field, value = args["item_id"], args["field"], args["value"]
            require(value,WORKFLOW if field=="workflow_status" else OUTCOME, field)
            row = item_by_id(state, ident)
            prior = row[field]
            if prior == value:
                raise ResearchError("no-op status update is not recorded")
            row[field] = value;row["revision"] += 1;row["updated_at"] = now()
            if field == "outcome":
                events.extend(propagate(state,ident,"user",clean["reason"]))
            events.insert(0,{"action":"status-changed","actor":"user","item_id":ident,
                             "proposal_id":proposal_id,"reason":clean["reason"],
                             "before":{field:prior},"after":{field:value}})
            result = {"id":ident,"field":field,"value":value}
        # Validation and revision checks occur in canonical write().
        write(root,state,events,expected_revision=p["expected_revision"])
        # A crash between write and proposal acknowledgement can be recognized
        # by event proposal_id on next approval attempt (do not double-apply).
        live["status"] = "applied"
        live["applied_at"] = now()
        live["result"] = result
        from rn_core import atomic_json
        atomic_json(path, live)
        return {"status":"applied","result":result,
                "revision":state["project"]["revision"]}
