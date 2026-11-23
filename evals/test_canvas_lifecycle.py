"""Regression #11: separate authorizations, safe archives, scientific history."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from rn_core import (init_project,add_item,add_relation,load,query,ResearchError,
                     change_status)
from rn_domain import create_branch,create_milestone
from rn_proposals import preview_proposal,queue_proposal,approve_proposal
from graph_projection import project_graph

class ArchiveCanvasTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        init_project(self.root,"Synthetic archived research")
        self.base=add_item(self.root,kind="Baseline",title="Shared control",module="literature")
        self.idea=add_item(self.root,kind="Idea",title="Weak experiment concept",module="topic")
        self.result=add_item(self.root,kind="Result",title="Synthetic weak negative",
                             module="experiment",observation="Synthetic metric 0.51 vs 0.50",
                             artifact_path="synthetic/weak.txt")
        self.branches=[create_branch(self.root,"Path "+v,"Hypothesis "+v,["No fair improvement"])
                       for v in ("A","B","C")]
        self.mile=create_milestone(self.root,"Evidence milestone",["Fair baseline exists"])
        for branch in self.branches:
            add_relation(self.root,self.base["id"],branch["id"],"member-of")
        add_relation(self.root,self.idea["id"],self.branches[0]["id"],"member-of")
        add_relation(self.root,self.branches[0]["id"],self.mile["id"],"contributes-to")
    def tearDown(self):self.tmp.cleanup()
    def payload(self,op,args):
        return {"operation":op,"params":args,"reason":"Human assesses synthetic negative result",
                "expected_revision":load(self.root)["project"]["revision"]}
    def approve(self,op,args):
        p=self.payload(op,args)
        previous=load(self.root)
        preview=preview_proposal(self.root,p)
        self.assertEqual(load(self.root),previous)
        self.assertFalse(preview["accepted"])
        ref=queue_proposal(self.root,p)["proposal_id"]
        self.assertEqual(load(self.root),previous)
        approve_proposal(self.root,ref,confirmed=True)
        self.assertTrue(any(e.get("proposal_id")==ref for e in load(self.root)["events"]))
        return ref
    def test_two_phases_original_negative_unchanged(self):
        original_result=next(x for x in load(self.root)["items"] if x["id"]==self.result["id"])
        self.approve("archive-route",{"item_id":self.idea["id"],"lifecycle":"parked",
           "failure_category":"evaluation","failure_scope":"Toy results only",
           "confidence":"uncertain","revival_triggers":"New reproducible larger data",
           "evidence_refs":[self.result["id"]]})
        state=load(self.root); archived=next(i for i in state["items"] if i["id"]==self.idea["id"])
        self.assertEqual(archived["lifecycle_status"],"parked")
        self.assertNotIn(self.idea["id"],[i["item_id"] for i in query(state,"planning")])
        self.assertIn(self.idea["id"],[i["item_id"] for i in query(state,"risk-check")])
        # merely reading archive cards does not authorize revival
        graph=project_graph(state,limit=None)
        item=next(n for n in graph["nodes"] if n["entity_id"]==self.idea["id"])
        self.assertEqual(item["metadata"]["archive"]["failure_scope"],"Toy results only")
        self.assertTrue(item["metadata"]["decision_history"])
        self.assertEqual(load(self.root),state)
        with self.assertRaises(ResearchError):
            queue_proposal(self.root,self.payload("approve-revival-candidate",
                {"item_id":self.idea["id"],"title":"Illegal candidate",
                 "new_conditions":"New data","approval_note":"Second approval"}))
        self.approve("begin-revival-review",{"item_id":self.idea["id"],
            "question":"Does a new sample change the result?",
            "new_conditions":"Use independent larger data"})
        mid=load(self.root)
        self.assertEqual(next(i for i in mid["items"] if i["id"]==self.idea["id"])["lifecycle_status"],
                         "under-revival-review")
        self.approve("approve-revival-candidate",{"item_id":self.idea["id"],
            "title":"Candidate v2 under new conditions",
            "new_conditions":"Independent reproducible larger data",
            "approval_note":"Second human confirmation after inspecting failure"})
        after=load(self.root)
        original=next(i for i in after["items"] if i["id"]==self.idea["id"])
        self.assertEqual(original["lifecycle_status"],"parked")
        self.assertEqual(original["archive"]["failure_scope"],"Toy results only")
        self.assertEqual(next(i for i in after["items"] if i["id"]==self.result["id"]),original_result)
        candidates=[i for i in after["items"] if i.get("derived_from")==self.idea["id"]]
        self.assertEqual(len(candidates),1)
        self.assertEqual(candidates[0]["epistemic_status"],"hypothesis")
        self.assertEqual(candidates[0]["review_status"],"needs-user-confirmation")
        self.assertEqual({r["type"] for r in after["relations"] if r["from"]==candidates[0]["id"]},
                         {"derived-from","revives"})
        m=next(i for i in after["items"] if i["id"]==self.mile["id"])
        self.assertEqual(m["impact_status"],"needs-review")
        self.assertEqual(next(i for i in after["items"] if i["id"]==self.base["id"])["lifecycle_status"],"active")
        self.assertEqual(next(i for i in after["items"] if i["id"]==self.branches[1]["id"])["impact_status"],"current")
    def test_revival_of_branch_requires_fresh_goal_and_stop_conditions(self):
        branch = self.branches[0]
        previous_metadata = next(i for i in load(self.root)["items"]
                                 if i["id"] == branch["id"])["branch"]
        baseline_before = next(i for i in load(self.root)["items"]
                               if i["id"] == self.base["id"])
        self.approve("archive-route", {"item_id": branch["id"],
            "lifecycle": "parked", "failure_scope": "Weak synthetic baseline",
            "revival_triggers": "New independent data"})
        self.approve("begin-revival-review", {
            "item_id": branch["id"], "question": "Can a new independent dataset help?",
            "new_conditions": "Different data distribution"})
        old = load(self.root)
        args = {"item_id": branch["id"], "title": "New Branch A v2",
                "new_conditions": "Fresh independent dataset",
                "approval_note": "Second deliberate authorization"}
        for invalid in (args, {**args, "goal": "New objective"},
                        {**args, "goal": "New objective", "stop_conditions": []},
                        {**args, "goal": " ", "stop_conditions": ["Stop if invalid"]}):
            with self.subTest(invalid=invalid), self.assertRaises(ResearchError):
                queue_proposal(self.root, self.payload("approve-revival-candidate", invalid))
            self.assertEqual(load(self.root), old)
        new_goal = "Independently check the next route"
        new_stops = ["No reproducible gain over new control"]
        self.approve("approve-revival-candidate", {
            **args, "goal": new_goal, "stop_conditions": new_stops})
        current = load(self.root)
        parent = next(i for i in current["items"] if i["id"] == branch["id"])
        candidate = next(i for i in current["items"] if
                         i.get("derived_from") == branch["id"])
        self.assertEqual(parent["lifecycle_status"], "parked")
        self.assertEqual(parent["branch"], previous_metadata)
        self.assertEqual(candidate["type"], "ResearchBranch")
        self.assertEqual(candidate["branch"]["goal"], new_goal)
        self.assertEqual(candidate["branch"]["stop_conditions"], new_stops)
        self.assertEqual(candidate["epistemic_status"], "hypothesis")
        self.assertEqual(candidate["review_status"], "needs-user-confirmation")
        self.assertEqual(next(i for i in current["items"]
                              if i["id"] == self.base["id"]), baseline_before)
        self.assertEqual(next(i for i in current["items"]
                              if i["id"] == self.mile["id"])["impact_status"], "needs-review")

    def test_cancel_review_and_reject_invalid_tombstone(self):
        before=load(self.root)
        with self.assertRaises(ResearchError):
            queue_proposal(self.root,self.payload("archive-route",{"item_id":self.idea["id"],
                "lifecycle":"parked","failure_scope":"","revival_triggers":""}))
        self.assertEqual(load(self.root),before)
        self.approve("archive-route",{"item_id":self.idea["id"],"lifecycle":"quarantined",
            "failure_scope":"Toy only","revival_triggers":"Changed assumptions"})
        self.approve("begin-revival-review",{"item_id":self.idea["id"],
            "question":"What changed?","new_conditions":"New data"})
        self.approve("reject-revival-review",{"item_id":self.idea["id"],
            "decision_note":"No new independent evidence"})
        result=next(i for i in load(self.root)["items"] if i["id"]==self.idea["id"])
        self.assertEqual(result["lifecycle_status"],"quarantined")
        self.assertIsNone(result["revival"])
        self.assertTrue(any(e["action"]=="revival-review-rejected" for e in load(self.root)["events"]))

if __name__=="__main__":unittest.main()
