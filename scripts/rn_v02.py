"""v0.2 add-on schema validation; legacy v0.1 projects remain readable."""
from __future__ import annotations
from urllib.parse import urlsplit

VERSION = "0.2.0"
LEGACY = "0.1.0"
STANCES = ("supports", "contradicts", "qualifies")
EVIDENCE_QUALITIES = ("unverified", "source-checked", "experiment-observed")
SESSION_PROVIDERS = ("codex", "chatgpt", "other")
SESSION_ROLES = ("idea-origin", "discussion", "experiment-analysis", "decision", "park", "revival", "other")


def validate_v02(state):
    """Return human-readable schema problems, never change the supplied state."""
    errors = []
    items = {x.get("id"): x for x in state.get("items", [])}
    sources = {x.get("id"): x for x in state.get("sources", [])}
    valid = set(items) | set(sources)
    for item in state.get("items", []):
        ident = item.get("id", "<unknown>")
        kind = item.get("type")
        if kind == "ResearchBranch":
            meta = item.get("branch")
            if not isinstance(meta, dict) or not isinstance(meta.get("goal"), str) or not meta["goal"].strip():
                errors.append(f"{ident}: ResearchBranch must define a goal")
            elif not isinstance(meta.get("stop_conditions"), list) or not meta["stop_conditions"]:
                errors.append(f"{ident}: ResearchBranch needs explicit stop conditions")
        if kind == "Milestone":
            meta = item.get("milestone")
            criteria = meta.get("criteria") if isinstance(meta, dict) else None
            if not isinstance(criteria, list) or not criteria:
                errors.append(f"{ident}: Milestone requires scientific acceptance criteria")
            else:
                ids = [c.get("id") for c in criteria if isinstance(c, dict)]
                if len(ids) != len(criteria) or len(set(ids)) != len(ids) or any(not x for x in ids):
                    errors.append(f"{ident}: invalid/duplicate milestone criterion id")
                for c in criteria:
                    if not isinstance(c, dict):
                        continue
                    if not isinstance(c.get("text"), str) or not c["text"].strip():
                        errors.append(f"{ident}: blank milestone criterion")
                    refs = c.get("evidence_refs", [])
                    if not isinstance(refs, list) or any(x not in valid for x in refs):
                        errors.append(f"{ident}: unresolved criterion evidence ref")
            if isinstance(meta, dict) and meta.get("accepted"):
                if item.get("review_status") != "user-confirmed" or not meta.get("approval_note"):
                    errors.append(f"{ident}: scientific Milestone acceptance requires human confirmation")
    for r in state.get("relations", []):
        if r.get("type") == "member-of":
            target = items.get(r.get("to"))
            if not target or target.get("type") != "ResearchBranch":
                errors.append(f"member-of must target ResearchBranch: {r}")
        if r.get("type") == "contributes-to":
            target = items.get(r.get("to"))
            if not target or target.get("type") != "Milestone":
                errors.append(f"contributes-to must target Milestone: {r}")

    links = state.get("evidence_links", [])
    if not isinstance(links, list):
        errors.append("evidence_links must be list")
        links = []
    ids = set()
    for link in links:
        if not isinstance(link, dict):
            errors.append("malformed evidence link")
            continue
        lid = link.get("id")
        if not lid or lid in ids:
            errors.append(f"duplicate/missing evidence link ID: {lid}")
        ids.add(lid)
        claim = items.get(link.get("claim_id"))
        if not claim or claim.get("type") != "Claim":
            errors.append(f"{lid}: evidence links must target a Claim")
        ev_id = link.get("evidence_id")
        if ev_id not in valid:
            errors.append(f"{lid}: dangling evidence reference")
        if link.get("stance") not in STANCES:
            errors.append(f"{lid}: invalid stance")
        if link.get("quality") not in EVIDENCE_QUALITIES:
            errors.append(f"{lid}: invalid evidence quality")
        if not isinstance(link.get("scope"), str) or not link["scope"].strip():
            errors.append(f"{lid}: missing applicability scope")
        if link.get("quality") == "source-checked":
            src = sources.get(ev_id)
            if not src or src.get("verification_status") != "primary-inspected":
                errors.append(f"{lid}: source-checked evidence needs inspected primary source")
        if link.get("quality") == "experiment-observed":
            res = items.get(ev_id)
            if not res or res.get("type") != "Result" or not res.get("observation") or not res.get("artifact_path"):
                errors.append(f"{lid}: experiment-observed evidence needs Result observation/artifact")

    sessions = state.get("session_refs", [])
    if not isinstance(sessions, list):
        errors.append("session_refs must be list")
        sessions = []
    seen, external = set(), set()
    for session in sessions:
        if not isinstance(session, dict):
            errors.append("malformed session ref")
            continue
        sid = session.get("id")
        if not sid or sid in seen:
            errors.append(f"duplicate/missing SessionRef ID: {sid}")
        seen.add(sid)
        key = (session.get("provider"), session.get("workspace_id"), session.get("session_id"))
        if key in external:
            errors.append(f"duplicate external session: {key}")
        external.add(key)
        if session.get("provider") not in SESSION_PROVIDERS or not session.get("workspace_id") or not session.get("session_id"):
            errors.append(f"{sid}: invalid provider/workspace/session identifier")
        url = session.get("url", "")
        if url:
            parts = urlsplit(url)
            if parts.scheme != "https" or not parts.hostname or parts.username or parts.password or parts.query or parts.fragment:
                errors.append(f"{sid}: session URL must be a clean HTTPS URL without credentials/query/fragment")
        entity_ids = session.get("entity_ids", [])
        if not isinstance(entity_ids, list) or len(set(entity_ids)) != len(entity_ids) or any(x not in items for x in entity_ids):
            errors.append(f"{sid}: invalid linked research IDs")
        roles = session.get("roles", {})
        if not isinstance(roles, dict) or set(roles) != set(entity_ids):
            errors.append(f"{sid}: roles must map exactly to linked research IDs")
        elif any(role not in SESSION_ROLES for role in roles.values()):
            errors.append(f"{sid}: invalid session relation role")
        if session.get("url_verified") is True:
            # v0.2 does not ship a provider-verification adapter: never claim automatic URL verification.
            errors.append(f"{sid}: provider-verified URL not supported in v0.2")
    return errors
