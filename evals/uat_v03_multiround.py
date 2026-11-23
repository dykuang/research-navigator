#!/usr/bin/env python3
"""v0.3 multi-round researcher UAT. All people, studies, numbers and logs are fictional.

Each narrative starts a fresh TemporaryDirectory, advances in 3-6 user turns, and
verifies that the canonical state after each turn matches expected safeguards.
No fixture projects/artifacts remain after process exit.
"""
from __future__ import annotations
from pathlib import Path
import json
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from rn_core import (ResearchError, init_project, add_item, add_source, add_relation,
                     change_status, load, query, validate_state)
from rn_domain import create_branch, create_milestone, create_session, link_evidence
from rn_reasoning import (create_run, record_run, analyze_claim,
                          invalidate_run, create_decision_trace, replay_decision)
from graph_projection import project_graph
from build_dashboard import build

DATE0="2026-11-23T08:00:00+08:00"
DATE1="2026-11-23T08:02:00+08:00"
RESULTS=[]

def stage(text):
    print("    ↪ "+text)

def saved(root):
    state=load(root)
    errors=validate_state(state)
    assert not errors, errors
    return state

def rejects(fn, label):
    try:
        fn()
    except ResearchError:
        stage(label+" — correctly rejected")
    else:
        raise AssertionError(label+": unsafe action was permitted")

def synthetic_result(root, experiment, number=1, outcome="negative"):
    run=create_run(root,experiment["id"],"SYNTHETIC test run "+str(number),number)
    log=root / ("synthetic-run-"+str(number)+".log")
    log.write_text("SYNTHETIC FIXTURE: not real measurement\nF1=0.49 versus baseline=0.50",encoding="utf-8")
    pair=record_run(root,run["id"],dataset="toy-data-v1",
        protocol="fixed synthetic split",code_revision="synthetic-commit",
        seed=7,artifact_path=log.name,observation="Toy F1 did not improve",
        outcome=outcome,metrics=[{"name":"F1","value":0.49,"unit":"ratio","direction":"higher"}],
        started_at=DATE0,ended_at=DATE1,synthetic=True)
    return pair

def novice_four_rounds(root):
    stage("Round 1 / Student: 'I have only a vague topic; do not claim novelty.'")
    idea=add_item(root,kind="Idea",title="SYNTHETIC: dynamic fusion",module="topic")
    hyp=add_item(root,kind="Hypothesis",title="SYNTHETIC: gain on new domain",module="topic")
    source=add_source(root,"Not a verified real paper",
                      url="https://example.org/fictional-abstract",
                      access_level="abstract",verification_status="unverified")
    assert source["verification_status"]=="unverified"
    stage("Round 2 / Student: 'Can I call the abstract an inspected primary paper?'")
    rejects(lambda: change_status(root,hyp["id"],"epistemic_status",
                                  "source-backed","Abstract sounds convincing",
                                  evidence_refs=[source["id"]]),
            "Abstract must not create source-backed claim")
    exp=add_item(root,kind="Experiment",title="SYNTHETIC protocol",module="experiment")
    stage("Round 3 / Student: 'The trial is planned, can I report an improvement now?'")
    run=create_run(root,exp["id"],"SYNTHETIC attempt",1)
    assert run["run"]["result_id"] is None
    assert run["epistemic_status"]=="uncertain"
    stage("Round 4 / Student: 'The tiny toy test failed; preserve the negative data.'")
    log=root/"toy.log";log.write_text("SYNTHETIC FIXTURE - F1=0.49",encoding="utf-8")
    pair=record_run(root,run["id"],dataset="toy",protocol="toy split",code_revision="synthetic",
        seed=9,artifact_path="toy.log",observation="No benefit observed",
        outcome="negative",metrics=[{"name":"F1","value":0.49,"unit":"ratio","direction":"higher"}],
        started_at=DATE0,ended_at=DATE1,synthetic=True)
    assert pair["result"]["outcome"]=="negative"
    assert pair["run"]["epistemic_status"]=="uncertain"
    assert pair["run"]["lifecycle_status"]=="active"
    assert saved(root)["project"]["schema_version"]=="0.2.0"
    RESULTS.append("novice: 4 rounds, schema/evidence/negative checks passed")

def branch_risk_four_rounds(root):
    stage("Round 1 / Student: 'Explore routes A/B with a shared, untouched baseline.'")
    baseline=add_item(root,kind="Baseline",title="SYNTHETIC common baseline",module="literature")
    a=create_branch(root,"SYNTHETIC route A","Compare toy F1",["Stop after valid low-power rerun"])
    b=create_branch(root,"SYNTHETIC route B","Compare toy F1 separately",["Stop if invalid"])
    exp=add_item(root,kind="Experiment",title="SYNTHETIC branch A evaluation",module="experiment")
    add_relation(root,exp["id"],a["id"],"member-of")
    add_relation(root,baseline["id"],a["id"],"member-of")
    add_relation(root,baseline["id"],b["id"],"member-of")
    stage("Round 2 / Student: 'Weak negative observed under A, not universal failure.'")
    pair=synthetic_result(root,exp)
    assert saved(root)["items"]
    stage("Round 3 / Student: 'Park route A and keep B and baseline available.'")
    change_status(root,a["id"],"lifecycle_status","parked",
                  "SYNTHETIC weak negative; user decides to park this route",
                  actor="user",failure_scope="two toy observations, not real evidence",
                  revival_triggers="Independent dataset, supervisor consent",
                  failure_category="evaluation",evidence_refs=[pair["result"]["id"]])
    state=saved(root)
    by={x["id"]:x for x in state["items"]}
    assert by[b["id"]]["impact_status"]=="current"
    assert by[baseline["id"]]["impact_status"]=="current"
    assert a["id"] not in {x["item_id"] for x in query(state,"planning")}
    assert a["id"] in {x["item_id"] for x in query(state,"risk-check")}
    stage("Round 4 / Student: 'Continue A experiment while branch A is parked.'")
    rejects(lambda:create_run(root,exp["id"],"SHOULD NOT RUN",2),
            "New runs under archived ResearchBranch must be blocked")
    rejects(lambda:create_run(root,exp["id"],"SHOULD NOT RUN",3),
            "Repeated archived-branch experiment planning must be blocked")
    assert saved(root)["project"]["revision"]>=5
    RESULTS.append("archive: 4 rounds, shared baseline untouched, route blocked")

def supervisor_four_rounds(root):
    stage("Round 1 / Supervisor: 'Show both supporting and contradicting scoped evidence.'")
    claim=add_item(root,kind="Claim",title="SYNTHETIC domain generalization claim",module="synthesis")
    exp=add_item(root,kind="Experiment",title="SYNTHETIC experiment",module="experiment")
    pair=synthetic_result(root,exp)
    paper=add_source(root,"SYNTHETIC abstract-only comparison",
                     url="https://example.org/fictional-paper",
                     access_level="abstract",verification_status="unverified")
    link_evidence(root,claim["id"],paper["id"],"supports","author-reported abstract, not verified",quality="unverified")
    link_evidence(root,claim["id"],pair["result"]["id"],"contradicts","toy data, 1 seed",quality="experiment-observed")
    report=analyze_claim(root,claim["id"])
    assert report["possible_conflict"] and report["epistemic_status"]=="uncertain"
    stage("Round 2 / Supervisor: 'Does mixed evidence prove this method false?'")
    assert "scientific truth" in report["conflict_warning"]
    stage("Round 3 / Supervisor: 'A leakage bug invalidates this toy run.'")
    invalidate_run(root,pair["run"]["id"],"SYNTHETIC evaluation leakage")
    after=analyze_claim(root,claim["id"])
    assert any(e["invalidated_or_blocked"] for e in after["evidence"])
    assert not after["possible_conflict"]
    stage("Round 4 / Supervisor: 'Keep original negative result; mark dependent claims blocked.'")
    state=saved(root)
    by={x["id"]:x for x in state["items"]}
    assert by[claim["id"]]["impact_status"]=="blocked"
    assert by[pair["result"]["id"]]["outcome"]=="negative"
    RESULTS.append("supervisor: 4 rounds, scoped conflict + invalidation passed")

def provenance_four_rounds(root):
    stage("Round 1 / Student: 'Keep a pointer to discussion, not full transcript.'")
    decision=add_item(root,kind="Decision",title="SYNTHETIC next route",module="pivot")
    session=create_session(root,"codex","synthetic-workspace","synthetic-session-A")
    assert not session.get("url_verified",False)
    stage("Round 2 / Student: 'Record decision's genuine event ID only.'")
    original_event=next(e["event_id"] for e in load(root)["events"] if e["action"]=="item-created")
    trace=create_decision_trace(root,decision_id=decision["id"],
        title="SYNTHETIC rationale",scope="toy comparison",
        options=["Retry A","Pilot B"],selected="Pilot B",
        rationale="Lower toy cost, still scientifically uncertain",
        event_ids=[original_event],session_ref_ids=[session["id"]])
    replay=replay_decision(root,trace["id"])
    assert len(replay["events"])==1 and replay["events"][0]["event_id"]==original_event
    assert len(replay["session_refs"])==1
    assert "NOT reconstructed" in replay["warning"]
    stage("Round 3 / Student: 'Can an Agent reconstruct an unrecorded event and approve it?'")
    rejects(lambda:create_decision_trace(root,decision_id=decision["id"],
        title="SHOULD FAIL",scope="toy",options=["X"],selected="X",
        rationale="unsupported",event_ids=["invented-event"]),
        "Fabricated event rejected")
    rejects(lambda:create_decision_trace(root,decision_id=decision["id"],
        title="SHOULD FAIL",scope="toy",options=["X"],selected="X",
        rationale="unsupported",approval_event_id=original_event),
        "Unapproved event cannot be reused as proof of human approval")
    stage("Round 4 / Supervisor: 'Show the decision graph without changing source data.'")
    state=saved(root)
    graph=project_graph(state,view="reasoning",limit=None)
    assert any(x["entity_id"]==trace["id"] for x in graph["nodes"])
    assert any(x["type"]=="linked-session" for x in graph["edges"])
    assert saved(root)==state
    RESULTS.append("provenance: 4 rounds, real-only replay + graph passed")

def canvas_two_rounds(root):
    stage("Round 1 / Student: 'Generate offline canvas; do not silently edit state.'")
    claim=add_item(root,kind="Claim",title="<script>synthetic-xss()</script>",module="synthesis")
    before=saved(root)
    output=build(root)
    canvas=root/"research"/"canvas"/"index.html"
    text=canvas.read_text(encoding="utf-8")
    assert 'reasoning' in text and '<script>synthetic-xss()</script>' not in text
    assert canvas.exists() and output.exists()
    stage("Round 2 / Mentor: 'Inspect old state again; no approval was inferred.'")
    assert saved(root)==before
    RESULTS.append("canvas: 2 rounds, read-only + escaped HTML passed")

def main():
    suites=[("novice",novice_four_rounds),("archive",branch_risk_four_rounds),
            ("supervisor",supervisor_four_rounds),
            ("provenance",provenance_four_rounds),("canvas",canvas_two_rounds)]
    failed=[]
    for name,run in suites:
        with tempfile.TemporaryDirectory(prefix="rn-v03-uat-"+name+"-") as tmp:
            root=Path(tmp)/"project"
            init_project(root,"SYNTHETIC FIXTURE v0.3 multi-round "+name)
            print("\n=== "+name.upper()+" ===")
            try:
                run(root)
                print("[PASS]",name)
            except Exception as exc:
                import traceback
                traceback.print_exc()
                failed.append((name,str(exc)))
                print("[FAIL]",name,repr(exc))
        assert not Path(tmp).exists(), "Temporary fixture was not cleaned up!"
    print("\nRESULT: %d/%d multi-round user journeys passed" % (len(suites)-len(failed),len(suites)))
    for item in RESULTS: print(" • "+item)
    if failed:sys.exit(1)

if __name__=="__main__":
    main()
