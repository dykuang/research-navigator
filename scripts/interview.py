#!/usr/bin/env python3
"""Research Navigator interview CLI. No implicit activation or scientific writes."""
import argparse
import json
import sys

from rn_core import ResearchError, paths
from rn_interview import (start,read,add_questions,answer,pause,resume,request_exit,
                          reject_exit,confirm_exit,abandon,reopen,frontier,handoff)

def main():
    p=argparse.ArgumentParser(description="Persistent, explicit v0.4.1 research grilling interview")
    p.add_argument("root",help="Existing initialized research project ROOT")
    sub=p.add_subparsers(dest="command",required=True)
    for cmd in ("start","status","add-questions","answer","next","pause","resume",
                "request-exit","reject-exit","confirm-exit","abandon","reopen","handoff"):
        sp=sub.add_parser(cmd)
        if cmd=="start":
            sp.add_argument("--topic",required=True)
            sp.add_argument("--restart",action="store_true",help="Archive a completed/abandoned interview before creating a new one")
        if cmd=="add-questions":
            sp.add_argument("--questions-json",required=True,help="JSON array of 1-5 question objects")
        if cmd=="answer":
            sp.add_argument("--question",required=True)
            sp.add_argument("--text",default="")
            sp.add_argument("--status",choices=("answered","deferred","unresolved"),default="answered")
            sp.add_argument("--revise",action="store_true")
        if cmd=="next":sp.add_argument("--limit",type=int,default=5)
        if cmd in ("request-exit","reject-exit","abandon","reopen"):
            sp.add_argument("--reason",required=True)
        if cmd=="confirm-exit":
            sp.add_argument("--accept-open",action="append",default=[],help="Explicitly acknowledge each unresolved question ID")
        if cmd not in ("status","next","handoff"):
            sp.add_argument("--actor",choices=("agent","user","mentor"),
                            default=("agent" if cmd in ("add-questions","request-exit") else "user"))
            sp.add_argument("--expected-revision",type=int)
    args=p.parse_args()
    try:
        c=args.command
        common={}
        if c not in ("status","next","handoff","start"):
            common={"actor":args.actor,"expected_revision":args.expected_revision}
        if c=="start":data=start(args.root,topic=args.topic,actor=args.actor,restart=args.restart)
        elif c=="status":
            x=read(args.root)
            data={"interview_id":x["interview_id"],"status":x["status"],
                  "revision":x["revision"],"topic":x["topic"],"round":x["round"],
                  "last_seen_project_revision":x["last_seen_project_revision"],
                  "frontier":frontier(x),"consensus_note":x["consensus_note"],
                  "accepted_open_questions":x["accepted_open_questions"]}
        elif c=="add-questions":data=add_questions(args.root,json.loads(args.questions_json),**common)
        elif c=="answer":
            data=answer(args.root,args.question,args.text,status=args.status,revise=args.revise,**common)
        elif c=="next":data=frontier(read(args.root),args.limit)
        elif c=="pause":data=pause(args.root,**common)
        elif c=="resume":data=resume(args.root,**common)
        elif c=="request-exit":data=request_exit(args.root,args.reason,**common)
        elif c=="reject-exit":data=reject_exit(args.root,args.reason,**common)
        elif c=="confirm-exit":data=confirm_exit(args.root,args.accept_open,**common)
        elif c=="abandon":data=abandon(args.root,args.reason,**common)
        elif c=="reopen":data=reopen(args.root,args.reason,**common)
        else:data=handoff(args.root)
        print(json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False))
        return 0
    except (ResearchError,ValueError,OSError,KeyError,TypeError) as exc:
        print("Interview error: "+str(exc),file=sys.stderr)
        return 2

if __name__=="__main__":
    sys.exit(main())
