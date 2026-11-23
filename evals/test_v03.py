"""v0.3 synthetic scientific-reasoning regression suite.

Never treat fixtures as real academic observations.
"""
import json
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from rn_core import (ResearchError, add_item, add_relation, add_source,
                     change_status, init_project, load, paths, validate_state)
from rn_domain import link_evidence, create_branch
from rn_reasoning import (create_run, record_run, invalidate_run, analyze_claim,
                          create_decision_trace, replay_decision)
from graph_projection import project_graph


class ResearchReasoningV03(unittest.TestCase):
    def setUp(self):
        self.workspace = tempfile.TemporaryDirectory()
        self.root = Path(self.workspace.name) / "research"
        init_project(self.root, "SYNTHETIC FIXTURE: reasoning", "Mock research question")
        self.exp = add_item(self.root,kind="Experiment",title="Synthetic protocol A",
                            module="experiment",actor="user")
        self.claim = add_item(self.root,kind="Claim",title="Synthetic claim",
                              module="synthesis")
        self.baseline = add_item(self.root,kind="Baseline",title="Shared baseline",
                                 module="literature")

    def tearDown(self):
        self.workspace.cleanup()

    def plan(self,attempt=1):
        return create_run(self.root,self.exp["id"],"Fixture run",attempt)

    def recorded(self,attempt=1):
        planned=self.plan(attempt)
        path=self.root / "research" / "03-experiments" / ("run-%d.log" % attempt)
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text("SYNTHETIC FIXTURE: no real experiment; 0.62 example\n",encoding="utf-8")
        result=record_run(self.root,planned["id"],
                           dataset="synthetic sample v1",
                           protocol="synthetic protocol v1",
                           code_revision="fake-test-commit-id",
                           seed=42,
                           artifact_path=str(path.relative_to(self.root)),
                           observation="Illustrative metric only",
                           outcome="negative",
                           metrics=[{"name":"F1","value":0.62,"unit":"ratio","direction":"higher"}],
                           started_at="2026-11-23T01:00:00Z",
                           ended_at="2026-11-23T01:01:00Z",
                           synthetic=True)
        return result

    def test_planned_run_carries_no_observed_result(self):
        run=self.plan()
        self.assertEqual(run["run"]["status"],"planned")
        self.assertIsNone(run["run"]["result_id"])
        self.assertEqual(run["epistemic_status"],"uncertain")
        self.assertEqual(validate_state(load(self.root)),[])

    def test_duplicate_attempt_rejected(self):
        self.plan()
        with self.assertRaises(ResearchError):self.plan()
        self.assertEqual(sum(x["type"]=="ExperimentRun" for x in load(self.root)["items"]),1)

    def test_record_requires_existing_artifact(self):
        run=self.plan()
        with self.assertRaises(ResearchError):
            record_run(self.root,run["id"],dataset="toy",protocol="v1",
                       code_revision="fake",seed=1,artifact_path="does-not-exist.log",
                       observation="badly claimed",outcome="positive",metrics=[],
                       started_at="start",ended_at="end",synthetic=True)
        self.assertEqual(next(x for x in load(self.root)["items"] if x["id"]==run["id"])["run"]["status"],"planned")

    def test_recorded_run_observation_and_provenance(self):
        pair=self.recorded()
        run,result=pair["run"],pair["result"]
        self.assertEqual(run["run"]["status"],"recorded")
        self.assertEqual(run["run"]["result_id"],result["id"])
        self.assertTrue(run["run"]["artifact_verified"])
        self.assertEqual(run["review_status"],"needs-user-confirmation")
        self.assertEqual(run["epistemic_status"],"uncertain")
        self.assertEqual(result["outcome"],"negative")
        self.assertIn("SYNTHETIC FIXTURE",result["observation"])
        self.assertEqual(run["lifecycle_status"],"active")
        self.assertEqual(validate_state(load(self.root)),[])

    def test_bad_metric_has_no_side_effect(self):
        run=self.plan()
        path=self.root/"test.log";path.write_text("SYNTHETIC FIXTURE")
        with self.assertRaises(ResearchError):
            record_run(self.root,run["id"],dataset="toy",protocol="v1",
                       code_revision="fake",seed=1,artifact_path="test.log",
                       observation="toy",outcome="negative",
                       metrics=[{"name":"F1","value":"good","unit":"ratio","direction":"higher"}],
                       started_at="start",ended_at="end",synthetic=True)
        self.assertEqual(sum(x["type"]=="Result" for x in load(self.root)["items"]),0)

    def test_path_traversal_rejected(self):
        run=self.plan()
        outside=Path(self.workspace.name)/"outside.log";outside.write_text("SYNTHETIC")
        with self.assertRaises(ResearchError):
            record_run(self.root,run["id"],dataset="toy",protocol="v1",
                       code_revision="fake",seed=1,artifact_path="../outside.log",
                       observation="toy",outcome="inconclusive",metrics=[],
                       started_at="start",ended_at="end",synthetic=True)

    def test_optimistic_revision_guard(self):
        rev=load(self.root)["project"]["revision"]
        self.plan()
        with self.assertRaises(ResearchError):
            create_run(self.root,self.exp["id"],"stale",2,expected_revision=rev)

    def test_claim_conflict_explicit_not_auto_proof(self):
        a=add_item(self.root,kind="Result",title="Toy A",module="experiment",
                   observation="fixture A",artifact_path="mock-a.log")
        b=add_item(self.root,kind="Result",title="Toy B",module="experiment",
                   observation="fixture B",artifact_path="mock-b.log")
        link_evidence(self.root,self.claim["id"],a["id"],"supports","toy split A",
                      quality="unverified")
        link_evidence(self.root,self.claim["id"],b["id"],"contradicts","toy split B",
                      quality="unverified")
        report=analyze_claim(self.root,self.claim["id"])
        self.assertTrue(report["possible_conflict"])
        self.assertEqual(report["epistemic_status"],"uncertain")
        self.assertIn("scopes",report["conflict_warning"])

    def test_invalidation_preserves_outcome_and_blocks_downstream(self):
        pair=self.recorded()
        result=pair["result"];run=pair["run"]
        downstream=add_item(self.root,kind="Task",title="Dependent draft",module="synthesis")
        add_relation(self.root,downstream["id"],self.claim["id"],"depends-on")
        link_evidence(self.root,self.claim["id"],result["id"],"supports",
                      "synthetic split",quality="experiment-observed")
        out=invalidate_run(self.root,run["id"],"test fixture evaluation leakage")
        self.assertEqual(out["run"]["run"]["status"],"invalidated")
        state=load(self.root);by={x["id"]:x for x in state["items"]}
        self.assertEqual(by[result["id"]]["outcome"],"negative")
        self.assertEqual(by[result["id"]]["impact_status"],"blocked")
        self.assertEqual(by[self.claim["id"]]["impact_status"],"blocked")
        self.assertEqual(by[self.baseline["id"]]["impact_status"],"current")
        self.assertTrue(analyze_claim(self.root,self.claim["id"])["evidence"][0]["invalidated_or_blocked"])

    def test_decision_trace_replays_only_real_events(self):
        decision=add_item(self.root,kind="Decision",title="Compare alternatives",
                          module="pivot")
        events=load(self.root)["events"]
        first=events[0]["event_id"]
        trace=create_decision_trace(self.root,decision_id=decision["id"],
                                    title="Decision context",scope="synthetic route",
                                    options=["test A","test B"],selected="test B",
                                    rationale="Lower toy cost",
                                    event_ids=[first],claim_ids=[self.claim["id"]])
        result=replay_decision(self.root,trace["id"])
        self.assertEqual(result["events"][0]["event_id"],first)
        self.assertEqual(result["claim_ids"],[self.claim["id"]])
        self.assertIn("NOT reconstructed",result["warning"])
        self.assertEqual(trace["review_status"],"needs-user-confirmation")

    def test_trace_does_not_fabricate_missing_event(self):
        decision=add_item(self.root,kind="Decision",title="Choose baseline",module="pivot")
        with self.assertRaises(ResearchError):
            create_decision_trace(self.root,decision_id=decision["id"],
                                  title="Bad trace",scope="toy",options=["A"],
                                  selected="A",rationale="unknown",
                                  event_ids=["nonexistent-event"])

    def test_documented_trace_requires_explicit_selected_option(self):
        decision=add_item(self.root,kind="Decision",title="Choose baseline",module="pivot")
        with self.assertRaises(ResearchError):
            create_decision_trace(self.root,decision_id=decision["id"],
                                  title="Bad trace",scope="toy",options=["A","B"],
                                  selected="C",rationale="unsupported choice")

    def test_reasoning_projection_end_to_end(self):
        pair=self.recorded()
        decision=add_item(self.root,kind="Decision",title="Review negative result",
                          module="pivot")
        trace=create_decision_trace(self.root,decision_id=decision["id"],
                                    title="Decision trace",scope="synthetic only",
                                    options=["park","rerun"],selected="rerun",
                                    rationale="Low power test",run_ids=[pair["run"]["id"]],
                                    claim_ids=[self.claim["id"]])
        state=load(self.root)
        before=json.dumps(state,sort_keys=True)
        graph=project_graph(state,view="reasoning",limit=None)
        after=json.dumps(state,sort_keys=True)
        self.assertEqual(before,after)
        nodes={x["id"]:x for x in graph["nodes"]}
        self.assertIn("item:"+pair["run"]["id"],nodes)
        self.assertIn("item:"+trace["id"],nodes)
        self.assertFalse(nodes["item:"+trace["id"]]["actionable"])
        self.assertTrue(any(e["type"]=="produced-result" for e in graph["edges"]))
        self.assertTrue(any(e["type"]=="reviewed-run" for e in graph["edges"]))
        self.assertEqual(validate_state(state),[])

    def test_original_milestone_and_baseline_unaffected(self):
        pair=self.recorded()
        invalidate_run(self.root,pair["run"]["id"],"toy evaluation issue")
        state=load(self.root)
        self.assertEqual(next(x for x in state["items"] if x["id"]==self.baseline["id"])["impact_status"],"current")

    def test_schema_rejects_fabricated_record(self):
        pair=self.recorded()
        state=load(self.root)
        row=next(x for x in state["items"] if x["id"]==pair["run"]["id"])
        row["run"]["artifact_sha256"]=""
        self.assertTrue(any("artifact_sha256" in x for x in validate_state(state)))


    def test_archived_branch_rejects_new_run_but_does_not_archive_shared_baseline(self):
        branch_a=create_branch(self.root,"Route A","Toy A",["Stop if invalid"])
        branch_b=create_branch(self.root,"Route B","Toy B",["Stop if invalid"])
        add_relation(self.root,self.exp["id"],branch_a["id"],"member-of")
        add_relation(self.root,self.baseline["id"],branch_a["id"],"member-of")
        add_relation(self.root,self.baseline["id"],branch_b["id"],"member-of")
        change_status(self.root,branch_a["id"],"lifecycle_status","parked",
                      "user parks weak route",actor="user",failure_scope="toy A only",
                      revival_triggers="new independent data")
        before=load(self.root)
        with self.assertRaisesRegex(ResearchError,"archived or review-blocked ResearchBranch"):
            create_run(self.root,self.exp["id"],"forbidden",1)
        self.assertEqual(load(self.root),before)
        state=load(self.root)
        by={x["id"]:x for x in state["items"]}
        self.assertEqual(by[self.baseline["id"]]["impact_status"],"current")
        self.assertEqual(by[branch_b["id"]]["lifecycle_status"],"active")

    def test_run_planned_before_branch_park_cannot_be_recorded_after(self):
        branch=create_branch(self.root,"Route A","Toy",["Stop if invalid"])
        add_relation(self.root,self.exp["id"],branch["id"],"member-of")
        run=create_run(self.root,self.exp["id"],"planned before archive",1)
        logfile=self.root/"toy.log";logfile.write_text("SYNTHETIC FIXTURE",encoding="utf-8")
        change_status(self.root,branch["id"],"lifecycle_status","parked",
                      "user parks route",actor="user",failure_scope="toy only",
                      revival_triggers="new data")
        before=load(self.root)
        with self.assertRaisesRegex(ResearchError,"archived or review-blocked ResearchBranch"):
            record_run(self.root,run["id"],dataset="toy",protocol="toy",code_revision="synthetic",
                       seed=7,artifact_path="toy.log",observation="toy only",
                       outcome="inconclusive",metrics=[],
                       started_at="2026-11-23T08:00:00+08:00",
                       ended_at="2026-11-23T08:01:00+08:00",synthetic=True)
        self.assertEqual(load(self.root),before)
        self.assertEqual(load(self.root)["project"]["schema_version"],"0.2.0")

    def test_nested_branch_park_blocks_run_without_affecting_others(self):
        outer=create_branch(self.root,"Nested outer","Outer",["Stop"])
        inner=create_branch(self.root,"Nested inner","Inner",["Stop"])
        add_relation(self.root,inner["id"],outer["id"],"member-of")
        add_relation(self.root,self.exp["id"],inner["id"],"member-of")
        planned=create_run(self.root,self.exp["id"],"allowed when active",1)
        self.assertEqual(planned["run"]["status"],"planned")
        change_status(self.root,outer["id"],"lifecycle_status","quarantined",
                      "user quarantines parent",actor="user",failure_scope="parent conditions",
                      revival_triggers="independent review")
        with self.assertRaisesRegex(ResearchError,"archived or review-blocked ResearchBranch"):
            create_run(self.root,self.exp["id"],"blocked",2)


if __name__=="__main__":
    unittest.main()
