"""Unified Research Canvas v0.6 state/model/security regression.

Pure synthetic projects in TemporaryDirectory; tests must not be mistaken for
scientific findings or a real user's authenticated approval.
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))

from rn_core import (init_project,add_item,add_source,load,ResearchError,
                     change_status,add_relation)
from rn_domain import (create_branch,create_milestone,attach_milestone_evidence,
                       create_session,session_entity_link,link_evidence)
from rn_interview import start,add_questions,answer,request_exit,confirm_exit,read
from unified_graph import (unified_graph,read_context,context_path,validate_link_fields,
                           validate_context_link,inspect_context_candidate)
from rn_proposals import (preview_proposal,queue_proposal,approve_proposal,
                          reject_proposal,proposal_status)
from build_unified_canvas import build_unified
from build_canvas import build_canvas
from canvas_views import save_layout,load_views

def question(label="What is the highest-priority outcome?"):
    return {"text":label,"why":"Defines a falsifiable goal",
            "options":"A or B","recommendation":"Verify one baseline",
            "lowest_cost_check":"Compare toy data",
            "depends_on":[],
            "choices":[{"id":"acc","label":"Improve accuracy","description":"Target macro F1"},
                       {"id":"cost","label":"Lower cost","description":"Limit GPU usage"}]}

class UnifiedGraphTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix="rn-v06-unified-")
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)/"project"
        init_project(self.root,"SYNTHETIC unified Canvas","Synthetic research question")
    def graph(self):
        return unified_graph(self.root)
    def interview(self):
        start(self.root,topic="SYNTHETIC research grilling")
        add_questions(self.root,[question()])
        return read(self.root)["interview_id"]
    def proposal(self,op,params):
        return {"operation":op,"params":params,
                "reason":"User reviews this context only, not scientific evidence",
                "expected_revision":load(self.root)["project"]["revision"]}
    def context_args(self,source,target,relation="addresses"):
        return {"from":source,"to":target,"relation":relation,
                "expected_context_revision":read_context(self.root)["revision"]}
    def test_empty_project_and_legacy_canvas_untouched(self):
        original=load(self.root)
        graph=self.graph()
        self.assertEqual(graph["schema_version"],"unified-research-graph-v1")
        self.assertEqual(graph["nodes"],[])
        self.assertEqual(graph["edges"],[])
        canvas=build_canvas(self.root)
        self.assertTrue(canvas.exists())
        self.assertTrue((canvas.parent/"unified.html").exists())
        self.assertIn('href="unified.html"',canvas.read_text(encoding="utf-8"))
        self.assertEqual(load(self.root),original)
    def test_interview_question_answer_dag(self):
        ident=self.interview()
        info=self.graph()
        nodes={x["id"]:x for x in info["nodes"]}
        base="question:"+ident+"-Q-0001"
        ans="answer:"+ident+"-Q-0001"
        self.assertIn(base,nodes);self.assertIn(ans,nodes)
        self.assertEqual(nodes[ans]["statuses"]["answer_status"],"pending")
        self.assertTrue(any(e["from"]==base and e["to"]==ans for e in info["edges"]))
        answer(self.root,"Q-0001",choice_id="other",custom_answer="SYNTHETIC cross-domain robust metric",
               supplement="Only toy design not verified")
        n={x["id"]:x for x in self.graph()["nodes"]}[ans]
        self.assertEqual(n["metadata"]["custom_answer"],"SYNTHETIC cross-domain robust metric")
        self.assertEqual(n["metadata"]["supplement"],"Only toy design not verified")
        self.assertFalse(n["actionable"])
        self.assertNotIn("experimentally-supported",str(n["statuses"]))
    def test_milestone_criteria_and_evidence_no_approval(self):
        milestone=create_milestone(self.root,"Reproduce toy baseline",["A reproducible trial"])
        source=add_source(self.root,"SYNTHETIC paper",url="https://example.org/paper")
        attach_milestone_evidence(self.root,milestone["id"],"C-001",source["id"])
        data=self.graph()
        criterion=next(n for n in data["nodes"] if n["kind"]=="criterion")
        self.assertEqual(criterion["id"],"criterion:"+milestone["id"]+"-C-001")
        self.assertFalse(criterion["statuses"]["satisfied"])
        self.assertTrue(any(e["to"]==criterion["id"] and e["type"]=="cited-for-criterion"
                            for e in data["edges"]))
        self.assertFalse(next(n for n in data["nodes"] if n["id"]=="item:"+milestone["id"])["metadata"]["milestone"]["accepted"])
    def test_canonical_shared_baseline_not_duplicated(self):
        base=add_item(self.root,kind="Baseline",title="Shared synthetic baseline",module="literature")
        a=create_branch(self.root,"A","test A",["Stop if invalid"])
        b=create_branch(self.root,"B","test B",["Stop if invalid"])
        add_relation(self.root,base["id"],a["id"],"member-of")
        add_relation(self.root,base["id"],b["id"],"member-of")
        graph=self.graph()
        self.assertEqual(sum(n["id"]=="item:"+base["id"] for n in graph["nodes"]),1)
        self.assertEqual(len([e for e in graph["edges"] if e["from"]=="item:"+base["id"]]),2)
    def test_provider_scoped_session_provenance(self):
        idea=add_item(self.root,kind="Idea",title="Toy idea",module="topic")
        codex=create_session(self.root,"codex","one","session-id")
        deepseek=create_session(self.root,"deepseek","two","session-id")
        session_entity_link(self.root,codex["id"],idea["id"],"discussion")
        session_entity_link(self.root,deepseek["id"],idea["id"],"discussion")
        graph=self.graph()
        refs=[n for n in graph["nodes"] if n["kind"]=="session-ref"]
        self.assertEqual(len(refs),2)
        self.assertEqual({r["metadata"]["provider"] for r in refs},{"codex","deepseek"})
        self.assertTrue(all(r["ports"]["outputs"] for r in refs))
        self.assertTrue(all("chat text not stored" in r["description"] for r in refs))
    def test_typing_rejects_wrong_direction_and_missing_node(self):
        ident=self.interview()
        idea=add_item(self.root,kind="Idea",title="Idea",module="topic")
        source="question:"+ident+"-Q-0001"
        validate_context_link(self.graph(),source,"item:"+idea["id"],"addresses")
        for a,b,relation in (
            ("item:"+idea["id"],source,"addresses"),
            (source,source,"addresses"),
            (source,"item:DOESNOTEXIST","addresses"),
            ("item:"+idea["id"],"item:"+idea["id"],"motivates")
        ):
            with self.subTest(a=a,b=b):
                with self.assertRaises(ResearchError):
                    validate_context_link(self.graph(),a,b,relation)
    def test_proposal_requires_explicit_terminal_approval(self):
        ident=self.interview()
        idea=add_item(self.root,kind="Idea",title="Unproven toy idea",module="topic")
        src="question:"+ident+"-Q-0001";target="item:"+idea["id"]
        payload=self.proposal("link-context",self.context_args(src,target))
        before=load(self.root)
        preview=preview_proposal(self.root,payload)
        self.assertFalse(preview["scientific_revision_unchanged"] is False)
        self.assertEqual(load(self.root),before)
        pending=queue_proposal(self.root,payload)["proposal_id"]
        self.assertEqual(self.graph()["context_revision"],0)
        with self.assertRaises(ResearchError):
            approve_proposal(self.root,pending)
        self.assertEqual(self.graph()["context_revision"],0)
        approved=approve_proposal(self.root,pending,confirmed=True)
        self.assertEqual(approved["status"],"applied")
        self.assertEqual(self.graph()["context_revision"],1)
        self.assertEqual(load(self.root),before)
        self.assertTrue(any(e["provenance"].get("context_only") for e in self.graph()["edges"]))
        with self.assertRaises(ResearchError):
            approve_proposal(self.root,pending,confirmed=True)
    def test_unlink_context_requires_new_approval_and_preserves_canonical(self):
        ident=self.interview()
        idea=add_item(self.root,kind="Idea",title="Synthetic idea",module="topic")
        src="question:"+ident+"-Q-0001";target="item:"+idea["id"]
        a=self.proposal("link-context",self.context_args(src,target))
        pid=queue_proposal(self.root,a)["proposal_id"]
        lid=approve_proposal(self.root,pid,confirmed=True)["result"]["link_id"]
        before=load(self.root)
        request=self.proposal("unlink-context",{"link_id":lid,
                        "expected_context_revision":read_context(self.root)["revision"]})
        remove=queue_proposal(self.root,request)["proposal_id"]
        self.assertEqual(len(read_context(self.root)["links"]),1)
        approve_proposal(self.root,remove,confirmed=True)
        self.assertEqual(read_context(self.root)["links"],[])
        self.assertEqual(load(self.root),before)
    def test_archived_rejects_new_link_but_old_history_stays_visible(self):
        ident=self.interview()
        idea=add_item(self.root,kind="Idea",title="Archived candidate",module="topic")
        src="question:"+ident+"-Q-0001";target="item:"+idea["id"]
        p=self.proposal("link-context",self.context_args(src,target))
        pid=queue_proposal(self.root,p)["proposal_id"]
        approve_proposal(self.root,pid,confirmed=True)
        change_status(self.root,idea["id"],"lifecycle_status","parked",
                      "human archived synthetic route",actor="user",
                      failure_scope="toy one seed",revival_triggers="independent data")
        self.assertTrue(any(e["provenance"].get("context_only") for e in self.graph()["edges"]))
        with self.assertRaises(ResearchError):
            queue_proposal(self.root,self.proposal("link-context",self.context_args(
                "answer:"+ident+"-Q-0001",target,"motivates")))
    def test_stale_context_revisions_and_cross_project(self):
        ident=self.interview()
        i=add_item(self.root,kind="Idea",title="A",module="topic")
        src="question:"+ident+"-Q-0001"
        first=self.proposal("link-context",self.context_args(src,"item:"+i["id"]))
        first_ref=queue_proposal(self.root,first)["proposal_id"]
        second=self.proposal("link-context",self.context_args("answer:"+ident+"-Q-0001",
            "item:"+i["id"],"motivates"))
        second_ref=queue_proposal(self.root,second)["proposal_id"]
        approve_proposal(self.root,first_ref,confirmed=True)
        with self.assertRaisesRegex(ResearchError,"stale"):
            approve_proposal(self.root,second_ref,confirmed=True)
        path=context_path(self.root)
        original=path.read_text(encoding="utf-8")
        row=json.loads(original);row["project_id"]="other-project"
        path.write_text(json.dumps(row),encoding="utf-8")
        with self.assertRaisesRegex(ResearchError,"Cross-project"):
            self.graph()
        path.write_text(original,encoding="utf-8")
        self.assertEqual(self.graph()["context_revision"],1)
    def test_layout_persists_new_namespaces_without_canonical_write(self):
        ident=self.interview()
        milestone=create_milestone(self.root,"Toy milestone",["Outcome documented"])
        base=load(self.root)
        ids=["question:"+ident+"-Q-0001","criterion:"+milestone["id"]+"-C-001"]
        view={"schema_version":"canvas-layout-v1",
              "project_id":base["project"]["project_id"],
              "view_name":"unified-test","graph_revision":base["project"]["revision"],
              "positions":{ident:{"x":i*120,"y":i*90} for i,ident in enumerate(ids)},
              "viewport":{"x":0,"y":0,"z":1},"collapsed":[],"pinned_groups":[]}
        save_layout(self.root,view)
        saved=load_views(self.root)["views"]["unified-test"]
        self.assertEqual(set(saved["positions"]),set(ids))
        self.assertEqual(load(self.root),base)
    def test_script_injection_encoded_in_unified_export(self):
        self.interview()
        add_item(self.root,kind="Idea",title='<script>window.pwned=true</script>',module="topic")
        page=build_unified(self.root)
        html=page.read_text(encoding="utf-8")
        self.assertNotIn('<script>window.pwned=true</script>',html)
        self.assertIn("\\u003cscript\\u003e",html)
        self.assertIn('id="rn-graph"',html)
    def test_corrupt_sidecar_fails_closed_and_old_canvas_remains(self):
        self.interview()
        path=context_path(self.root)
        path.parent.mkdir(exist_ok=True,parents=True)
        path.write_text("{not json",encoding="utf-8")
        original=load(self.root)
        with self.assertRaises(ResearchError):self.graph()
        self.assertEqual(load(self.root),original)

if __name__=="__main__":unittest.main()
