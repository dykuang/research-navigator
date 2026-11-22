"""Research Canvas #8/#9 output and layout regressions, synthetic data only."""
import json
import re
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from rn_core import ResearchError,add_item,add_relation,init_project,load,paths
from rn_domain import create_branch,create_milestone,create_session,session_entity_link
from build_canvas import build_canvas
from canvas_views import save_layout,load_views,delete_layout,validate_layout
from build_dashboard import build

class CanvasTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        init_project(self.root,"SYNTHETIC Canvas project")
    def tearDown(self):
        self.temp.cleanup()
    def fixture(self):
        base=add_item(self.root,kind="Baseline",title="Shared synthetic baseline",module="literature")
        a=create_branch(self.root,"Branch A","A",["stop"])
        b=create_branch(self.root,"Branch B","B",["stop"])
        c=create_branch(self.root,"Branch C","C",["stop"])
        for br in (a,b,c):
            add_relation(self.root,base["id"],br["id"],"member-of")
        milestone=create_milestone(self.root,"Milestone","not broken") if False else create_milestone(self.root,"Milestone",["Evidence collected"])
        add_relation(self.root,a["id"],milestone["id"],"contributes-to")
        return a,b,c,base,milestone
    def payload(self,name="default"):
        state=load(self.root)
        return {"schema_version":"canvas-layout-v1","project_id":state["project"]["project_id"],
                "graph_revision":state["project"]["revision"],"view_name":name,
                "author":"synthetic-tester",
                "positions":{"item:IDEA-0001":{"x":25.5,"y":-45.25}},
                "viewport":{"x":178.0,"y":90.0,"z":0.74},
                "collapsed":[],"pinned_groups":["topic"]}
    def test_canvas_contains_every_node_over_100(self):
        self.fixture()
        for i in range(110):
            add_item(self.root,kind="Idea",title="Synthetic idea "+str(i),module="topic")
        canvas=build_canvas(self.root)
        html=canvas.read_text(encoding="utf-8")
        self.assertIn("Research Canvas",html)
        self.assertIn('id="minimap"',html)
        self.assertIn('id="zoomIn"',html)
        self.assertIn('id="exportSVG"',html)
        self.assertIn('id="inspector"',html)
        self.assertIn('id="rn-graph"',html)
        self.assertNotIn("__RN_GRAPH_JSON__",html)
        match=re.search(r'<script type="application/json" id="rn-graph">(.*?)</script>',html,re.S)
        self.assertIsNotNone(match)
        graph=json.loads(match.group(1))
        self.assertEqual(graph["page"]["total_nodes"],115)
        self.assertEqual(len(graph["nodes"]),115)
        self.assertEqual(sum(n["type"]=="Baseline" for n in graph["nodes"]),1)
        self.assertEqual(sum(e["type"]=="member-of" for e in graph["edges"]),3)
        self.assertEqual(graph["project_revision"],load(self.root)["project"]["revision"])
        self.assertFalse(canvas.as_posix().endswith("dashboard/index.html"))
    def test_canvas_html_safe_embedded_content(self):
        add_item(self.root,kind="Idea",title="evil </script><script>alert(1)</script>",module="topic")
        html=build_canvas(self.root).read_text(encoding="utf-8")
        self.assertNotIn("</script><script>alert(1)",html)
        self.assertIn("\\u003c/script\\u003e",html)
    def test_classic_dashboard_still_builds(self):
        add_item(self.root,kind="Idea",title="Synthetic",module="topic")
        old=build(self.root)
        self.assertTrue(old.exists())
        self.assertIn('id="relationSvg"',old.read_text(encoding="utf-8"))
        self.assertIn('../canvas/index.html',old.read_text(encoding="utf-8"))
        self.assertTrue((self.root/"research"/"canvas"/"index.html").exists())
    def test_canvas_scripts_compile_with_node_if_available(self):
        if not shutil.which("node"):
            self.skipTest("node executable not installed")
        html=build_canvas(self.root).read_text(encoding="utf-8")
        matches=re.findall(r"<script(?: [^>]*)?>(.*?)</script>",html,re.S)
        scripts=[x for x in matches if "(function(){" in x]
        self.assertEqual(len(scripts),1)
        cp=subprocess.run(["node","--check"],input=scripts[0],text=True,
                          capture_output=True,timeout=10)
        self.assertEqual(cp.returncode,0,cp.stderr)
    def test_layout_only_does_not_change_research_state(self):
        add_item(self.root,kind="Idea",title="Idea",module="topic")
        original=load(self.root)
        saved=save_layout(self.root,self.payload())
        self.assertEqual(saved["viewport"]["z"],.74)
        after=load(self.root)
        self.assertEqual(after,original)
        self.assertTrue((self.root/"research"/"canvas"/"views.json").exists())
        self.assertEqual(load_views(self.root)["views"]["default"]["positions"]["item:IDEA-0001"]["y"],-45.25)
        html=build_canvas(self.root).read_text(encoding="utf-8")
        embedded=re.search(r'<script type="application/json" id="rn-views">(.*?)</script>',html,re.S)
        self.assertIsNotNone(embedded)
        self.assertIn("default",json.loads(embedded.group(1))["views"])
    def test_layout_rejects_scientific_fields_and_wrong_project(self):
        add_item(self.root,kind="Idea",title="A",module="topic")
        valid=self.payload()
        bad=dict(valid);bad["epistemic_status"]="experimentally-supported"
        with self.assertRaises(ResearchError):save_layout(self.root,bad)
        bad=dict(valid);bad["project_id"]="other"
        with self.assertRaises(ResearchError):save_layout(self.root,bad)
        bad=self.payload();bad["positions"]["item:IDEA-0001"]["x"]=float("nan")
        with self.assertRaises(ResearchError):save_layout(self.root,bad)
        self.assertEqual(load_views(self.root)["views"],{})
    def test_layout_roundtrip_rename_and_deleted_node_tolerated(self):
        add_item(self.root,kind="Idea",title="A",module="topic")
        x=self.payload(name="Experiment A")
        x["positions"]["item:IDEA-9999"]={"x":900,"y":600}
        saved=save_layout(self.root,x)
        self.assertIn("item:IDEA-9999",saved["positions"])
        saved=save_layout(self.root,self.payload("Research Routes"))
        self.assertEqual(set(load_views(self.root)["views"]),{"Experiment A","Research Routes"})
        delete_layout(self.root,"Experiment A")
        self.assertEqual(set(load_views(self.root)["views"]),{"Research Routes"})
        self.assertTrue(build_canvas(self.root).exists())
    def test_legacy_project_can_migrate_and_render_canvas_without_data_loss(self):
        from rn_core import read_json, atomic_json
        from migrate_state import apply,preview
        idea=add_item(self.root,kind="Idea",title="Synthetic migrated idea",module="topic")
        before=load(self.root)
        project=read_json(paths(self.root)["project"])
        project["schema_version"]="0.1.0"
        atomic_json(paths(self.root)["project"],project)
        paths(self.root)["session_refs"].unlink()
        paths(self.root)["evidence_links"].unlink()
        self.assertTrue(preview(self.root)["needs_migration"])
        migrated=apply(self.root)
        self.assertEqual(migrated["status"],"migrated")
        self.assertEqual(load(self.root)["items"],before["items"])
        html=build_canvas(self.root).read_text(encoding="utf-8")
        self.assertIn(idea["id"],html)
        self.assertIn('id="minimap"',html)
        self.assertEqual(load(self.root)["project"]["schema_version"],"0.2.0")
    def test_canvas_new_nodes_after_saved_layout_receive_default_positions(self):
        a=add_item(self.root,kind="Idea",title="A",module="topic")
        x=self.payload();x["positions"]={"item:"+a["id"]:{"x":100,"y":200}}
        save_layout(self.root,x)
        before=load_views(self.root)
        add_item(self.root,kind="Idea",title="B",module="topic")
        html=build_canvas(self.root).read_text(encoding="utf-8")
        match=re.search(r'<script type="application/json" id="rn-views">(.*?)</script>',html,re.S)
        saved=json.loads(match.group(1))
        self.assertEqual(saved["views"]["default"]["positions"],before["views"]["default"]["positions"])
        self.assertEqual(len(load(self.root)["items"]),2)

    def test_canvas_creation_does_not_append_research_events(self):
        self.fixture()
        before=load(self.root)
        build_canvas(self.root);build_canvas(self.root)
        self.assertEqual(load(self.root),before)

if __name__=="__main__":unittest.main()
