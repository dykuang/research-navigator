#!/usr/bin/env python3
"""Research Navigator v0.4 decision reports; does not change canonical state."""
import argparse
import json
import sys
from pathlib import Path

from rn_core import ResearchError
from rn_decision import summarize, markdown_brief

def main():
    p = argparse.ArgumentParser(description="Read-only v0.4 research decision assistant")
    p.add_argument("root", help="Research project root")
    p.add_argument("command", choices=("gaps", "opportunities", "archive", "brief"))
    p.add_argument("--format", choices=("json", "markdown"), default="json")
    p.add_argument("--output", help="Optional report path; reports are derived, never canonical state")
    a = p.parse_args()
    try:
        data = summarize(a.root, a.command)
        if a.format == "markdown":
            if a.command != "brief":
                raise ResearchError("Markdown supported for brief only")
            output = markdown_brief(data)
        else:
            output = json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False)+"\n"
        if a.output:
            target = Path(a.output).expanduser().resolve()
            if target.is_dir():
                raise ResearchError("output must be file path")
            # Refuse all paths within canonical project state.
            state = (Path(a.root).expanduser().resolve()/"research"/"state")
            if target == state or state in target.parents:
                raise ResearchError("cannot place derived reports inside canonical state directory")
            target.parent.mkdir(parents=True, exist_ok=True)
            from rn_core import atomic_text
            atomic_text(target, output)
            print(json.dumps({"report":str(target), "read_only_projection":True}, ensure_ascii=False))
        else:
            print(output,end="")
    except (ResearchError, ValueError, OSError, KeyError) as e:
        print("Research decision error: "+str(e),file=sys.stderr)
        return 2
    return 0

if __name__=="__main__":
    sys.exit(main())
