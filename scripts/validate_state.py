#!/usr/bin/env python3
import argparse, json, sys
from rn_core import load, validate_state, project_summary, ResearchError

def main():
    ap=argparse.ArgumentParser();ap.add_argument("root");a=ap.parse_args()
    try:
        s=load(a.root);errors=validate_state(s)
        print(json.dumps({"valid":not errors,"errors":errors,"counts":{"items":len(s["items"]),"relations":len(s["relations"]),"sources":len(s["sources"]),"events":len(s["events"])}},ensure_ascii=False,indent=2))
        sys.exit(1 if errors else 0)
    except (ResearchError,OSError,ValueError,KeyError) as e: print(str(e),file=sys.stderr);sys.exit(2)
if __name__=="__main__":main()
