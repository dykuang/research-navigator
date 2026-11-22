"""Typed research branch, scientific milestone, evidence, and Agent SessionRef APIs.

This is an additive v0.2 API: existing v0.1 records are never auto-reinterpreted.
Mutations take the shared workspace lock and pass canonical validation + event audit.
"""
from __future__ import annotations

import copy
from urllib.parse import urlsplit

from rn_core import (ACTORS, ResearchError, item_by_id, load, new_item, now,
                     propagate, require, validate_state, workspace_lock, write)
from rn_v02 import EVIDENCE_QUALITIES, SESSION_PROVIDERS, SESSION_ROLES, STANCES


def _id(existing, prefix):
    taken = {x["id"] for x in existing}
    number = 1
    while f"{prefix}-{number:04d}" in taken:
        number += 1
    return f"{prefix}-{number:04d}"


def _event(action, ident, actor, reason, after, before=None):
    record = {"action": action, "item_id": ident, "actor": actor,
              "reason": reason, "after": copy.deepcopy(after)}
    if before is not None:
        record["before"] = copy.deepcopy(before)
    return record


def create_branch(root, title, goal, stop_conditions, actor="agent",
                  module="topic", next_action=""):
    require(actor, ACTORS, "actor")
    if not goal.strip() or not stop_conditions or any(not x.strip() for x in stop_conditions):
        raise ResearchError("ResearchBranch needs a goal and explicit stop conditions")
    with workspace_lock(root):
        state = load(root)
        branch = new_item(state, "ResearchBranch", title, module, actor=actor,
                          next_action=next_action)
        branch["branch"] = {"goal": goal, "stop_conditions": list(stop_conditions),
                            "created_at": now()}
        write(root, state, [_event("branch-created", branch["id"], actor, "new research route", branch)])
        return branch


def create_milestone(root, title, criteria, actor="agent", module="experiment"):
    require(actor, ACTORS, "actor")
    if not criteria or any(not t.strip() for t in criteria):
        raise ResearchError("Milestone needs measurable scientific acceptance criteria")
    with workspace_lock(root):
        state = load(root)
        item = new_item(state, "Milestone", title, module, actor=actor)
        item["milestone"] = {
            "criteria": [{"id": f"C-{n+1:03d}", "text": t,
                          "evidence_refs": [], "reviewed": False}
                         for n, t in enumerate(criteria)],
            "accepted": False, "approval_note": "",
        }
        write(root, state, [_event("milestone-created", item["id"], actor,
                                  "scientific criteria registered", item)])
        return item


def attach_milestone_evidence(root, milestone_id, criterion_id, evidence_id,
                              actor="agent", reason="evidence attached"):
    require(actor, ACTORS, "actor")
    with workspace_lock(root):
        s = load(root)
        milestone = item_by_id(s, milestone_id)
        item_by_id(s, evidence_id) if not any(x["id"] == evidence_id for x in s["sources"]) else None
        if milestone["type"] != "Milestone":
            raise ResearchError("target must be Milestone")
        criterion = next((x for x in milestone["milestone"]["criteria"]
                          if x["id"] == criterion_id), None)
        if criterion is None:
            raise ResearchError("unknown milestone acceptance criterion")
        if evidence_id in criterion["evidence_refs"]:
            raise ResearchError("duplicate milestone evidence")
        criterion["evidence_refs"].append(evidence_id)
        milestone["impact_status"] = "needs-review"
        milestone["revision"] += 1
        milestone["updated_at"] = now()
        write(root, s, [_event("milestone-evidence-attached", milestone_id, actor,
                              reason, {"criterion": criterion_id, "evidence_id": evidence_id})])
        return milestone


def accept_milestone(root, milestone_id, approval_note, actor="user"):
    """Do not infer scientific validation; require actual human authorization by caller."""
    if actor not in ("user", "mentor") or not approval_note.strip():
        raise ResearchError("Scientific Milestone acceptance requires explicit user/mentor approval")
    with workspace_lock(root):
        s = load(root)
        item = item_by_id(s, milestone_id)
        if item["type"] != "Milestone":
            raise ResearchError("not a Milestone")
        if item["lifecycle_status"] != "active" or item["impact_status"] in ("stale", "blocked"):
            raise ResearchError("archived or blocked Milestone cannot be accepted")
        if item["milestone"]["accepted"]:
            raise ResearchError("Milestone is already accepted")
        if any(not c["evidence_refs"] for c in item["milestone"]["criteria"]):
            raise ResearchError("each scientific criterion needs linked evidence before acceptance")
        # Evidence IDs may still be uncertain: consent does not strengthen epistemic status.
        item["milestone"]["accepted"] = True
        item["milestone"]["approval_note"] = approval_note
        item["review_status"] = "user-confirmed"
        item["workflow_status"] = "done"
        item["acceptance_criteria"] = "; ".join(c["text"] for c in item["milestone"]["criteria"])
        item["completion_note"] = "Human accepted the milestone with linked evidence; not scientific proof"
        item["impact_status"] = "current"
        item["revision"] += 1
        item["updated_at"] = now()
        write(root, s, [_event("milestone-accepted", milestone_id, actor,
                              approval_note, {"linked_criteria": item["milestone"]["criteria"]})])
        return item


def link_evidence(root, claim_id, evidence_id, stance, scope, quality="unverified",
                  locator="", note="", actor="agent"):
    require(actor, ACTORS, "actor")
    require(stance, STANCES, "stance")
    require(quality, EVIDENCE_QUALITIES, "quality")
    if not scope.strip():
        raise ResearchError("evidence requires applicability scope")
    with workspace_lock(root):
        s = load(root)
        claim = item_by_id(s, claim_id)
        if claim["type"] != "Claim":
            raise ResearchError("evidence link target must be a Claim")
        evidence = next((x for x in s["sources"] if x["id"] == evidence_id), None)
        if evidence is None:
            evidence = item_by_id(s, evidence_id)
        if quality == "source-checked" and (evidence_id not in
                {x["id"] for x in s["sources"] if x.get("verification_status") == "primary-inspected"}):
            raise ResearchError("source-checked requires inspected original source")
        if quality == "experiment-observed" and (
                evidence.get("type") != "Result" or not evidence.get("observation")
                or not evidence.get("artifact_path")):
            raise ResearchError("experiment-observed requires a Result observation and artifact")
        if any(x["claim_id"] == claim_id and x["evidence_id"] == evidence_id and
               x["stance"] == stance and x["scope"] == scope for x in s["evidence_links"]):
            raise ResearchError("duplicate evidence link")
        link = {"id": _id(s["evidence_links"], "EVL"), "claim_id": claim_id,
                "evidence_id": evidence_id, "stance": stance, "quality": quality,
                "scope": scope, "locator": locator, "note": note, "created_at": now(),
                "recorded_by": actor}
        s["evidence_links"].append(link)
        events = [_event("evidence-linked", link["id"], actor,
                         "scoped claim-evidence relationship", link)]
        if stance == "contradicts":
            prev = claim["impact_status"]
            claim["impact_status"] = "needs-review"
            claim["revision"] += 1
            claim["updated_at"] = now()
            events.append(_event("impact-propagated", claim_id, actor,
                                 "contradictory evidence", {"impact_status": "needs-review"},
                                 {"impact_status": prev}))
            events.extend(propagate(s, claim_id, actor, "contradictory evidence"))
        write(root, s, events)
        return link


def claim_evidence(root, claim_id):
    s = load(root)
    claim = item_by_id(s, claim_id)
    if claim["type"] != "Claim":
        raise ResearchError("not a Claim")
    refs = {x["id"]: x for x in s["items"] + s["sources"]}
    return {"claim_id": claim_id, "epistemic_status": claim["epistemic_status"],
            "impact_status": claim["impact_status"], "links": [
                {"link": x, "evidence": refs[x["evidence_id"]]}
                for x in s["evidence_links"] if x["claim_id"] == claim_id]}


def _validate_url(url):
    if not url:
        return
    parts = urlsplit(url)
    if parts.scheme != "https" or not parts.hostname or parts.username or parts.password or parts.query or parts.fragment:
        raise ResearchError("Session URL must be a clean HTTPS URL; unverified links are never opened automatically")


def create_session(root, provider, workspace_id, session_id, actor="user", url=""):
    require(provider, SESSION_PROVIDERS, "provider")
    require(actor, ACTORS, "actor")
    if not workspace_id.strip() or not session_id.strip():
        raise ResearchError("workspace ID and session ID are required")
    _validate_url(url)
    with workspace_lock(root):
        s = load(root)
        if any(x["provider"] == provider and x["workspace_id"] == workspace_id and
               x["session_id"] == session_id for x in s["session_refs"]):
            raise ResearchError("SessionRef already exists")
        row = {"id": _id(s["session_refs"], "SESS"), "provider": provider,
               "workspace_id": workspace_id, "session_id": session_id,
               "url": url, "url_verified": False, "entity_ids": [], "roles": {},
               "recorded_by": actor, "recorded_at": now()}
        s["session_refs"].append(row)
        write(root, s, [_event("session-registered", row["id"], actor,
                              "external session reference; no chat content copied", row)])
        return row


def session_entity_link(root, session_ref_id, entity_id, role="discussion",
                        actor="user", remove=False):
    require(role, SESSION_ROLES, "role")
    require(actor, ACTORS, "actor")
    with workspace_lock(root):
        s = load(root)
        item_by_id(s, entity_id)
        record = next((x for x in s["session_refs"] if x["id"] == session_ref_id), None)
        if record is None:
            raise ResearchError("SessionRef not found")
        if remove:
            if entity_id not in record["entity_ids"]:
                raise ResearchError("link does not exist")
            record["entity_ids"].remove(entity_id)
            record["roles"].pop(entity_id)
        else:
            if entity_id in record["entity_ids"]:
                raise ResearchError("duplicate session/entity link")
            record["entity_ids"].append(entity_id)
            record["roles"][entity_id] = role
        action = "session-entity-unlinked" if remove else "session-entity-linked"
        write(root, s, [_event(action, session_ref_id, actor, "explicit research/session association",
                              {"entity_id": entity_id, "role": role})])
        return record
