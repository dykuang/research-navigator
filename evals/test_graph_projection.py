"""Issue #7: deterministic graph projections and immutable canonical state."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from rn_core import init_project,add_item,add_relation,add_source,change_status,load
from rn_domain import create_branch,create_milestone,create_session,session_entity_link,link_evidence
from graph_projection import project_graph

class ProjectionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        init_project(self.root,"SYNTHETIC graph fixture")
    def tearDown(self):self.temp.cleanup()

    def test_deterministic_and_canonical_immutable(self):
        b=create_branch(self.root,"Track A","Research A",["stop when falsified"])
        a=add_item(self.root,kind="Idea",title="Idea A",module="topic")
        add_relation(self.root,a["id"],b["id"],"member-of")
        before=load(self.root);original=copy.deepcopy(before)
        x=project_graph(before,limit=None)
        y=project_graph(before,limit=None)
        self.assertEqual(json.dumps(x,sort_keys=True),json.dumps(y,sort_keys=True))
        self.assertEqual(before,original)
        self.assertTrue(all(e["from"] in {n["id"] for n in x["nodes"]} for e in x["edges"]))
        self.assertTrue(all(e["to"] in {n["id"] for n in x["nodes"]} for e in x["edges"]))
        self.assertTrue(any(e["provenance"]["collection"]=="relations" for e in x["edges"]))
    def test_shared_baseline_has_one_node_and_multiple_edges(self):
        a=create_branch(self.root,"A","A",["stop"])
        b=create_branch(self.root,"B","B",["stop"])
        c=create_branch(self.root,"C","C",["stop"])
        base=add_item(self.root,kind="Baseline",title="Same baseline",module="literature")
        for branch in [a,b,c]:
            add_relation(self.root,base["id"],branch["id"],"member-of")
        graph=project_graph(load(self.root),limit=None)
        self.assertEqual(sum(n["entity_id"]==base["id"] for n in graph["nodes"]),1)
        self.assertEqual(sum(e["type"]=="member-of" for e in graph["edges"]),3)
        focused=project_graph(load(self.root),focus=base["id"],depth=1,limit=None)
        self.assertEqual(len(focused["nodes"]),4)
    def test_archive_restricted_planning_and_risk(self):
        idea=add_item(self.root,kind="Idea",title="Failed synthetic",module="topic")
        change_status(self.root,idea["id"],"lifecycle_status","parked",
            "synthetic failure",actor="user",failure_scope="toy data",revival_triggers="new data")
        graph=project_graph(load(self.root),limit=None)
        self.assertEqual(next(n for n in graph["nodes"] if n["entity_id"]==idea["id"])["statuses"]["lifecycle_status"],"parked")
        self.assertFalse(any(n["entity_id"]==idea["id"] for n in project_graph(load(self.root),view="planning",limit=None)["nodes"]))
        self.assertTrue(any(n["entity_id"]==idea["id"] for n in project_graph(load(self.root),view="archive",limit=None)["nodes"]))
    def test_source_evidence_and_session_ref_provenance(self):
        claim=add_item(self.root,kind="Claim",title="Toy claim",module="synthesis")
        src=add_source(self.root,title="Synthetic paper",url="https://example.org/placeholder")
        link=link_evidence(self.root,claim["id"],src["id"],"qualifies","synthetic scope",quality="unverified")
        sess=create_session(self.root,"codex","synthetic","session123")
        session_entity_link(self.root,sess["id"],claim["id"],"decision")
        graph=project_graph(load(self.root),limit=None)
        types={n["type"] for n in graph["nodes"]}
        self.assertTrue({"Claim","Source","EvidenceLink","SessionRef"}<=types)
        self.assertEqual(sum(e["provenance"]["collection"]=="evidence_links" for e in graph["edges"]),2)
        self.assertEqual(sum(e["provenance"]["collection"]=="session_refs" for e in graph["edges"]),1)
        self.assertNotIn("chat_body",json.dumps(graph))
        self.assertFalse(any("secret transcript" in json.dumps(n) for n in graph["nodes"]))
    def test_pagination_over_100_and_focus(self):
        for i in range(141):
            add_item(self.root,kind="Idea",title="Synthetic %03d"%i,module="topic")
        state=load(self.root)
        one=project_graph(state,offset=0,limit=70)
        two=project_graph(state,offset=70,limit=70)
        three=project_graph(state,offset=140,limit=70)
        ids=[n["id"] for g in (one,two,three) for n in g["nodes"]]
        self.assertEqual(len(ids),141)
        self.assertEqual(len(set(ids)),141)
        self.assertEqual(one["page"]["total_nodes"],141)
        self.assertIsNone(three["page"]["next_offset"])
    def test_filters(self):
        a=add_item(self.root,kind="Idea",title="Unique search term",module="topic")
        graph=project_graph(load(self.root),text="unique",module="topic",limit=None)
        self.assertEqual([n["entity_id"] for n in graph["nodes"]],[a["id"]])
        self.assertEqual(project_graph(load(self.root),view="routes",limit=None)["nodes"][0]["entity_id"],a["id"])

if __name__=="__main__":unittest.main()
