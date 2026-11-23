"""Issue #10: proposal preview + guarded semantic commit, synthetic data only."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from rn_core import (ResearchError, add_item, add_relation, add_source,
                     change_status, init_project, load)
from rn_domain import create_branch, create_milestone
from rn_proposals import (preview_proposal, queue_proposal, approve_proposal,
                          proposal_status, inspect_proposal)


class CanvasSemanticsTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        init_project(self.root,"Synthetic #10 project")
    def tearDown(self):self.tmp.cleanup()

    def data(self,op,params,revision=None):
        return {"operation":op,"params":params,
                "reason":"Human reviews the scientific rationale",
                "expected_revision":(load(self.root)["project"]["revision"]
                                     if revision is None else revision)}

    def approve(self,op,params):
        payload=self.data(op,params)
        before=load(self.root)
        preview=preview_proposal(self.root,payload)
        self.assertEqual(load(self.root),before,"preview must never write")
        self.assertFalse(preview["accepted"])
        self.assertFalse(preview["scientifically_validated"])
        self.assertTrue(preview["requires_terminal_approval"])
        queued=queue_proposal(self.root,payload)
        self.assertEqual(load(self.root),before,"queue must never write")
        self.assertEqual(proposal_status(self.root,queued["proposal_id"])["status"],"pending")
        done=approve_proposal(self.root,queued["proposal_id"],confirmed=True)
        self.assertEqual(done["status"],"applied")
        after=load(self.root)
        self.assertEqual(after["project"]["revision"],before["project"]["revision"]+1)
        self.assertTrue(any(e.get("proposal_id")==queued["proposal_id"] for e in after["events"]))
        self.assertEqual(proposal_status(self.root,queued["proposal_id"])["status"],"applied")
        with self.assertRaises(ResearchError):
            approve_proposal(self.root,queued["proposal_id"],confirmed=True)
        return done["result"]

    def test_create_branch_and_share_one_baseline(self):
        baseline=add_item(self.root,kind="Baseline",title="Shared synthetic baseline",module="literature")
        branches=[]
        for name in ("A","B","C"):
            row=self.approve("add-branch",{"title":"Branch "+name,"goal":"Explore "+name,
                        "stop_conditions":["No robust improvement"],"module":"topic"})
            branches.append(row["id"])
        for branch in branches:
            self.approve("add-relation",{"source":baseline["id"],"target":branch,"relation":"member-of"})
        state=load(self.root)
        self.assertEqual(len([x for x in state["items"] if x["type"]=="Baseline"]),1)
        self.assertEqual(len([x for x in state["relations"] if x["type"]=="member-of"]),3)
        for b in branches:
            self.assertEqual(next(i for i in state["items"] if i["id"]==b)["review_status"],"needs-user-confirmation")

    def test_milestone_criterion_provenance_and_task(self):
        m=self.approve("add-milestone",{"title":"Synthetic milestone",
                  "criteria":["Baseline reproducible","Evidence sufficient"],"module":"experiment"})
        milestone_id=m["id"]
        before=load(self.root)
        self.approve("revise-criterion",{"milestone_id":milestone_id,
                     "criterion_id":"C-001","text":"Baseline validated in controlled synthetic setting"})
        mile=next(x for x in load(self.root)["items"] if x["id"]==milestone_id)
        self.assertFalse(mile["milestone"]["criteria"][0]["reviewed"])
        self.assertEqual(mile["impact_status"],"needs-review")
        result=add_item(self.root,kind="Result",title="Synthetic measured result",
                        module="experiment",observation="Toy observation",
                        artifact_path="synthetic.log")
        self.approve("attach-milestone-evidence",{"milestone_id":milestone_id,
                    "criterion_id":"C-001","evidence_id":result["id"]})
        mile=next(x for x in load(self.root)["items"] if x["id"]==milestone_id)
        self.assertEqual(mile["milestone"]["criteria"][0]["evidence_refs"],[result["id"]])
        task=self.approve("add-item",{"type":"Task","title":"Run fair synthetic experiment",
                        "module":"experiment","next_action":"Inspect synthetic baseline"})
        self.assertEqual(task["type"],"Task")
        self.assertNotEqual(load(self.root)["items"][-1]["epistemic_status"],"experimentally-supported")

    def test_claim_evidence_and_unlink_relation(self):
        claim=add_item(self.root,kind="Claim",title="Synthetic claim",module="synthesis")
        paper=add_source(self.root,title="Unverified synthetic paper",url="https://example.org/paper")
        link=self.approve("link-evidence",{"claim_id":claim["id"],
                 "evidence_id":paper["id"],"stance":"qualifies",
                 "scope":"Only described toy configuration","locator":"Abstract",
                 "quality":"unverified"})
        self.assertTrue(link["id"].startswith("EVL-"))
        self.assertEqual(load(self.root)["items"][0]["epistemic_status"],"uncertain")
        idea=add_item(self.root,kind="Idea",title="Candidate",module="topic")
        self.approve("add-relation",{"source":idea["id"],"target":claim["id"],"relation":"depends-on"})
        self.assertIn(claim["id"],next(i for i in load(self.root)["items"]
                      if i["id"]==idea["id"])["depends_on"])
        self.approve("unlink-relation",{"source":idea["id"],"target":claim["id"],"relation":"depends-on"})
        self.assertNotIn(claim["id"],next(i for i in load(self.root)["items"]
                          if i["id"]==idea["id"])["depends_on"])

    def test_contradictory_evidence_flags_claim(self):
        claim=add_item(self.root,kind="Claim",title="Synthetic claim",module="synthesis")
        src=add_source(self.root,title="Synthetic source",url="https://example.org/synth")
        self.approve("link-evidence",{"claim_id":claim["id"],"evidence_id":src["id"],
                  "stance":"contradicts","scope":"Toy negative result","quality":"unverified"})
        obj=next(x for x in load(self.root)["items"] if x["id"]==claim["id"])
        self.assertEqual(obj["impact_status"],"needs-review")
        self.assertEqual(obj["epistemic_status"],"uncertain")

    def test_stale_two_proposals_one_approval(self):
        rev=load(self.root)["project"]["revision"]
        a=queue_proposal(self.root,self.data("add-item",
                 {"type":"Idea","title":"Idea A","module":"topic"},rev))
        b=queue_proposal(self.root,self.data("add-item",
                 {"type":"Idea","title":"Idea B","module":"topic"},rev))
        approve_proposal(self.root,a["proposal_id"],confirmed=True)
        state=load(self.root)
        with self.assertRaisesRegex(ResearchError,"stale"):
            approve_proposal(self.root,b["proposal_id"],confirmed=True)
        self.assertEqual(load(self.root),state)
        with self.assertRaisesRegex(ResearchError,"stale"):
            preview_proposal(self.root,self.data("add-item",
                 {"type":"Idea","title":"Stale","module":"topic"},rev))

    def test_forbidden_archive_promotion_and_fabricated_evidence(self):
        idea=add_item(self.root,kind="Idea",title="Archived",module="topic")
        change_status(self.root,idea["id"],"lifecycle_status","parked",
                      "Human approved archive",actor="user",
                      failure_scope="Toy experiment",revival_triggers="New data")
        branch=create_branch(self.root,"Active route","Synthetic evaluation",["Stop"])
        before=load(self.root)
        for data in (
            self.data("set-status",{"item_id":idea["id"],"field":"outcome","value":"positive"}),
            self.data("add-relation",{"source":idea["id"],"target":branch["id"],"relation":"member-of"}),
            self.data("add-relation",{"source":branch["id"],"target":idea["id"],"relation":"revives"}),
            self.data("add-item",{"type":"Idea","title":"Fake","module":"topic","review_status":"user-confirmed"}),
        ):
            with self.subTest(op=data["operation"]):
                with self.assertRaises(ResearchError):
                    queue_proposal(self.root,data)
        self.assertEqual(load(self.root),before)

    def test_accepted_milestone_criterion_protected(self):
        milestone=create_milestone(self.root,"M",["Proof"])
        state=load(self.root)
        # Directly forbid editing accepted milestone without a new human review.
        # Validator still requires accepted Milestone review/approval metadata.
        from rn_core import workspace_lock,write
        with workspace_lock(self.root):
            st=load(self.root)
            item=next(i for i in st["items"] if i["id"]==milestone["id"])
            item["milestone"]["accepted"]=True
            item["milestone"]["approval_note"]="Synthetic human sign-off"
            item["review_status"]="user-confirmed"
            write(self.root,st,[{"action":"synthetic-test-setup","actor":"tool","reason":"fixture"}])
        with self.assertRaisesRegex(ResearchError,"accepted Milestone"):
            queue_proposal(self.root,self.data("revise-criterion",
                     {"milestone_id":milestone["id"],"criterion_id":"C-001","text":"New criteria"}))


if __name__=="__main__":unittest.main()
