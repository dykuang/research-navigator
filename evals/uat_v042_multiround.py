"""Seven simulated interactive grilling rounds with real durable CLI semantics."""
import sys
import tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from rn_core import init_project,load,ResearchError
from rn_interview import (start,read,add_questions,answer,frontier,pause,resume,
                          request_exit,reject_exit,confirm_exit,handoff)
from rn_interview_choices import (codex_request,resolve_codex_answer,text_prompt,delivery_plan)
from build_canvas import build_canvas

def q(title,depends=None):
    return {
        "text":title,"why":"Scientific objective affects evaluation",
        "options":"accuracy or budget","recommendation":"Start with accuracy",
        "lowest_cost_check":"Synthetic no-run comparison",
        "depends_on":depends or [],
        "choices":[
            {"id":"accuracy","label":"Improve accuracy","description":"Target macro F1"},
            {"id":"compute","label":"Lower compute cost","description":"Limit GPU hours"},
        ],
        "recommended_choice_id":"accuracy"
    }

def reject(fn):
    try:fn()
    except ResearchError:return
    raise AssertionError("invalid operation succeeded")

def main():
    with tempfile.TemporaryDirectory(prefix="v042-synthetic-") as tmp:
        root=Path(tmp)/"research"
        init_project(root,"SYNTHETIC multi-round interactive research study")
        base=load(root)
        # Round 1 - Student activates Grilling, agent offers typed choices.
        start(root,topic="SYNTHETIC uncertain research objective")
        add_questions(root,[q("Which outcome is worth optimizing?")])
        first=frontier(read(root))["ready"][0]
        assert "其他／自定义" in text_prompt(first)
        # Simulate a runtime without the UI and a failed sync modal.
        no_modal=delivery_plan(first,capability="none")
        assert no_modal["mode"]=="chat" and "补充说明" in no_modal["fallback_text"]
        failed_modal=delivery_plan(first,capability="sync",failure="error")
        assert failed_modal["mode"]=="chat" and "其他／自定义" in failed_modal["fallback_text"]
        assert not failed_modal["native_tool_called"]
        request=codex_request(first)
        assert len(request["questions"][0]["options"])==2
        # Round 2 - Student chooses Other; no forced A/B answer.
        option=resolve_codex_answer(first,{
            "answers":{"q_0001":{"selected":["Other"],"other":"Measure robustness under shift"}}})
        answer(root,"Q-0001",choice_id=option["choice_id"],
               custom_answer=option["custom_answer"],actor="user")
        assert read(root)["questions"][0]["custom_answer"]=="Measure robustness under shift"
        # Round 3 - Agent adds dependent question; student selects fixed choice.
        add_questions(root,[q("How should we evaluate robustness?",["Q-0001"])])
        second=frontier(read(root))["ready"][0]
        option=resolve_codex_answer(second,{"answers":{"q_0002":{"answers":["Improve accuracy"]}}})
        answer(root,"Q-0002",choice_id=option["choice_id"],
               supplement="Include cost and robustness constraints")
        # Round 4 - Interrupt and resume from persistent file.
        pause(root)
        h=handoff(root)
        assert h["confirmed"][0]["answer"]=="Measure robustness under shift"
        assert h["confirmed"][1]["supplement"]=="Include cost and robustness constraints"
        resume(root)
        # Round 5 - Change first answer -> invalidate dependent confirmation.
        answer(root,"Q-0001",choice_id="accuracy",revise=True)
        assert read(root)["questions"][1]["status"]=="unresolved"
        assert read(root)["questions"][1]["selected_option_id"] is None
        # Round 6 - User resolves dependent choice and rejects premature exit.
        answer(root,"Q-0002",choice_id="other",custom_answer="Use cross-site evaluation")
        request_exit(root,"Current research scope is agreed; not scientifically proven")
        reject(lambda:confirm_exit(root,actor="agent"))
        reject_exit(root,"Need to discuss compute budget",actor="user")
        add_questions(root,[q("What is the acceptable compute budget?")])
        answer(root,"Q-0003",choice_id="compute")
        # Round 7 - Explicit exit; no background UI write.
        request_exit(root,"Confirmed objective, evaluations and budget")
        confirm_exit(root,actor="user")
        assert frontier(read(root))["ready"]==[]
        rev=read(root)["revision"]
        board=build_canvas(root)
        assert (board.parent/"interview.html").exists()
        assert read(root)["revision"]==rev
        assert load(root)==base
        print("PASS: 7 synthetic rounds: typed options, Other, native resolution, cross-session, revision, explicit exit")
    assert not Path(tmp).exists()
    print("PASS: synthetic project, interview and generated HTML removed after UAT")

if __name__=="__main__":
    main()
