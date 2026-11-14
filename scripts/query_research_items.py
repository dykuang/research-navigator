#!/usr/bin/env python3
"""Audited query modes. Historical items never leak into positive planning candidates."""
import argparse, json, sys
from rn_core import load, query, ResearchError

def dispatch(root,mode,user_authorized=False):
    return query(load(root),mode,user_authorized)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("root");p.add_argument("--mode",required=True,choices=("planning","recommendation","task-generation","risk-check","novelty-check","failure-avoidance","archive-exploration","creative-recombination","revival-review","synthesis"))
    p.add_argument("--user-authorized",action="store_true",help="Explicit user request to explore historical ideas (not execution approval)")
    a=p.parse_args()
    try: print(json.dumps(dispatch(a.root,a.mode,a.user_authorized),indent=2,ensure_ascii=False))
    except ResearchError as e:print(str(e),file=sys.stderr);sys.exit(2)
if __name__=="__main__":main()
