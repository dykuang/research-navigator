#!/usr/bin/env python3
"""v0.3 research reasoning CLI. No experiment execution or transcript ingestion."""
import argparse
import json
import sys

from rn_core import ResearchError, load, validate_state
from rn_reasoning import (analyze_claim, create_decision_trace, create_run,
                          invalidate_run, record_run, replay_decision)


def json_print(result):
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))


def metric_value(raw):
    # name=value:unit:direction, e.g. F1=0.71:ratio:higher
    try:
        name, right = raw.split("=", 1)
        value, unit, direction = right.split(":", 2)
        result = {"name":name.strip(),"value":float(value),
                  "unit":unit.strip(),"direction":direction.strip()}
        if not all(result[k] for k in ("name","unit","direction")):
            raise ValueError()
        return result
    except ValueError as exc:
        raise argparse.ArgumentTypeError("metric must be name=value:unit:direction") from exc


def main():
    ap=argparse.ArgumentParser(description="Research Navigator v0.3 reasoning CLI")
    sub=ap.add_subparsers(dest="command",required=True)
    def command(name):
        p=sub.add_parser(name)
        p.add_argument("root", help="research project root")
        return p
    def rev(p):
        p.add_argument("--expected-revision",type=int,default=None)

    p=command("run-plan");p.add_argument("--experiment",required=True)
    p.add_argument("--title",required=True);p.add_argument("--attempt",type=int,required=True)
    p.add_argument("--actor",default="agent");rev(p)

    p=command("run-record");p.add_argument("--run",required=True)
    for name in ("dataset","protocol","code-revision","artifact","observation",
                 "outcome","started-at","ended-at"):
        p.add_argument("--"+name,required=True)
    p.add_argument("--seed",type=int,required=True)
    p.add_argument("--metric",action="append",type=metric_value,default=[])
    p.add_argument("--synthetic",action="store_true",help="Explicit test fixture; not a real experiment")
    p.add_argument("--actor",default="agent");rev(p)

    p=command("run-invalidate");p.add_argument("--run",required=True)
    p.add_argument("--reason",required=True);p.add_argument("--actor",default="user");rev(p)

    p=command("run-list");p.add_argument("--experiment")

    p=command("claim-analyze");p.add_argument("--claim",required=True)

    p=command("trace-create")
    p.add_argument("--decision",required=True);p.add_argument("--title",required=True)
    p.add_argument("--scope",required=True);p.add_argument("--option",action="append",required=True)
    p.add_argument("--selected",required=True);p.add_argument("--rationale",required=True)
    p.add_argument("--event-id",action="append",default=[])
    p.add_argument("--session-ref",action="append",default=[])
    p.add_argument("--claim-id",action="append",default=[])
    p.add_argument("--run-id",action="append",default=[])
    p.add_argument("--approval-event-id")
    p.add_argument("--status",default="documented",
                   choices=("documented","incomplete","disputed"))
    p.add_argument("--actor",default="agent");rev(p)

    p=command("trace-replay");p.add_argument("--trace",required=True)

    a=ap.parse_args()
    try:
        if a.command=="run-plan":
            result=create_run(a.root,a.experiment,a.title,a.attempt,
                              actor=a.actor,expected_revision=a.expected_revision)
        elif a.command=="run-record":
            result=record_run(a.root,a.run,dataset=a.dataset,protocol=a.protocol,
                code_revision=a.code_revision,seed=a.seed,artifact_path=a.artifact,
                observation=a.observation,outcome=a.outcome,metrics=a.metric,
                started_at=a.started_at,ended_at=a.ended_at,synthetic=a.synthetic,
                actor=a.actor,expected_revision=a.expected_revision)
        elif a.command=="run-invalidate":
            result=invalidate_run(a.root,a.run,a.reason,actor=a.actor,
                                  expected_revision=a.expected_revision)
        elif a.command=="run-list":
            state=load(a.root);result=[i for i in state["items"]
                if i["type"]=="ExperimentRun" and
                (not a.experiment or i["run"]["experiment_id"]==a.experiment)]
        elif a.command=="claim-analyze":
            result=analyze_claim(a.root,a.claim)
        elif a.command=="trace-create":
            result=create_decision_trace(a.root,decision_id=a.decision,title=a.title,
                scope=a.scope,options=a.option,selected=a.selected,rationale=a.rationale,
                event_ids=a.event_id,session_ref_ids=a.session_ref,
                claim_ids=a.claim_id,run_ids=a.run_id,
                approval_event_id=a.approval_event_id,status=a.status,
                actor=a.actor,expected_revision=a.expected_revision)
        elif a.command=="trace-replay":
            result=replay_decision(a.root,a.trace)
        json_print(result)
    except (ResearchError, OSError, ValueError, KeyError) as e:
        print("Research Navigator v0.3 error: "+str(e),file=sys.stderr)
        sys.exit(2)


if __name__=="__main__":
    main()
