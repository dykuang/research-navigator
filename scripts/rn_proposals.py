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

from rn_canvas_semantics import (CANVAS_OPERATIONS, SAFE_RELATIONS, validate_extra,
                                 apply_to_state, preview_from_state)

CONTEXT_OPERATIONS = ("link-context", "unlink-context")
PROPOSAL_OPERATIONS = CANVAS_OPERATIONS + CONTEXT_OPERATIONS
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
        if args["relation"] not in SAFE_RELATIONS:
            raise ResearchError("revival, supersession, support and blocking edges need the main Agent workflow")
    elif op == "set-status":
        if set(args) != {"item_id", "field", "value"}:
            raise ResearchError("status requires item_id, field and value")
        for key in args:
            _validate_text(args, key, required=True, maxlen=120)
        # Browser cannot request scientific truth promotions or lifecycle/review
        # decisions; these remain in the main Agent/CLI domain workflow.
        if args["field"] not in ("workflow_status", "outcome"):
            raise ResearchError("lifecycle, evidence, review and impact changes need main Agent workflow")
        if args["field"] == "workflow_status" and args["value"] not in (
            "to-be-determined", "ready-for-agent", "to-be-implemented", "in-progress"
        ):
            raise ResearchError("blocking, completion and retirement require main Agent workflow")
    elif op == "link-context":
        if set(args) != {"from","to","relation","expected_context_revision"}:
            raise ResearchError("Context link requires exact source, target, relation and context revision")
        from unified_graph import validate_link_fields
        validate_link_fields(args["from"], args["to"], args["relation"])
        if type(args["expected_context_revision"]) is not int or args["expected_context_revision"]<0:
            raise ResearchError("Invalid context revision")
    elif op == "unlink-context":
        if set(args) != {"link_id","expected_context_revision"}:
            raise ResearchError("Context unlink requires exact edge and context revision")
        if not isinstance(args["link_id"],str) or not re.fullmatch(r"context:[0-9a-f]{24}",args["link_id"]):
            raise ResearchError("Invalid context link ID")
        if type(args["expected_context_revision"]) is not int or args["expected_context_revision"]<0:
            raise ResearchError("Invalid context revision")
    else:
        validate_extra(op, args)
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
        # Reject structurally invalid or unauthorized semantic changes before
        # placing the proposal in the queue; no canonical files are modified.
        if proposal["operation"] in CONTEXT_OPERATIONS:
            _preview_context(root,proposal)
        else:
            preview_from_state(state, proposal)
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
    if p.get("id") != proposal_id:
        raise ResearchError("proposal file identifier mismatch")
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
        if p["operation"] in CONTEXT_OPERATIONS:
            from unified_graph import commit_context_proposal
            result=commit_context_proposal(root,clean,proposal_id=proposal_id)
            live["status"]="applied"
            live["applied_at"]=now()
            live["result"]=result
            from rn_core import atomic_json
            atomic_json(path,live)
            return {"status":"applied","result":result,
                    "revision":state["project"]["revision"],
                    "context_only":True}
        # Simulate the exact approved change on a private copy; the canonical
        # write occurs exactly once and preserves the event-based audit trail.
        import copy
        from rn_core import write
        state = copy.deepcopy(state)
        result, events = apply_to_state(state, clean, proposal_id=proposal_id)
        # Validation and revision checks occur in canonical write().
        write(root,state,events,expected_revision=p["expected_revision"])
        # A crash between write and acknowledgement is detected via revision
        # and event proposal_id; it cannot be silently applied a second time.
        live["status"] = "applied"
        live["applied_at"] = now()
        live["result"] = result
        from rn_core import atomic_json
        atomic_json(path, live)
        return {"status":"applied","result":result,
                "revision":state["project"]["revision"]}



def _preview_context(root, clean):
    from unified_graph import (inspect_context_candidate,inspect_unlink_candidate,
                               read_context)
    params=clean["params"]
    if read_context(root)["revision"]!=params["expected_context_revision"]:
        raise ResearchError("stale context revision; refresh before submitting")
    if clean["operation"]=="link-context":
        return inspect_context_candidate(root,params["from"],params["to"],
                                         params["relation"],clean["expected_revision"])
    return inspect_unlink_candidate(root,params["link_id"],clean["expected_revision"])


def preview_proposal(root, payload):
    """Preview a concrete before/after/impact; never enqueue or edit state."""
    clean = validate_proposal(root, payload)
    state = load(root)
    if state["project"].get("schema_version") != "0.2.0":
        raise ResearchError("migrate project before semantic proposals")
    if clean["operation"] in CONTEXT_OPERATIONS:
        return _preview_context(root,clean)
    return preview_from_state(state, clean)


def proposal_status(root, proposal_id):
    """Minimal status result for the authenticated local browser."""
    row = inspect_proposal(root, proposal_id)
    current = load(root)["project"]
    if row.get("project_id") != current["project_id"]:
        raise ResearchError("wrong project")
    return {"proposal_id":proposal_id, "status":row["status"],
            "expected_revision":row["expected_revision"],
            "current_revision":current["revision"],
            "result":row.get("result")}


def reject_proposal(root, proposal_id, *, confirmed=False):
    """Local terminal rejection does not modify canonical research state."""
    if not confirmed:
        raise ResearchError("rejection requires explicit terminal confirmation")
    from rn_core import atomic_json
    with workspace_lock(root):
        path, row = _open_proposal(root, proposal_id)
        if row.get("status") != "pending" or row.get("id") != proposal_id:
            raise ResearchError("proposal already processed or tampered")
        if row.get("project_id") != load(root)["project"]["project_id"]:
            raise ResearchError("wrong project")
        row["status"] = "rejected"
        row["rejected_at"] = now()
        atomic_json(path,row)
        return {"proposal_id":proposal_id,"status":"rejected"}
