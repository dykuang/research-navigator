"""Regression and integration tests for issues #2-#5. Synthetic data ONLY."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from rn_core import (ResearchError, add_item, add_relation, add_source, change_status,
                     init_project, load, paths, project_summary, query, read_json,
                     atomic_json, validate_state, workspace_lock, write)
from migrate_state import preview, apply, recover
from rn_domain import (accept_milestone, attach_milestone_evidence, claim_evidence,
                       create_branch, create_milestone, create_session, link_evidence,
                       session_entity_link)


class SchemaV02Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "project"
        init_project(self.root, "SYNTHETIC fixture", "Synthetic question")
    def tearDown(self):
        self.temp.cleanup()

    def _legacy(self):
        p = paths(self.root)
        project = read_json(p["project"])
        project["schema_version"] = "0.1.0"
        atomic_json(p["project"], project)
        for key in ("session_refs", "evidence_links"):
            p[key].unlink()

    def test_02_01_new_projects_are_schema_v02(self):
        s = load(self.root)
        self.assertEqual(s["project"]["schema_version"], "0.2.0")
        self.assertEqual(validate_state(s), [])
        self.assertTrue(paths(self.root)["session_refs"].exists())

    def test_02_02_legacy_preview_does_not_mutate(self):
        self._legacy()
        p = paths(self.root)
        before = {k:p[k].read_bytes() for k in ("project","items","events")}
        report = preview(self.root)
        self.assertTrue(report["needs_migration"])
        self.assertEqual(report["sidecars_to_create"],["session_refs","evidence_links"])
        self.assertEqual(before,{k:p[k].read_bytes() for k in before})

    def test_02_03_migration_backup_idempotency_and_event(self):
        i=add_item(self.root,kind="Idea",title="Synthetic failed hypothesis",module="topic")
        change_status(self.root,i["id"],"lifecycle_status","parked","synthetic weak result",
                      actor="user",failure_scope="tiny sample",revival_triggers="more data")
        old=load(self.root)
        self._legacy()
        result=apply(self.root)
        self.assertEqual(result["status"],"migrated")
        migrated=load(self.root)
        self.assertEqual(migrated["project"]["schema_version"],"0.2.0")
        self.assertEqual(migrated["items"],old["items"])
        self.assertEqual(migrated["relations"],old["relations"])
        self.assertEqual(migrated["sources"],old["sources"])
        self.assertEqual(migrated["events"][:-1],old["events"])
        self.assertEqual(migrated["events"][-1]["action"],"schema-migrated")
        with zipfile.ZipFile(result["backup"]) as z:
            self.assertIsNone(z.testzip())
            self.assertIn("research/state/items.json",z.namelist())
        again=apply(self.root)
        self.assertEqual(again["status"],"already-current")
        self.assertEqual(load(self.root), migrated)

    def test_02_04_legacy_write_requires_explicit_migration(self):
        self._legacy()
        with self.assertRaisesRegex(ResearchError,"migrate_state"):
            add_item(self.root,kind="Idea",title="not allowed until migration",module="topic")
        apply(self.root)
        self.assertEqual(add_item(self.root,kind="Idea",title="allowed",module="topic")["id"],"IDEA-0001")

    def test_02_05_revision_conflict_rejected(self):
        s=load(self.root)
        rev=s["project"]["revision"]
        add_item(self.root,kind="Idea",title="another writer",module="topic")
        with workspace_lock(self.root):
            with self.assertRaisesRegex(ResearchError,"stale"):
                write(self.root,s,[],expected_revision=rev)
        self.assertEqual(load(self.root)["project"]["revision"],rev+1)

    def test_02_06_pending_journal_blocks_read_and_can_rollback(self):
        p=paths(self.root)
        before={k: p[k].read_text(encoding="utf-8") if p[k].exists() else None
                for k in ("project","items","relations","sources","session_refs","evidence_links","events")}
        atomic_json(p["journal"],{"project_id":read_json(p["project"])["project_id"],
                                  "revision":0,"before":before})
        atomic_json(p["items"],{"items":[{"id":"BROKEN"}]})
        with self.assertRaisesRegex(ResearchError,"recover"):
            load(self.root)
        self.assertEqual(recover(self.root)["status"],"rolled-back")
        self.assertEqual(validate_state(load(self.root)),[])
        self.assertEqual(p["items"].read_text(encoding="utf-8"),before["items"])

    def test_02_07_reject_dependency_cycles(self):
        a=add_item(self.root,kind="Idea",title="A",module="topic")
        b=add_item(self.root,kind="Idea",title="B",module="topic")
        add_relation(self.root,a["id"],b["id"],"depends-on")
        with self.assertRaises(ResearchError):
            add_relation(self.root,b["id"],a["id"],"depends-on")

    def test_03_01_multiple_branches_share_baseline(self):
        base=add_item(self.root,kind="Baseline",title="Shared baseline",module="literature")
        a=create_branch(self.root,"Branch A","Improve transfer",["No robust gain"])
        b=create_branch(self.root,"Branch B","Improve calibration",["Budget exceeded"])
        c=create_branch(self.root,"Branch C","Investigate alignment",["Data unavailable"])
        for branch in (a,b,c):
            add_relation(self.root,base["id"],branch["id"],"member-of")
        s=load(self.root)
        self.assertEqual(len([i for i in s["items"] if i["type"]=="Baseline"]),1)
        self.assertEqual(len([r for r in s["relations"] if r["type"]=="member-of"]),3)

    def test_03_02_archive_flags_dependents_and_milestone_not_baseline(self):
        base=add_item(self.root,kind="Baseline",title="Shared",module="literature")
        idea=add_item(self.root,kind="Idea",title="Idea A",module="topic")
        branch=create_branch(self.root,"Branch A","Evaluate A",["No evidence"])
        mile=create_milestone(self.root,"Scientific milestone",["Fair comparison"])
        add_relation(self.root,idea["id"],branch["id"],"member-of")
        add_relation(self.root,branch["id"],mile["id"],"contributes-to")
        add_relation(self.root,base["id"],branch["id"],"member-of")
        change_status(self.root,idea["id"],"lifecycle_status","parked","synthetic negative",
                      actor="user",failure_scope="toy benchmark",revival_triggers="new data")
        s={i["id"]:i for i in load(self.root)["items"]}
        self.assertEqual(s[branch["id"]]["impact_status"],"needs-review")
        self.assertEqual(s[mile["id"]]["impact_status"],"needs-review")
        self.assertEqual(s[base["id"]]["impact_status"],"current")
        self.assertEqual(s[base["id"]]["lifecycle_status"],"active")

    def test_03_03_milestone_requires_evidence_and_human(self):
        mile=create_milestone(self.root,"Review data",["Experiments logged"])
        with self.assertRaises(ResearchError):
            accept_milestone(self.root,mile["id"],"premature",actor="user")
        result=add_item(self.root,kind="Result",title="SYNTHETIC numbers",module="experiment",
                       observation="toy only",artifact_path="toy.log")
        attach_milestone_evidence(self.root,mile["id"],"C-001",result["id"])
        with self.assertRaises(ResearchError):
            accept_milestone(self.root,mile["id"],"agent self approval",actor="agent")
        approved=accept_milestone(self.root,mile["id"],"Human reviewed toy log",actor="mentor")
        self.assertTrue(approved["milestone"]["accepted"])
        self.assertEqual(approved["epistemic_status"],"uncertain")
        self.assertEqual(approved["workflow_status"],"done")

    def test_03_04_typed_links_validate_target(self):
        b=create_branch(self.root,"A","Goal",["stop"])
        m=create_milestone(self.root,"M",["evidence"])
        a=add_item(self.root,kind="Idea",title="A",module="topic")
        with self.assertRaisesRegex(ResearchError,"member-of"):
            add_relation(self.root,a["id"],m["id"],"member-of")
        with self.assertRaisesRegex(ResearchError,"contributes-to"):
            add_relation(self.root,a["id"],b["id"],"contributes-to")

    def test_04_01_abstract_not_verified(self):
        source=add_source(self.root,title="SYNTHETIC abstract",url="https://example.org/abstract",
                          access_level="abstract")
        claim=add_item(self.root,kind="Claim",title="Scientific claim",module="synthesis")
        with self.assertRaises(ResearchError):
            link_evidence(self.root,claim["id"],source["id"],"supports","this study",
                          quality="source-checked")

    def test_04_02_support_contradiction_scope_and_propagation(self):
        source=add_source(self.root,title="SYNTHETIC paper",locator="paper.txt",
                          access_level="user-provided",verification_status="primary-inspected",
                          verification_note="Only synthetic paper was inspected")
        claim=add_item(self.root,kind="Claim",title="Scientific claim",module="synthesis")
        dependent=add_item(self.root,kind="Task",title="Paper draft",module="synthesis")
        add_relation(self.root,dependent["id"],claim["id"],"depends-on")
        first=link_evidence(self.root,claim["id"],source["id"],"supports","toy study",
                            quality="source-checked",locator="Section 2")
        result=add_item(self.root,kind="Result",title="synthetic negative",module="experiment",
                        observation="F1 0.60 vs 0.61 (fabricated)",artifact_path="fake.log")
        link_evidence(self.root,claim["id"],result["id"],"contradicts","toy study only",
                      quality="experiment-observed")
        read=claim_evidence(self.root,claim["id"])
        self.assertEqual(len(read["links"]),2)
        self.assertEqual(read["epistemic_status"],"uncertain")
        impact={x["id"]:x["impact_status"] for x in load(self.root)["items"]}
        self.assertEqual(impact[dependent["id"]],"needs-review")
        with self.assertRaisesRegex(ResearchError,"duplicate"):
            link_evidence(self.root,claim["id"],source["id"],"supports","toy study",
                          quality="source-checked")

    def test_04_03_dangling_provenance_rejected(self):
        claim=add_item(self.root,kind="Claim",title="Claim",module="synthesis")
        with self.assertRaises(ResearchError):
            link_evidence(self.root,claim["id"],"SRC-9099","supports","some study")

    def test_05_01_many_to_many_and_unlink(self):
        a=add_item(self.root,kind="Idea",title="A",module="topic")
        b=add_item(self.root,kind="Claim",title="B",module="synthesis")
        s1=create_session(self.root,"codex","workspace-A","session-A")
        s2=create_session(self.root,"codex","workspace-A","session-B")
        session_entity_link(self.root,s1["id"],a["id"],"idea-origin")
        session_entity_link(self.root,s1["id"],b["id"],"decision")
        session_entity_link(self.root,s2["id"],a["id"],"discussion")
        self.assertEqual(len(load(self.root)["session_refs"]),2)
        with self.assertRaises(ResearchError):
            session_entity_link(self.root,s1["id"],a["id"],"discussion")
        session_entity_link(self.root,s1["id"],b["id"],remove=True)
        s={x["id"]:x for x in load(self.root)["session_refs"]}
        self.assertEqual(s[s1["id"]]["entity_ids"],[a["id"]])
        self.assertEqual(s[s2["id"]]["entity_ids"],[a["id"]])
        self.assertTrue(any(e["action"]=="session-entity-unlinked" for e in load(self.root)["events"]))

    def test_05_02_unsafe_or_fake_verified_link_rejected(self):
        with self.assertRaises(ResearchError):
            create_session(self.root,"codex","w","x",url="javascript:alert(1)")
        with self.assertRaises(ResearchError):
            create_session(self.root,"codex","w","x",url="https://user:pass@example.org/chat")
        s=create_session(self.root,"codex","w","x",url="https://example.org/session")
        self.assertFalse(s["url_verified"])
        with self.assertRaises(ResearchError):
            create_session(self.root,"codex","w","x")

    def test_deepseek_session_ref(self):
        a=add_item(self.root,kind="Idea",title="DSH fixture",module="topic")
        s=create_session(self.root,"deepseek","workspace","session")
        c=create_session(self.root,"codex","workspace","session")
        session_entity_link(self.root,s["id"],a["id"],"discussion")
        self.assertNotEqual(s["id"],c["id"])
        self.assertFalse(s["url_verified"])
        self.assertEqual(validate_state(load(self.root)),[])
        with self.assertRaises(ResearchError):
            create_session(self.root,"deepseek","workspace","session")

    def test_05_03_unlinked_session_does_not_change_evidence(self):
        a=add_item(self.root,kind="Idea",title="A",module="topic")
        s=create_session(self.root,"other","workspace","session")
        session_entity_link(self.root,s["id"],a["id"],"idea-origin")
        session_entity_link(self.root,s["id"],a["id"],remove=True)
        self.assertEqual(load(self.root)["items"][0]["epistemic_status"],"hypothesis")
        self.assertEqual(load(self.root)["session_refs"][0]["entity_ids"],[])

    def test_04_04_revising_result_invalidates_linked_claim_and_milestone(self):
        result = add_item(self.root,kind="Result",title="SYNTHETIC result",
                          module="experiment",observation="Toy metric",artifact_path="toy.log")
        claim = add_item(self.root,kind="Claim",title="Effect claim",module="synthesis")
        milestone = create_milestone(self.root,"Evidence review",["Claim checked"])
        add_relation(self.root,claim["id"],milestone["id"],"contributes-to")
        link_evidence(self.root,claim["id"],result["id"],"supports",
                      "toy experimental protocol",quality="experiment-observed")
        change_status(self.root,result["id"],"outcome","negative",
                      "new synthetic result changed the interpretation")
        by={x["id"]:x for x in load(self.root)["items"]}
        self.assertEqual(by[claim["id"]]["impact_status"],"needs-review")
        self.assertEqual(by[milestone["id"]]["impact_status"],"needs-review")
        self.assertEqual(by[claim["id"]]["epistemic_status"],"uncertain")


if __name__=="__main__":
    unittest.main()
