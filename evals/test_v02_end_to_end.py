"""#13 integrated synthetic research scenario: archive, graph, session, milestone,
migration, stale write and offline snapshots. No real human or Codex asserted."""
from pathlib import Path
import sys,tempfile,unittest,copy
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from rn_core import (init_project,add_item,add_relation,add_source,load,query,
                     change_status,read_json,atomic_json,paths,ResearchError)
from rn_domain import create_branch,create_milestone
from rn_proposals import queue_proposal,approve_proposal,preview_proposal
from graph_projection import project_graph
from build_dashboard import build
from migrate_state import preview as migration_preview,apply as migrate

class IntegratedSyntheticResearch(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(prefix="rn-v02-e2e-")
  self.root=Path(self.temp.name)
  init_project(self.root,"SYNTHETIC integrated project")
 def tearDown(self):self.temp.cleanup()
 def payload(self,op,args):
  return {"operation":op,"params":args,
          "reason":"Synthetic human-reviewed scenario; not real authentication",
          "expected_revision":load(self.root)["project"]["revision"]}
 def act(self,op,args):
  payload=self.payload(op,args)
  pre=load(self.root)
  preview_proposal(self.root,payload)
  queued=queue_proposal(self.root,payload)
  self.assertEqual(load(self.root),pre)
  approve_proposal(self.root,queued["proposal_id"],confirmed=True)
  return queued["proposal_id"]
 def test_full_synthetic_three_branch_archive_and_revival(self):
  baseline=add_item(self.root,kind="Baseline",title="Shared synthetic baseline",module="literature")
  branches=[create_branch(self.root,"Route "+v,"Compare "+v,["No robust gain"])
            for v in "ABC"]
  for b in branches:add_relation(self.root,baseline["id"],b["id"],"member-of")
  mile=create_milestone(self.root,"Scientific gate",["Fair reference comparison"])
  add_relation(self.root,branches[0]["id"],mile["id"],"contributes-to")
  idea=add_item(self.root,kind="Idea",title="Weak method A",module="topic")
  add_relation(self.root,idea["id"],branches[0]["id"],"member-of")
  result=add_item(self.root,kind="Result",title="SYNTHETIC negative",
                  module="experiment",observation="toy: .49 vs .50",
                  artifact_path="fixture-toy.log")
  claim=add_item(self.root,kind="Claim",title="Synthetic uncertainty",module="synthesis")
  source=add_source(self.root,title="Unverified fixture",url="https://example.org/toy")
  self.act("link-evidence",{"claim_id":claim["id"],"evidence_id":result["id"],
           "stance":"contradicts","quality":"experiment-observed",
           "scope":"Only synthetic toy experiment"})
  self.act("register-session",{"provider":"codex","workspace_id":"synthetic-project",
           "session_id":"fake-session-1"})
  self.act("register-session",{"provider":"chatgpt","workspace_id":"synthetic-project",
           "session_id":"fake-session-2"})
  for ref,entity,role in (("SESS-0001",idea["id"],"idea-origin"),
           ("SESS-0001",claim["id"],"decision"),
           ("SESS-0002",idea["id"],"experiment-analysis")):
   self.act("link-session",{"session_ref_id":ref,"entity_id":entity,"role":role})
  self.act("archive-route",{"item_id":idea["id"],"lifecycle":"parked",
           "failure_scope":"Toy sample only","revival_triggers":"Changed independent data",
           "failure_category":"evaluation","evidence_refs":[result["id"]]})
  snapshot=load(self.root)
  old_result=copy.deepcopy(next(x for x in snapshot["items"] if x["id"]==result["id"]))
  self.assertNotIn(idea["id"],[q["item_id"] for q in query(snapshot,"planning")])
  self.assertIn(idea["id"],[q["item_id"] for q in query(snapshot,"synthesis")])
  self.assertEqual(next(x for x in snapshot["items"] if x["id"]==branches[1]["id"])["impact_status"],"current")
  self.assertEqual(next(x for x in snapshot["items"] if x["id"]==mile["id"])["impact_status"],"needs-review")
  graph=project_graph(snapshot,limit=None)
  self.assertEqual(sum(n["entity_id"]==baseline["id"] for n in graph["nodes"]),1)
  self.assertEqual(sum(n["type"]=="SessionRef" for n in graph["nodes"]),2)
  self.assertEqual(sum(e["provenance"]["collection"]=="session_refs" for e in graph["edges"]),3)
  self.act("begin-revival-review",{"item_id":idea["id"],"question":"New data?",
            "new_conditions":"Independent trial"})
  self.act("approve-revival-candidate",{"item_id":idea["id"],
           "title":"New v2 synthetic hypothesis","new_conditions":"Independent larger sample",
           "approval_note":"Second authorization, synthetic fixture only"})
  new=load(self.root)
  old=next(x for x in new["items"] if x["id"]==idea["id"])
  self.assertEqual(old["lifecycle_status"],"parked")
  self.assertEqual(next(x for x in new["items"] if x["id"]==result["id"]),old_result)
  self.assertEqual(len([x for x in new["items"] if x.get("derived_from")==idea["id"]]),1)
  before=load(self.root)
  dashboard=build(self.root)
  self.assertTrue(dashboard.exists())
  self.assertTrue((self.root/"research"/"canvas"/"index.html").exists())
  self.assertEqual(load(self.root),before)
 def test_migrated_legacy_snapshot_and_conflicts(self):
  add_item(self.root,kind="Idea",title="Historic idea",module="topic")
  state=load(self.root)
  version=read_json(paths(self.root)["project"])
  version["schema_version"]="0.1.0";atomic_json(paths(self.root)["project"],version)
  paths(self.root)["session_refs"].unlink();paths(self.root)["evidence_links"].unlink()
  self.assertTrue(migration_preview(self.root)["needs_migration"])
  migrate(self.root)
  self.assertEqual(state["items"],load(self.root)["items"])
  rev=load(self.root)["project"]["revision"]
  p=self.payload("add-item",{"type":"Idea","title":"Two editors","module":"topic"})
  queued=queue_proposal(self.root,p)
  add_item(self.root,kind="Idea",title="Fresh external change",module="topic")
  before=load(self.root)
  with self.assertRaisesRegex(ResearchError,"stale"):
   approve_proposal(self.root,queued["proposal_id"],confirmed=True)
  self.assertEqual(load(self.root),before)
  first=add_item(self.root,kind="Idea",title="A",module="topic")
  other=add_item(self.root,kind="Idea",title="B",module="topic")
  add_relation(self.root,first["id"],other["id"],"depends-on")
  with self.assertRaises(ResearchError):
   add_relation(self.root,other["id"],first["id"],"depends-on")

if __name__=="__main__":unittest.main()
