"""v0.4.1 interview lifecycle regression. Every project is synthetic and temporary."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from rn_core import init_project, load, ResearchError, add_item
from rn_interview import (start,read,add_questions,answer,frontier,pause,resume,
                          request_exit,reject_exit,confirm_exit,abandon,reopen,
                          handoff,interview_path)
from build_interview import build as build_interview
from build_canvas import build_canvas
from install_interview_guidance import install as install_guidance, START as AGENTS_START

def question(text="Define useful improvement",depends_on=None):
    return {"text":text,
            "why":"Specify falsifiable research conditions",
            "options":"F1 vs accuracy; cost tradeoff",
            "recommendation":"Define a baseline and evaluation protocol",
            "lowest_cost_check":"Check one synthetic pilot, not a real result",
            "depends_on":list(depends_on or [])}

class InterviewLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix="rn-v041-test-")
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)/"project"
        init_project(self.root,"SYNTHETIC toy question")
    def begin(self):
        return start(self.root,topic="Toy transfer",actor="user")
    def test_explicit_start_and_no_implicit_interview(self):
        self.assertFalse(interview_path(self.root).exists())
        self.assertIsNone(build_interview(self.root))
        self.begin()
        self.assertTrue(interview_path(self.root).exists())
        self.assertEqual(read(self.root)["status"],"active")
    def test_start_does_not_touch_canonical_state(self):
        canonical=load(self.root)
        self.begin();add_questions(self.root,[question()])
        answer(self.root,"Q-0001","F1 increase by 2 points",actor="user")
        self.assertEqual(load(self.root),canonical)
    def test_no_accidental_overwrite(self):
        self.begin()
        with self.assertRaises(ResearchError):self.begin()
    def test_multi_question_frontier_depends_on_verified_answer(self):
        self.begin()
        add_questions(self.root,[question("Which dataset?")])
        add_questions(self.root,[question("Which metric?",["Q-0001"])])
        f=frontier(read(self.root))
        self.assertEqual([q["id"] for q in f["ready"]],["Q-0001"])
        self.assertEqual(f["blocked"][0]["depends_on"],["Q-0001"])
        with self.assertRaises(ResearchError):
            answer(self.root,"Q-0002","F1")
        answer(self.root,"Q-0001","Toy dataset",actor="user")
        self.assertEqual([q["id"] for q in frontier(read(self.root))["ready"]],["Q-0002"])
    def test_unchanged_resumption_after_pause(self):
        self.begin();add_questions(self.root,[question()])
        pause(self.root)
        self.assertEqual(read(self.root)["status"],"paused")
        with self.assertRaises(ResearchError):answer(self.root,"Q-0001","Value")
        restored=resume(self.root)
        self.assertEqual(restored["status"],"active")
        self.assertEqual(restored["questions"][0]["status"],"pending")
    def test_deferred_unresolved_do_not_unlock_dependency(self):
        self.begin();add_questions(self.root,[question("Premise")])
        add_questions(self.root,[question("Dependent",["Q-0001"])])
        answer(self.root,"Q-0001","Need data",status="deferred")
        self.assertEqual(frontier(read(self.root))["ready"][0]["id"],"Q-0001")
        self.assertEqual(frontier(read(self.root))["blocked"][0]["id"],"Q-0002")
        answer(self.root,"Q-0001","Still unknown",status="unresolved")
        self.assertEqual(frontier(read(self.root))["blocked"][0]["id"],"Q-0002")
    def test_no_agent_auto_approval(self):
        self.begin();add_questions(self.root,[question()])
        for operation in (lambda:answer(self.root,"Q-0001","I agree",actor="agent"),
                          lambda:confirm_exit(self.root,actor="agent"),
                          lambda:pause(self.root,actor="agent")):
            with self.assertRaises(ResearchError):operation()
    def test_explicit_exit_reject_and_confirm(self):
        self.begin();add_questions(self.root,[question()])
        request_exit(self.root,"Hypothesis remains untested",actor="agent")
        self.assertEqual(read(self.root)["status"],"consensus-review")
        with self.assertRaises(ResearchError):confirm_exit(self.root)
        reject_exit(self.root,"Need another round",actor="user")
        self.assertEqual(read(self.root)["status"],"active")
        answer(self.root,"Q-0001","Metric is F1")
        request_exit(self.root,"Researcher confirmed F1, science pending")
        confirmed=confirm_exit(self.root,actor="user")
        self.assertEqual(confirmed["status"],"completed")
        self.assertEqual(confirmed["accepted_open_questions"],[])
        self.assertEqual(frontier(read(self.root))["ready"],[])
    def test_user_accepts_open_items_one_by_one(self):
        self.begin();add_questions(self.root,[question("A"),question("B")])
        answer(self.root,"Q-0001","Confirmed")
        request_exit(self.root,"Need to revisit B")
        with self.assertRaises(ResearchError):confirm_exit(self.root,["Q-0003"])
        with self.assertRaises(ResearchError):confirm_exit(self.root,[])
        confirmed=confirm_exit(self.root,["Q-0002"])
        self.assertEqual(confirmed["accepted_open_questions"],["Q-0002"])
    def test_revise_invalidates_dependent_confirmation(self):
        self.begin();add_questions(self.root,[question("What dataset?")])
        add_questions(self.root,[question("Metric",["Q-0001"])])
        answer(self.root,"Q-0001","Dataset A")
        answer(self.root,"Q-0002","F1")
        with self.assertRaises(ResearchError):answer(self.root,"Q-0001","Dataset B")
        answer(self.root,"Q-0001","Dataset B",revise=True)
        s=read(self.root)
        self.assertEqual(s["questions"][1]["status"],"unresolved")
        self.assertIsNone(s["questions"][1]["confirmed_by"])
    def test_stale_write_and_revision(self):
        self.begin()
        rev=read(self.root)["revision"]
        add_questions(self.root,[question()],expected_revision=rev)
        with self.assertRaises(ResearchError):add_questions(self.root,[question()],expected_revision=rev)
    def test_bad_dependency_and_no_partial_mutation(self):
        self.begin()
        before=read(self.root)
        with self.assertRaises(ResearchError):
            add_questions(self.root,[question("bad",["Q-9999"])])
        self.assertEqual(read(self.root),before)
    def test_corrupt_data_fail_closed(self):
        self.begin()
        p=interview_path(self.root)
        p.write_text("{this is not JSON",encoding="utf-8")
        with self.assertRaises(ResearchError):read(self.root)
        with self.assertRaises(ResearchError):start(self.root,topic="Overwrite")
    def test_wrong_project_id_fail_closed(self):
        self.begin()
        p=interview_path(self.root)
        s=json.loads(p.read_text(encoding="utf-8"))
        s["project_id"]="other-project"
        p.write_text(json.dumps(s),encoding="utf-8")
        with self.assertRaises(ResearchError):read(self.root)
    def test_abandon_and_reopen_and_safe_restart(self):
        self.begin()
        former=read(self.root)["interview_id"]
        abandon(self.root,"Study postponed")
        reopen(self.root,"Try again")
        with self.assertRaises(ResearchError):start(self.root,topic="Another",restart=True)
        abandon(self.root,"New start requested")
        start(self.root,topic="Another",restart=True)
        archive=interview_path(self.root).parent/"archive"/(former+".json")
        self.assertTrue(archive.exists())
        self.assertNotEqual(read(self.root)["interview_id"],former)
    def test_outside_project_no_recovery(self):
        self.begin()
        other=Path(self.tmp.name)/"unrelated"
        init_project(other,"Different research project")
        with self.assertRaises(ResearchError):read(other)
    def test_handoff_does_not_leak_transcript_or_change_revision(self):
        self.begin()
        add_questions(self.root,[question()])
        answer(self.root,"Q-0001","Synthetic answer")
        s=read(self.root)
        h=handoff(self.root)
        self.assertIn("$research-navigator",h["startup_hint"])
        self.assertEqual(h["confirmed"][0]["answer"],"Synthetic answer")
        self.assertEqual(read(self.root),s)
    def test_html_safe_and_canvas_remains_read_only(self):
        self.begin()
        add_questions(self.root,[question('<script>alert("x")</script>')])
        old_revision=read(self.root)["revision"]
        out=build_canvas(self.root)
        html=(out.parent/"interview.html").read_text(encoding="utf-8")
        self.assertIn("\\u003cscript\\u003e",html)
        self.assertNotIn('<script>alert("x")</script>',html)
        self.assertIn('href="interview.html"',out.read_text(encoding="utf-8"))
        self.assertEqual(read(self.root)["revision"],old_revision)
    def test_no_interview_canvas_no_broken_link(self):
        out=build_canvas(self.root)
        self.assertNotIn('href="interview.html"',out.read_text(encoding="utf-8"))
        self.assertFalse((out.parent/"interview.html").exists())
    def test_frontier_bounds(self):
        self.begin()
        with self.assertRaises(ResearchError):add_questions(self.root,[question(str(i)) for i in range(6)])
        with self.assertRaises(ResearchError):frontier(read(self.root),6)
    def test_human_pending_status_is_not_scientific_proof(self):
        self.begin();add_questions(self.root,[question()])
        answer(self.root,"Q-0001","Claim: F1 2 points better")
        self.assertEqual(load(self.root)["items"],[])

    def test_agents_md_opt_in_does_not_overwrite(self):
        self.begin()
        file=self.root/"AGENTS.md"
        file.write_text("# Existing rules\nKeep unrelated instructions.\n",encoding="utf-8")
        before=file.read_text(encoding="utf-8")
        preview=install_guidance(self.root)
        self.assertFalse(preview["applied"])
        self.assertEqual(file.read_text(encoding="utf-8"),before)
        installed=install_guidance(self.root,apply=True)
        self.assertTrue(installed["applied"])
        updated=file.read_text(encoding="utf-8")
        self.assertTrue(updated.startswith(before.rstrip()))
        self.assertIn(AGENTS_START,updated)
        with self.assertRaises(ResearchError):install_guidance(self.root,apply=True)
        self.assertEqual(file.read_text(encoding="utf-8"),updated)
    def test_agents_md_no_implicit_project_initialization(self):
        other=Path(self.tmp.name)/"no-such-research"
        with self.assertRaises(ResearchError):install_guidance(other,apply=True)
        self.assertFalse((other/"AGENTS.md").exists())

if __name__=="__main__": unittest.main()
