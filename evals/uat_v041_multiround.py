"""v0.4.1 fictional researcher multi-round session UAT; zero persistent fixtures."""
from pathlib import Path
import json
import sys
import tempfile

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from rn_core import ResearchError,init_project,load
from rn_interview import (start,read,add_questions,answer,frontier,pause,resume,
                          request_exit,reject_exit,confirm_exit,handoff)
from build_canvas import build_canvas

def q(text,deps=None):
    return {"text":text,"why":"Research choice changes experiment design",
            "options":"Option A vs B; scientific trade-offs remain uncertain",
            "recommendation":"Make assumptions explicit; user chooses",
            "lowest_cost_check":"Compare one controlled toy scenario",
            "depends_on":deps or []}
def reject(fn):
    try:fn()
    except ResearchError:return
    raise AssertionError("Invalid transition incorrectly accepted")

def main():
    with tempfile.TemporaryDirectory(prefix="rn-v041-synthetic-") as tmp:
        root=Path(tmp)/"research"
        init_project(root,"SYNTHETIC interview demonstration")
        before=load(root)
        # Round 1: explicit activation and targeted questions.
        start(root,topic="Can an imagined model improve cross-domain toy F1?")
        add_questions(root,[q("What task and baseline?"),
                            q("What does success mean?")])
        first=frontier(read(root))
        assert len(first["ready"])==2
        # Round 2: student answers one and defers the other, no fake consensus.
        answer(root,"Q-0001","Toy image classification versus baseline X",actor="user")
        answer(root,"Q-0002","Need to check metric",status="deferred",actor="user")
        add_questions(root,[q("Which minimum experiment can distinguish it?",["Q-0002"])])
        assert len(frontier(read(root))["blocked"])==1
        # Round 3: new independent session gets no prior in-memory chat.
        pause(root)
        del first
        assert read(root)["status"]=="paused"
        assert "resume" not in {q["status"] for q in read(root)["questions"]}
        resume(root)
        packet=handoff(root)
        assert packet["confirmed"][0]["answer"]=="Toy image classification versus baseline X"
        assert "Q-0002" in {q["id"] for q in packet["frontier"]}
        # Round 4: user clarifies and agent asks dependent question.
        answer(root,"Q-0002","Macro F1 on held-out domain",actor="user")
        assert [x["id"] for x in frontier(read(root))["ready"]]==["Q-0003"]
        answer(root,"Q-0003","Two seeds with fixed split; no actual run yet")
        # Round 5: proposed consensus, user rejects.
        request_exit(root,"Task, metric and minimal experiment agreed; not scientifically validated")
        reject(lambda:confirm_exit(root,[],actor="agent"))
        reject_exit(root,"Need to define permitted computing budget")
        add_questions(root,[q("What is permitted budget?")])
        answer(root,"Q-0004","Two GPU-hours maximum")
        # Round 6: explicit consensus and exit.
        request_exit(root,"Task, F1 metric, toy protocol and budget defined; no scientific conclusion")
        out=confirm_exit(root,actor="user")
        assert out["status"]=="completed" and out["exit_confirmed_by"]=="user"
        assert frontier(out)["ready"]==[]
        assert len([h for h in out["history"] if h["action"]=="exit-rejected"])==1
        # Round 7: rendering/normal-mode and canonical-state isolation.
        page=build_canvas(root)
        assert (page.parent/"interview.html").exists()
        assert read(root)["status"]=="completed"
        assert load(root)==before
        print("PASS: 7 rounds, cross-session resume, deferred dependency, rejected/confirmed exit, no canonical writes")
    assert not Path(tmp).exists(),"fixture cleanup failed"
    print("PASS: synthetic project and HTML automatically removed")

if __name__=="__main__":
    main()
