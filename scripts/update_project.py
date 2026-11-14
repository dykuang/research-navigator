#!/usr/bin/env python3
"""Mutate Research Navigator project state with explicit, auditable operations.

Examples:
 python scripts/update_project.py init /path/to/project --name "研究项目"
 python scripts/update_project.py add-item /path/to/project --type Idea --title "候选方案 A" --module topic
 python scripts/update_project.py set-status /path/to/project IDEA-0001 --field lifecycle_status --value parked --actor user --reason "初步评估表现一般" --failure-scope "small synthetic test" --revival-triggers "new representative data"
"""
import argparse, json, sys
from pathlib import Path
from rn_core import (MODULES, TYPES, WORKFLOW, EPISTEMIC, REVIEW, OUTCOME, LIFECYCLE, IMPACT, RELATIONS, ARCHIVED, ACTORS, ResearchError, init_project, add_item, add_source, add_relation, change_status, revive, set_project, project_summary)
from build_dashboard import build as build_dashboard
from query_research_items import dispatch as query_dispatch

def common(p):
    p.add_argument("root", help="科研项目根目录，与 Skill 安装目录不同")

def cmd():
    ap=argparse.ArgumentParser(description="Research Navigator project CLI, offline stdlib-only")
    ap.add_argument("--no-dashboard", action="store_true",help="本次不重建工作台")
    sub=ap.add_subparsers(dest="action",required=True)
    p=sub.add_parser("init");common(p);p.add_argument("--name",required=True);p.add_argument("--question",default="")
    p=sub.add_parser("add-item");common(p)
    p.add_argument("--type",required=True,choices=TYPES);p.add_argument("--title",required=True);p.add_argument("--module",required=True,choices=MODULES);p.add_argument("--description",default="")
    p.add_argument("--actor",choices=ACTORS,default="agent");p.add_argument("--workflow",choices=WORKFLOW,default="to-be-determined");p.add_argument("--epistemic",choices=EPISTEMIC);p.add_argument("--review",choices=REVIEW);p.add_argument("--outcome",choices=OUTCOME,default="unknown");p.add_argument("--evidence-ref",action="append",default=[])
    p.add_argument("--acceptance-criteria",default="");p.add_argument("--next-action",default="");p.add_argument("--owner",default="");p.add_argument("--observation",default="");p.add_argument("--artifact-path",default="");p.add_argument("--completion-note",default="")
    p=sub.add_parser("add-source");common(p)
    for f in ("title","url","doi","authors","year","verification-note","locator","summary"):p.add_argument("--"+f,required=(f=="title"),default="")
    p.add_argument("--access-level",choices=("full-text","abstract","secondary","user-provided","unavailable"),default="unavailable")
    p.add_argument("--verification-status",choices=("unverified","metadata-checked","primary-inspected"),default="unverified");p.add_argument("--actor",choices=ACTORS,default="agent")
    p=sub.add_parser("link");common(p);p.add_argument("source");p.add_argument("target");p.add_argument("--relation",required=True,choices=RELATIONS);p.add_argument("--actor",default="agent",choices=ACTORS);p.add_argument("--reason",default="")
    p=sub.add_parser("set-status");common(p);p.add_argument("id");p.add_argument("--field",required=True,choices=("workflow_status","epistemic_status","review_status","outcome","lifecycle_status","impact_status"));p.add_argument("--value",required=True);p.add_argument("--reason",required=True);p.add_argument("--actor",default="agent",choices=ACTORS)
    p.add_argument("--evidence-ref",action="append",default=[]);p.add_argument("--completion-note",default="");p.add_argument("--failure-category",default="unknown");p.add_argument("--failure-scope",default="");p.add_argument("--confidence",default="uncertain");p.add_argument("--revival-triggers",default="");p.add_argument("--lesson",default="");p.add_argument("--cost",default="");p.add_argument("--revival-question",default="");p.add_argument("--new-conditions",default="")
    p=sub.add_parser("revive");common(p);p.add_argument("id");p.add_argument("--title",required=True);p.add_argument("--reason",required=True);p.add_argument("--approval-note",required=True);p.add_argument("--new-conditions",required=True);p.add_argument("--actor",choices=("user","mentor"),required=True)
    p=sub.add_parser("set-project");common(p);p.add_argument("--focus-module",choices=MODULES);p.add_argument("--research-question");p.add_argument("--next-decision");p.add_argument("--actor",default="user",choices=ACTORS);p.add_argument("--reason",default="")
    p=sub.add_parser("summary");common(p)
    p=sub.add_parser("dashboard");common(p)
    args=ap.parse_args()
    root=Path(args.root).resolve()
    try:
        if args.action=="init":result=init_project(root,args.name,args.question)
        elif args.action=="add-item":result=add_item(root,kind=args.type,title=args.title,module=args.module,description=args.description,actor=args.actor,workflow=args.workflow,epistemic=args.epistemic,review=args.review,outcome=args.outcome,evidence_refs=args.evidence_ref,acceptance_criteria=args.acceptance_criteria,next_action=args.next_action,owner=args.owner,observation=args.observation,artifact_path=args.artifact_path,completion_note=args.completion_note)
        elif args.action=="add-source":result=add_source(root,title=args.title,url=args.url,doi=args.doi,authors=args.authors,year=args.year,access_level=args.access_level,verification_status=args.verification_status,verification_note=args.verification_note,locator=args.locator,summary=args.summary,actor=args.actor)
        elif args.action=="link":result=add_relation(root,args.source,args.target,args.relation,args.actor,args.reason)
        elif args.action=="set-status":result=change_status(root,args.id,args.field,args.value,args.reason,args.actor,evidence_refs=args.evidence_ref,completion_note=args.completion_note,failure_category=args.failure_category,failure_scope=args.failure_scope,confidence=args.confidence,revival_triggers=args.revival_triggers,lesson=args.lesson,cost=args.cost,revival_question=args.revival_question,new_conditions=args.new_conditions)[0]
        elif args.action=="revive":result=revive(root,args.id,args.title,args.reason,args.approval_note,args.new_conditions,args.actor)
        elif args.action=="set-project":result=set_project(root,args.focus_module,args.research_question,args.next_decision,args.actor,args.reason)
        elif args.action=="summary":result=project_summary(root)
        elif args.action=="dashboard":result={"dashboard":str(build_dashboard(root))}
        if args.action not in ("summary","dashboard") and not args.no_dashboard:
            result={"result":result,"dashboard":str(build_dashboard(root))}
        print(json.dumps(result,ensure_ascii=False,indent=2))
    except (ResearchError,ValueError,FileNotFoundError,KeyError) as e:
        print("Research Navigator error: "+str(e),file=sys.stderr)
        sys.exit(2)
if __name__=="__main__":cmd()
