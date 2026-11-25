#!/usr/bin/env python3
"""Research Navigator interview CLI. No implicit activation or scientific writes."""
import argparse
import json
import sys

from rn_core import ResearchError, paths
from rn_interview_choices import (codex_request,codex_async_request,text_prompt,
                                  resolve_codex_answer,resolve_async_reply,
                                  delivery_plan)
from rn_interview import (start,read,add_questions,answer,pause,resume,request_exit,
                          reject_exit,confirm_exit,abandon,reopen,frontier,handoff)

def main():
    p=argparse.ArgumentParser(description="Persistent, explicit v0.4.1 research grilling interview")
    p.add_argument("root",help="Existing initialized research project ROOT")
    sub=p.add_subparsers(dest="command",required=True)
    for cmd in ("start","status","add-questions","answer","next","present","prompt","native-request","resolve-native","async-request","resolve-async","pause","resume",
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
            sp.add_argument("--choice",help="Stable choice ID or other for free-form response")
            sp.add_argument("--custom-answer",help="Original user text; requires --choice other")
            sp.add_argument("--supplement",help="Optional additional explanation with ANY answer/choice")
        if cmd=="next":sp.add_argument("--limit",type=int,default=5)
        if cmd in ("present","prompt","native-request","resolve-native","async-request","resolve-async"):
            sp.add_argument("--question",required=True)
        if cmd=="present":
            sp.add_argument("--capability",choices=("none","sync","async"),default="none",
                            help="Only set sync/async if the REAL client exposes it")
            sp.add_argument("--failure",choices=("unavailable","error","timeout","cancelled","no-answer"),
                            help="If delivery failed, return normal-chat fallback regardless of capability")
        if cmd=="resolve-async":sp.add_argument("--text",required=True)
        if cmd=="resolve-native":
            sp.add_argument("--response-json",required=True,
                            help="Native request_user_input return JSON, for inspection only")
        if cmd in ("request-exit","reject-exit","abandon","reopen"):
            sp.add_argument("--reason",required=True)
        if cmd=="confirm-exit":
            sp.add_argument("--accept-open",action="append",default=[],help="Explicitly acknowledge each unresolved question ID")
        if cmd not in ("status","next","handoff","present","prompt","native-request",
                       "resolve-native","async-request","resolve-async"):
            sp.add_argument("--actor",choices=("agent","user","mentor"),
                            default=("agent" if cmd in ("add-questions","request-exit") else "user"))
            sp.add_argument("--expected-revision",type=int)
    args=p.parse_args()
    try:
        c=args.command
        common={}
        if c not in ("status","next","handoff","start","present","prompt",
                      "native-request","resolve-native","async-request","resolve-async"):
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
            data=answer(args.root,args.question,args.text,status=args.status,
                        revise=args.revise,choice_id=args.choice,
                        custom_answer=args.custom_answer,
                        supplement=args.supplement,**common)
        elif c=="next":data=frontier(read(args.root),args.limit)
        elif c in ("present","prompt","native-request","resolve-native","async-request","resolve-async"):
            document=read(args.root)
            questions={q["id"]:q for q in document["questions"]}
            selected=questions.get(args.question)
            if selected is None:raise ResearchError("unknown question ID")
            allowed={q["id"] for q in frontier(document)["ready"]}
            if document["status"]!="active" or args.question not in allowed:
                raise ResearchError("question is not available for an active interview")
            if c=="present":
                data=delivery_plan(selected,args.capability,args.failure)
            elif c=="prompt":data={"question_id":selected["id"],"text":text_prompt(selected),
                                  "interactive_ui":False,"writeback":False}
            elif c=="native-request":
                data={"tool_name":"request_user_input",
                      "tool_arguments":codex_request(selected),
                      "must_check_runtime_capability":True,
                      "tool_called":False,
                      "other_is_client_supplied":True,
                      "writeback":False}
            elif c=="async-request":
                data={"tool_name":"request_user_input_async",
                      "tool_arguments":codex_async_request(selected),
                      "must_check_runtime_capability":True,"tool_called":False,
                      "async_ack_is_not_user_answer":True,
                      "writeback":False}
            elif c=="resolve-async":
                data={"resolved":resolve_async_reply(selected,args.text),
                      "requires_explicit_user_confirmation":True,
                      "source":"subsequent-user-message-not-async-tool-ack",
                      "writeback":False}
            else:
                data={"resolved":resolve_codex_answer(selected,json.loads(args.response_json)),
                      "requires_explicit_user_confirmation":True,"writeback":False}
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
