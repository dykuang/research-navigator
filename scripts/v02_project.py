#!/usr/bin/env python3
"""v0.2 research domain CLI (keep existing update_project.py backward compatible)."""
import argparse
import json
import sys

from rn_core import ResearchError, load
from rn_domain import (accept_milestone, attach_milestone_evidence, claim_evidence,
                       create_branch, create_milestone, create_session, link_evidence,
                       session_entity_link)


def main():
    ap = argparse.ArgumentParser(description="Research Navigator v0.2: scientific routes and provenance")
    sp = ap.add_subparsers(dest="cmd", required=True)

    def cmd(name):
        p = sp.add_parser(name)
        p.add_argument("root", help="research project root, not skill directory")
        return p

    p = cmd("branch-create")
    p.add_argument("--title", required=True)
    p.add_argument("--goal", required=True)
    p.add_argument("--stop-condition", action="append", required=True)
    p.add_argument("--actor", default="agent")
    p.add_argument("--module", default="topic")
    p.add_argument("--next-action", default="")

    p = cmd("milestone-create")
    p.add_argument("--title", required=True)
    p.add_argument("--criterion", action="append", required=True)
    p.add_argument("--actor", default="agent")
    p.add_argument("--module", default="experiment")

    p = cmd("milestone-evidence")
    p.add_argument("--milestone", required=True)
    p.add_argument("--criterion", required=True)
    p.add_argument("--evidence-id", required=True)
    p.add_argument("--reason", default="evidence registered")
    p.add_argument("--actor", default="agent")

    p = cmd("milestone-accept")
    p.add_argument("--milestone", required=True)
    p.add_argument("--approval-note", required=True)
    p.add_argument("--actor", choices=("user", "mentor"), required=True)

    p = cmd("evidence-link")
    p.add_argument("--claim", required=True)
    p.add_argument("--evidence-id", required=True)
    p.add_argument("--stance", required=True, choices=("supports", "contradicts", "qualifies"))
    p.add_argument("--quality", default="unverified",
                   choices=("unverified", "source-checked", "experiment-observed"))
    p.add_argument("--scope", required=True)
    p.add_argument("--locator", default="")
    p.add_argument("--note", default="")
    p.add_argument("--actor", default="agent")

    p = cmd("evidence-show")
    p.add_argument("--claim", required=True)

    p = cmd("session-create")
    p.add_argument("--provider", choices=("codex", "chatgpt", "other"), required=True)
    p.add_argument("--workspace", required=True)
    p.add_argument("--session-id", required=True)
    p.add_argument("--url", default="")
    p.add_argument("--actor", default="user")

    p = cmd("session-link")
    p.add_argument("--session-ref", required=True)
    p.add_argument("--entity-id", required=True)
    p.add_argument("--role", choices=("idea-origin", "discussion", "experiment-analysis",
                                      "decision", "park", "revival", "other"), default="discussion")
    p.add_argument("--actor", default="user")

    p = cmd("session-unlink")
    p.add_argument("--session-ref", required=True)
    p.add_argument("--entity-id", required=True)
    p.add_argument("--actor", default="user")

    p = cmd("session-list")

    a = ap.parse_args()
    try:
        if a.cmd == "branch-create":
            result = create_branch(a.root, a.title, a.goal, a.stop_condition,
                                   a.actor, a.module, a.next_action)
        elif a.cmd == "milestone-create":
            result = create_milestone(a.root, a.title, a.criterion, a.actor, a.module)
        elif a.cmd == "milestone-evidence":
            result = attach_milestone_evidence(a.root, a.milestone, a.criterion,
                                               a.evidence_id, a.actor, a.reason)
        elif a.cmd == "milestone-accept":
            result = accept_milestone(a.root, a.milestone, a.approval_note, a.actor)
        elif a.cmd == "evidence-link":
            result = link_evidence(a.root, a.claim, a.evidence_id, a.stance,
                                   a.scope, a.quality, a.locator, a.note, a.actor)
        elif a.cmd == "evidence-show":
            result = claim_evidence(a.root, a.claim)
        elif a.cmd == "session-create":
            result = create_session(a.root, a.provider, a.workspace, a.session_id,
                                    a.actor, a.url)
        elif a.cmd == "session-link":
            result = session_entity_link(a.root, a.session_ref, a.entity_id,
                                         a.role, a.actor)
        elif a.cmd == "session-unlink":
            result = session_entity_link(a.root, a.session_ref, a.entity_id,
                                         actor=a.actor, remove=True)
        else:
            result = load(a.root)["session_refs"]
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except (ResearchError, OSError, ValueError, KeyError) as e:
        print(f"Research Navigator error: {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
