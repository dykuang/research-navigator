"""v0.4 research decision projections: end-to-end synthetic, no real studies."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from rn_core import init_project,add_item,add_relation,add_source,change_status,load,ResearchError
from rn_domain import create_milestone,create_branch,link_evidence
from rn_decision import gaps,opportunities,archive_watchlist,mentor_brief,markdown_brief,summarize
from build_decision import build as build_decision
from build_canvas import build_canvas

class DecisionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)/"synthetic-study"
        init_project(self.root,"SYNTHETIC FIXTURE - NO REAL SCIENCE","Does A outperform B under toy conditions?")
    def tearDown(self):
        self.tmp.cleanup()
    def thing(self,kind,title="mock",module="topic",**kw):
        return add_item(self.root,kind=kind,title=title,module=module,**kw)
    def test_empty_project(self):
        r=summarize(self.root)
        self.assertEqual(r["pending_gaps"],[])
        self.assertEqual(r["proposed_next_checks"],[])
        self.assertEqual(r["archive_review_watchlist"],[])
        self.assertEqual(r["revision"],0)
    def test_uncertain_hypothesis_generates_unapproved_check(self):
        hyp=self.thing("Hypothesis","toy uncertain hypothesis")
        report=summarize(self.root)
        codes={g["code"] for g in report["pending_gaps"]}
        self.assertIn("HYPOTHESIS_NOT_TESTED",codes)
        obs=next(o for o in report["proposed_next_checks"] if o["subject_id"]==hyp["id"])
        self.assertFalse(obs["execution_approved"])
        self.assertFalse(obs["is_canonical_state"])
        self.assertEqual(obs["estimated_cost"],"unknown")
        self.assertEqual(obs["expected_information_value"],"uncertain")
        self.assertEqual(load(self.root)["project"]["revision"],1)
    def test_planned_experiment_not_observed(self):
        experiment=self.thing("Experiment","Toy Experiment",module="experiment")
        codes={g["code"] for g in gaps(load(self.root))}
        self.assertIn("EXPERIMENT_NO_REGISTERED_RUN",codes)
        self.assertFalse(any(o["execution_approved"] for o in opportunities(load(self.root))))
    def test_archive_stays_isolated(self):
        hyp=self.thing("Hypothesis","Toy archived")
        change_status(self.root,hyp["id"],"lifecycle_status","parked",
                      "small simulated study failed",actor="user",
                      failure_scope="synthetic toy subset n=1",
                      revival_triggers="new high-quality dataset")
        s=load(self.root)
        self.assertNotIn(hyp["id"],{o["subject_id"] for o in opportunities(s)})
        watch=archive_watchlist(s)
        self.assertEqual(watch[0]["id"],hyp["id"])
        self.assertEqual(watch[0]["revival_conditions"],"new high-quality dataset")
        self.assertFalse(watch[0]["trigger_verified"])
        self.assertFalse(watch[0]["automatic_reactivation"])
        self.assertEqual(s["items"][0]["lifecycle_status"],"parked")
    def test_experiment_negative_does_not_auto_quarantine(self):
        exp=self.thing("Experiment",module="experiment")
        change_status(self.root,exp["id"],"outcome","negative","Toy failure")
        self.assertEqual(load(self.root)["items"][0]["lifecycle_status"],"active")
    def test_scoped_claim_conflict_requires_review_not_proof(self):
        claim=self.thing("Claim","Toy claim",module="synthesis")
        x=self.thing("Result","positive toy observation",module="experiment",
                     observation="SYNTHETIC positive",artifact_path="toy-positive.txt")
        y=self.thing("Result","negative toy observation",module="experiment",
                     observation="SYNTHETIC negative",artifact_path="toy-negative.txt")
        link_evidence(self.root,claim["id"],x["id"],"supports","toy condition A",
                      quality="experiment-observed")
        link_evidence(self.root,claim["id"],y["id"],"contradicts","toy condition B",
                      quality="experiment-observed")
        ss=gaps(load(self.root))
        conf=next(g for g in ss if g["code"]=="CLAIM_CONFLICTING_EVIDENCE")
        self.assertIn("不能自动判定",conf["description"])
        self.assertFalse(conf["claim_is_scientifically_proven"])
    def test_milestone_pending_human_and_evidence(self):
        m=create_milestone(self.root,"Fair comparison",["consistent split","seed logged"])
        r=mentor_brief(load(self.root))
        self.assertEqual(r["milestones"][0]["id"],m["id"])
        self.assertFalse(r["milestones"][0]["accepted"])
        checks=[g for g in r["pending_gaps"] if g["code"]=="MILESTONE_GATE_PENDING"]
        self.assertEqual(len(checks),2)
        self.assertFalse(r["milestones"][0]["scientific_truth_certified"])
    def test_stale_items_cannot_get_positive_check(self):
        hyp=self.thing("Hypothesis","Toy outdated")
        change_status(self.root,hyp["id"],"impact_status","needs-review","Changed prerequisite",actor="agent")
        r=mentor_brief(load(self.root))
        self.assertIn("DEPENDENCY_NEEDS_REVIEW",{g["code"] for g in r["pending_gaps"]})
        self.assertNotIn(hyp["id"],{o["subject_id"] for o in r["proposed_next_checks"]})
    def test_report_generation_escapes_html(self):
        self.thing("Hypothesis",'<script>alert("x")</script>')
        src=build_decision(self.root)
        txt=src.read_text(encoding="utf-8")
        self.assertIn("rn-decision",txt)
        self.assertIn("\\u003cscript\\u003e",txt)
        self.assertNotIn('<script>alert("x")</script>',txt)
        self.assertIn("READ ONLY",txt)
    def test_canvas_offline_link_and_no_state_write(self):
        a=self.thing("Hypothesis","Canvas decision example")
        rev=load(self.root)["project"]["revision"]
        dest=build_canvas(self.root)
        self.assertTrue((dest.parent/"decisions.html").exists())
        self.assertIn('href="decisions.html"',dest.read_text(encoding="utf-8"))
        self.assertEqual(load(self.root)["project"]["revision"],rev)
    def test_bad_cost_rejected(self):
        with self.assertRaises(ResearchError):
            opportunities(load(self.root),"75% likely")
    def test_brief_markdown_has_no_false_approval(self):
        self.thing("Hypothesis")
        t=markdown_brief(summarize(self.root))
        self.assertIn("未获执行许可",t)
        self.assertIn("科学结论",t)
    def test_no_implicit_human_approval(self):
        hyp=self.thing("Hypothesis")
        s=load(self.root)
        self.assertEqual(s["items"][0]["review_status"],"needs-user-confirmation")
        opportunities(s)
        self.assertEqual(load(self.root)["items"][0]["review_status"],"needs-user-confirmation")

if __name__=="__main__":
    unittest.main()
