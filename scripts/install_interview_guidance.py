#!/usr/bin/env python3
"""Opt-in project AGENTS.md handoff guidance for persistent interviews.

No automatic installation, no global Agent changes, and no hidden activation.
The caller must explicitly pass --apply. Existing content is retained.
"""
import argparse
from pathlib import Path
import sys

from rn_core import ResearchError, paths, load, workspace_lock, atomic_text

START="<!-- research-navigator-interview-v0.4.1:start -->"
END="<!-- research-navigator-interview-v0.4.1:end -->"
SECTION=START+"""
## Research Navigator ongoing interview (project-local opt-in)

This project may have a saved Research Navigator grilling interview.

When a user explicitly asks to **continue an ongoing research interview** or
resume Research Navigator work in this workspace, read:
\`research/interviews/current.json\` (if present) and the Research Navigator
Skill's \`references/interaction-protocol.md\`.

Use \`python /PATH/TO/research-navigator/scripts/interview.py PROJECT_ROOT status\`
and \`next\` to recover only the confirmed and unresolved interview context,
then continue the current highest-value question frontier. The Skill root path
must be resolved in the user's environment; never assume the placeholder path
is executable. Explicitly activate the installed \`research-navigator\` Skill using the live harness's supported mechanism.

An independent Codex or DeepSeek DSH chat does **not** automatically inherit the previous
chat's Skill invocation. Explain this honestly. If the Skill is unavailable,
ask the user to invoke/install it rather than claiming it ran.

Do not initialize a duplicate project, do not silently answer or confirm
questions, and do not promote interview answers to scientific evidence.
Never exit the grilling workflow without a user/mentor confirmation.
When the interview is \`completed\` or \`abandoned\`, continue normal work and
do not re-enter grilling unless the user explicitly asks.

This project instruction is not a global always-on Skill invocation and must
not interfere with unrelated work in the workspace.
"""+END+"\n"

def install(root,apply=False):
    project=paths(root)["root"]
    load(root)  # require initialized project
    dest=project/"AGENTS.md"
    if not apply:
        return {"applied":False,"target":str(dest),
                "message":"Preview only. Explicitly re-run with --apply to opt in.",
                "section":SECTION}
    with workspace_lock(root):
        load(root)
        old=dest.read_text(encoding="utf-8") if dest.exists() else ""
        if (START in old) != (END in old):
            raise ResearchError("Partial Research Navigator markers: please inspect manually")
        if START in old:
            raise ResearchError("Research Navigator AGENTS.md guidance already installed; not overwriting")
        if len(old)>2_000_000:
            raise ResearchError("AGENTS.md too large for safe append")
        text=old.rstrip()+"\n\n"+SECTION if old.strip() else SECTION
        atomic_text(dest,text)
    return {"applied":True,"target":str(dest),
            "message":"Project-scoped guidance installed; no global Skill activation guaranteed."}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("root")
    p.add_argument("--apply",action="store_true",help="Explicitly opt into editing the project AGENTS.md")
    a=p.parse_args()
    try:
        import json
        print(json.dumps(install(a.root,a.apply),ensure_ascii=False,indent=2))
    except (ResearchError,OSError) as exc:
        p.error(str(exc))
if __name__=="__main__":
    main()
