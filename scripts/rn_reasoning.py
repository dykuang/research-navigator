"""v0.3 scientific reasoning extensions on the existing canonical item/event store.

No background experiments, transcript ingestion, or inferred scientific approval.
All writes run under the v0.2 workspace lock/journal and validate the full state.
"""
from __future__ import annotations

import copy
import hashlib
from pathlib import Path

from rn_core import (ACTORS, OUTCOME, ResearchError, item_by_id, load, new_item,
                     now, propagate, require, workspace_lock, write)
from rn_v03 import RUN_STATES, TRACE_STATES, METRIC_DIRECTIONS


def _event(action, item_id, actor, reason, after, before=None):
    return {"action": action, "item_id": item_id, "actor": actor,
            "reason": reason, "before": before, "after": copy.deepcopy(after)}


def _artifact(root, local_path):
    path = Path(local_path)
    if path.is_absolute() or not local_path or any(part == ".." for part in path.parts):
        raise ResearchError("artifact must be a relative path inside the research project")
    base = Path(root).expanduser().resolve()
    try:
        file = (base / path).resolve(strict=True)
    except FileNotFoundError as e:
        raise ResearchError("artifact not found; cannot claim a recorded experiment") from e
    if not file.is_relative_to(base) or not file.is_file():
        raise ResearchError("artifact must be a regular file inside project root")
    digest = hashlib.sha256()
    with file.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return path.as_posix(), digest.hexdigest()


def _unique_attempt(state, exp_id, attempt, exclude=None):
    if any(i["type"] == "ExperimentRun" and i["id"] != exclude
           and i.get("run", {}).get("experiment_id") == exp_id
           and i.get("run", {}).get("attempt") == attempt
           for i in state["items"]):
        raise ResearchError("duplicate experiment run attempt")


def create_run(root, experiment_id, title, attempt, actor="agent", *, expected_revision=None):
    require(actor, ACTORS, "actor")
    if not isinstance(attempt, int) or isinstance(attempt, bool) or attempt < 1:
        raise ResearchError("attempt must be positive integer")
    with workspace_lock(root):
        state = load(root)
        experiment = item_by_id(state, experiment_id)
        if experiment["type"] != "Experiment":
            raise ResearchError("run must belong to an Experiment")
        if experiment["lifecycle_status"] != "active" or experiment["impact_status"] != "current":
            raise ResearchError("cannot plan an unreviewed or archived Experiment")
        _unique_attempt(state, experiment_id, attempt)
        item = new_item(state, "ExperimentRun", title, "experiment",
                        actor=actor, epistemic="uncertain",
                        review="needs-user-confirmation",
                        next_action="Record actual artifact or invalidate the attempt")
        item["run"] = {"experiment_id": experiment_id, "attempt": attempt,
                       "status": "planned", "dataset": "", "protocol": "",
                       "code_revision": "", "seed": None, "artifact_path": "",
                       "artifact_sha256": "", "artifact_verified": False,
                       "synthetic": False, "metrics": [], "result_id": None,
                       "started_at": "", "ended_at": "", "invalidation_reason": ""}
        state["relations"].append({"from": item["id"], "to": experiment_id, "type": "depends-on"})
        item["depends_on"].append(experiment_id)
        write(root, state, [_event("experiment-run-planned", item["id"], actor,
                                   "Registered only; no execution asserted", item["run"])],
              expected_revision=expected_revision)
        return item


def record_run(root, run_id, *, dataset, protocol, code_revision, seed,
               artifact_path, observation, outcome, metrics, started_at, ended_at,
               synthetic=False, actor="agent", expected_revision=None):
    require(actor, ACTORS, "actor")
    require(outcome, OUTCOME, "outcome")
    if outcome == "unknown":
        raise ResearchError("recorded run needs an actual outcome or inconclusive status")
    for field, value in (("dataset",dataset), ("protocol",protocol),
                         ("code_revision",code_revision),("observation",observation),
                         ("started_at",started_at), ("ended_at",ended_at)):
        if not isinstance(value, str) or not value.strip():
            raise ResearchError(field + " must be provided; no inferred execution")
    if not isinstance(seed, int) or isinstance(seed,bool):
        raise ResearchError("seed must be integer")
    if not isinstance(synthetic, bool):
        raise ResearchError("synthetic flag must be explicit boolean")
    if not isinstance(metrics, list):
        raise ResearchError("metrics must be list of explicit measured values")
    names=set()
    for m in metrics:
        if not isinstance(m,dict) or not isinstance(m.get("name"),str) or not m["name"].strip() or m["name"] in names:
            raise ResearchError("invalid/duplicate metric name")
        names.add(m["name"])
        if m.get("direction") not in METRIC_DIRECTIONS or not isinstance(m.get("unit"),str):
            raise ResearchError("metric must declare unit/direction")
        if isinstance(m.get("value"),bool) or not isinstance(m.get("value"),(int,float)):
            raise ResearchError("metric value must be numeric")
    local_artifact, digest = _artifact(root, artifact_path)
    with workspace_lock(root):
        state = load(root)
        item = item_by_id(state, run_id)
        if item["type"]!="ExperimentRun" or item["run"]["status"]!="planned":
            raise ResearchError("run must exist and be planned; recorded attempts are immutable")
        experiment = item_by_id(state, item["run"]["experiment_id"])
        if experiment["lifecycle_status"]!="active":
            raise ResearchError("cannot record work under archived experiment without review")
        result = new_item(state, "Result",
                          "Observed result for " + run_id, "experiment",
                          actor=actor, workflow="done", outcome=outcome,
                          observation=("SYNTHETIC FIXTURE: " if synthetic else "") + observation,
                          artifact_path=local_artifact, epistemic="uncertain",
                          acceptance_criteria="Record actual observation and inspect source artifact",
                          completion_note=("Synthetic fixture; no real study" if synthetic else
                                           "Observed data recorded; scientific interpretation pending"))
        row = item["run"]
        old = copy.deepcopy(row)
        row.update({"status":"recorded", "dataset":dataset, "protocol":protocol,
                    "code_revision":code_revision, "seed":seed,
                    "artifact_path":local_artifact, "artifact_sha256":digest,
                    "artifact_verified":True, "synthetic":synthetic,
                    "metrics":copy.deepcopy(metrics), "result_id":result["id"],
                    "started_at":started_at, "ended_at":ended_at})
        item["workflow_status"]="done"
        item["acceptance_criteria"]="File checksum recorded and Result linked"
        item["completion_note"]="Run record complete; scientific review is separate"
        item["outcome"]=outcome
        item["revision"]+=1;item["updated_at"]=now()
        state["relations"].append({"from":result["id"],"to":run_id,"type":"depends-on"})
        result["depends_on"].append(run_id)
        write(root,state,[
            _event("result-observed",result["id"],actor,
                   "Recorded observation; requires scientific review",{"outcome":outcome,"run_id":run_id,"artifact_sha256":digest,"synthetic":synthetic}),
            _event("experiment-run-recorded",run_id,actor,
                   "Artifact inspected by local CLI; no scientific validity implied",row,old)
        ],expected_revision=expected_revision)
        return {"run":item,"result":result}


def invalidate_run(root, run_id, reason, actor="user", *, expected_revision=None):
    require(actor, ACTORS, "actor")
    if not reason.strip():
        raise ResearchError("invalidation requires diagnosis")
    with workspace_lock(root):
        state=load(root)
        item=item_by_id(state,run_id)
        if item["type"]!="ExperimentRun" or item["run"]["status"]!="recorded":
            raise ResearchError("only recorded runs can be invalidated")
        row=item["run"];old=copy.deepcopy(row)
        row["status"]="invalidated";row["invalidation_reason"]=reason
        item["impact_status"]="blocked"
        item["revision"]+=1;item["updated_at"]=now()
        result=item_by_id(state,row["result_id"])
        result_old=result["impact_status"]
        result["impact_status"]="blocked";result["revision"]+=1;result["updated_at"]=now()
        events=[_event("experiment-run-invalidated",run_id,actor,reason,row,old),
                _event("impact-propagated",result["id"],actor,reason,
                       {"impact_status":"blocked"},{"impact_status":result_old})]
        events+=propagate(state,result["id"],actor,reason,block=True)
        write(root,state,events,expected_revision=expected_revision)
        return {"run":item,"result":result,"affected":[e["item_id"] for e in events if e["action"]=="impact-propagated"]}


def create_decision_trace(root, *, decision_id, title, scope, options, selected,
                          rationale, event_ids=None, session_ref_ids=None,
                          claim_ids=None, run_ids=None, approval_event_id=None,
                          status="documented", actor="agent", expected_revision=None):
    require(actor, ACTORS, "actor")
    require(status, TRACE_STATES, "trace status")
    if not isinstance(options,list) or not options or any(not isinstance(x,str) or not x.strip() for x in options):
        raise ResearchError("decision options required")
    if status=="documented" and selected not in options:
        raise ResearchError("documented decision must select one of recorded options")
    if not scope.strip() or not rationale.strip():
        raise ResearchError("scope and rationale required; use explicit unknowns")
    with workspace_lock(root):
        state=load(root)
        decision=item_by_id(state,decision_id)
        if decision["type"]!="Decision":raise ResearchError("decision_id must reference Decision")
        event_map={e["event_id"]:e for e in state["events"]}
        sess={x["id"] for x in state["session_refs"]}
        for eid in event_ids or []:
            if eid not in event_map:raise ResearchError("decision event ID missing")
        for sid in session_ref_ids or []:
            if sid not in sess:raise ResearchError("unknown SessionRef")
        for cid in claim_ids or []:
            if item_by_id(state,cid)["type"]!="Claim":raise ResearchError("claim must be Claim")
        for rid in run_ids or []:
            if item_by_id(state,rid)["type"]!="ExperimentRun":raise ResearchError("run must be ExperimentRun")
        if approval_event_id:
            event=event_map.get(approval_event_id)
            if not event or event.get("actor") not in ("user","mentor") or event.get("action") not in ("status-changed","milestone-accepted","revival-candidate-created"):
                raise ResearchError("approval_event_id must reference preexisting human-attributed approval event")
        trace=new_item(state,"DecisionTrace",title,decision["module"],
                       actor=actor, review="needs-user-confirmation",
                       epistemic="uncertain",description="Documented provenance, not reconstructed chat")
        trace["decision_trace"]={"decision_id":decision_id,"scope":scope,
                                 "options":list(options),"selected":selected,
                                 "rationale":rationale,"status":status,
                                 "event_ids":list(event_ids or []),
                                 "session_ref_ids":list(session_ref_ids or []),
                                 "claim_ids":list(claim_ids or []),
                                 "run_ids":list(run_ids or []),
                                 "approval_event_id":approval_event_id}
        state["relations"].append({"from":trace["id"],"to":decision_id,"type":"depends-on"})
        trace["depends_on"].append(decision_id)
        # Claim/Run/SessionRef references are typed links in trace metadata.
        # Graph projection exposes them without modifying canonical relation types.
        write(root,state,[_event("decision-trace-created",trace["id"],actor,
                                 "Provenance references only; no transcript inferred",trace["decision_trace"])],
              expected_revision=expected_revision)
        return trace


def replay_decision(root, trace_id):
    state=load(root)
    item=item_by_id(state,trace_id)
    if item["type"]!="DecisionTrace":raise ResearchError("not a DecisionTrace")
    trace=item["decision_trace"]
    events={x["event_id"]:x for x in state["events"]}
    sessions={x["id"]:x for x in state["session_refs"]}
    return {"trace_id":trace_id,"decision_id":trace["decision_id"],
            "status":trace["status"],"selected":trace["selected"],
            "scope":trace["scope"],"options":trace["options"],
            "rationale":trace["rationale"],"review_status":item["review_status"],
            "events":[events[x] for x in trace["event_ids"]],
            "session_refs":[{"id":x,"provider":sessions[x]["provider"],
                             "workspace_id":sessions[x]["workspace_id"],
                             "session_id":sessions[x]["session_id"]}
                            for x in trace["session_ref_ids"]],
            "claim_ids":trace["claim_ids"],"run_ids":trace["run_ids"],
            "approval_event_id":trace.get("approval_event_id"),
            "warning":"Only recorded events and SessionRef IDs; missing dialogue was NOT reconstructed."}


def analyze_claim(root, claim_id):
    state=load(root)
    claim=item_by_id(state,claim_id)
    if claim["type"]!="Claim":raise ResearchError("not a Claim")
    evidence={x["id"]:x for x in state["items"]+state["sources"]}
    links=[x for x in state["evidence_links"] if x["claim_id"]==claim_id]
    observations=[]
    for link in links:
        src=evidence[link["evidence_id"]]
        invalidated=(src.get("impact_status") in ("stale","blocked") or
                     src.get("lifecycle_status") in ("quarantined","retired"))
        observations.append({"id":link["id"],"stance":link["stance"],
                             "quality":link["quality"],"scope":link["scope"],
                             "locator":link.get("locator",""),"note":link.get("note",""),
                             "evidence_id":link["evidence_id"],
                             "evidence_type":src.get("type","Source"),
                             "invalidated_or_blocked":bool(invalidated)})
    stances={x["stance"] for x in observations if not x["invalidated_or_blocked"]}
    return {"claim_id":claim_id,"epistemic_status":claim["epistemic_status"],
            "impact_status":claim["impact_status"],
            "evidence":observations,
            "possible_conflict":("supports" in stances and "contradicts" in stances),
            "conflict_warning":("Both support and contradiction recorded; compare their scopes and protocols. "
                                "Overlap and scientific truth have NOT been inferred."),
            "recommendation":"Review conditions and source verification; no automatic promotion to validated."}
