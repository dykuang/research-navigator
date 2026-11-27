"""Three synthetic scientist journeys for v0.6; each fixture auto-removed."""
from pathlib import Path
import tempfile
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from rn_core import init_project,add_item,add_relation,add_source,load,change_status,ResearchError
from rn_domain import create_branch,create_milestone,attach_milestone_evidence,link_evidence,create_session,session_entity_link
from rn_reasoning import create_run,record_run
from rn_interview import start,add_questions,answer,pause,resume,request_exit,reject_exit,confirm_exit,read
from rn_proposals import queue_proposal,preview_proposal,approve_proposal
from unified_graph import unified_graph,read_context
from build_canvas import build_canvas

def question(text):
    return {"text":text,"why":"Clarifies the scientific route",
            "options":"A or B","recommendation":"Compare a falsifiable baseline",
            "lowest_cost_check":"Toy controlled check","depends_on":[],
            "choices":[{"id":"a","label":"Accuracy","description":"Focus macro F1"},
                       {"id":"b","label":"Cost","description":"Reduce compute"}]}
def proposal(root,op,params):
    return {"operation":op,"params":params,
            "reason":"Researcher explicitly reviews reference-only context",
            "expected_revision":load(root)["project"]["revision"]}
def approved_context(root,from_id,to_id,relation):
    params={"from":from_id,"to":to_id,"relation":relation,
            "expected_context_revision":read_context(root)["revision"]}
    req=proposal(root,"link-context",params)
    assert "not scientific" in str(preview_proposal(root,req)).lower() or "Reference-only" in str(preview_proposal(root,req))
    pid=queue_proposal(root,req)["proposal_id"]
    assert not read_context(root)["links"] or all(r["proposal_id"]!=pid for r in read_context(root)["links"])
    approve_proposal(root,pid,confirmed=True)

def journey_grilling_to_evidence(root):
    start(root,topic="SYNTHETIC unknown transfer effect")
    add_questions(root,[question("What should be optimized?")])
    interview_id=read(root)["interview_id"]
    answer(root,"Q-0001",choice_id="other",
           custom_answer="Generalization under shift",supplement="No real measurements")
    hypothesis=add_item(root,kind="Hypothesis",title="Toy model improves transfer",module="topic")
    branch=create_branch(root,"Candidate A","Compare synthetic baselines",["Stop after weak negative"])
    add_relation(root,hypothesis["id"],branch["id"],"member-of")
    baseline=add_item(root,kind="Baseline",title="Shared control",module="literature")
    exp=add_item(root,kind="Experiment",title="Single toy evaluation",module="experiment")
    add_relation(root,exp["id"],hypothesis["id"],"tests")
    run=create_run(root,exp["id"],"toy run",1)
    (root/"toy.log").write_text("SYNTHETIC TEST, not experimental scientific evidence",encoding="utf-8")
    record=record_run(root,run["id"],dataset="synthetic",protocol="toy",
                      code_revision="synthetic-only",seed=1,artifact_path="toy.log",
                      observation="Synthetic result lower than comparison",
                      outcome="negative",metrics=[{"name":"F1","value":0.42,
                                               "unit":"ratio","direction":"higher"}],
                      started_at="2026-11-23T01:00:00+00:00",
                      ended_at="2026-11-23T01:01:00+00:00",synthetic=True)
    claim=add_item(root,kind="Claim",title="Model improves transfer",module="synthesis")
    link_evidence(root,claim["id"],record["result"]["id"],"contradicts",
                  "Only toy split n=1",quality="experiment-observed")
    milestone=create_milestone(root,"Synthetic result reproducibility",["Repeated comparison"])
    attach_milestone_evidence(root,milestone["id"],"C-001",record["result"]["id"])
    original=load(root)
    approved_context(root,"question:"+interview_id+"-Q-0001","item:"+hypothesis["id"],"addresses")
    graph=unified_graph(root)
    assert graph["interview"]["questions"]==1
    assert any(e["type"]=="contradicts" for e in graph["edges"])
    assert any(n["type"]=="MilestoneCriterion" and n["statuses"]["satisfied"] is False
               for n in graph["nodes"])
    assert any(e["provenance"].get("context_only") for e in graph["edges"])
    assert load(root)==original
    assert (build_canvas(root).parent/"unified.html").exists()
    print("PASS scenario 1: Grilling → branch → Run negative → contradictory evidence → scientific Milestone")

def journey_routes_archive(root):
    baseline=add_item(root,kind="Baseline",title="Toy shared baseline",module="literature")
    a=create_branch(root,"Route A","Test novelty",["Stop after negative"])
    b=create_branch(root,"Route B","Try alternative",["Stop if unsupported"])
    add_relation(root,baseline["id"],a["id"],"member-of")
    add_relation(root,baseline["id"],b["id"],"member-of")
    start(root,topic="Toy alternative research")
    add_questions(root,[question("Which route is plausible?")])
    ident=read(root)["interview_id"]
    approved_context(root,"question:"+ident+"-Q-0001","item:"+a["id"],"addresses")
    change_status(root,a["id"],"lifecycle_status","parked",
                  "Human explicitly parked low-evidence route",actor="user",
                  failure_scope="single toy run",revival_triggers="new independent test")
    graph=unified_graph(root)
    assert any(n["id"]=="item:"+a["id"] and n["statuses"]["lifecycle_status"]=="parked"
               for n in graph["nodes"])
    assert any(e["type"]=="addresses" for e in graph["edges"])
    before=load(root)
    try:
        queue_proposal(root,proposal(root,"link-context",
            {"from":"answer:"+ident+"-Q-0001","to":"item:"+a["id"],
             "relation":"motivates","expected_context_revision":1}))
    except ResearchError: pass
    else:raise AssertionError("Archived route must not receive new active links")
    assert load(root)==before
    assert sum(n["id"]=="item:"+baseline["id"] for n in graph["nodes"])==1
    print("PASS scenario 2: shared baseline and parked historical link isolated")

def journey_sessions_and_exit(root):
    idea=add_item(root,kind="Idea",title="Cross-harness idea",module="topic")
    codex=create_session(root,"codex","toy-workspace","toy-shared")
    deepseek=create_session(root,"deepseek","toy-workspace","toy-shared")
    for ref in (codex,deepseek):session_entity_link(root,ref["id"],idea["id"],"discussion")
    start(root,topic="Synthetic interview handoff")
    add_questions(root,[question("One objective?")])
    ident=read(root)["interview_id"]
    pause(root);resume(root)
    answer(root,"Q-0001",choice_id="a",supplement="SYNTHETIC auxiliary note")
    request_exit(root,"Accepted toy direction; no scientific validation")
    reject_exit(root,"Need another user consideration")
    request_exit(root,"Confirmed only the conversation scope")
    confirm_exit(root)
    ref_src="session:"+deepseek["id"]
    approved_context(root,ref_src,"question:"+ident+"-Q-0001","discussed-in-session")
    graph=unified_graph(root)
    refs=[n for n in graph["nodes"] if n["kind"]=="session-ref"]
    assert len(refs)==2 and {x["metadata"]["provider"] for x in refs}=={"codex","deepseek"}
    assert graph["interview"]["status"]=="completed"
    assert any(n["kind"]=="answer" and n["metadata"]["supplement"] for n in graph["nodes"])
    assert all("chat text not stored" in x["description"] for x in refs)
    print("PASS scenario 3: Codex/DeepSeek SessionRef, resumed interview and explicit exit")

def main():
    for name,scenario in (("grilling",journey_grilling_to_evidence),
                          ("archive",journey_routes_archive),
                          ("session",journey_sessions_and_exit)):
        with tempfile.TemporaryDirectory(prefix="rn-v06-journey-"+name+"-") as temp:
            root=Path(temp)
            init_project(root,"SYNTHETIC "+name)
            scenario(root)
        assert not Path(temp).exists()
    print("PASS all 3 synthetic research journeys; temporary projects automatically cleaned")

if __name__=="__main__":
    main()
