"""Issue #12 SessionRef many-to-many, unsafe URL, role, provenance and adapter limits."""
from pathlib import Path
import sys,tempfile,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from rn_core import init_project,add_item,load,ResearchError
from rn_proposals import queue_proposal,approve_proposal,preview_proposal
from graph_projection import project_graph

class SessionCanvasTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
  init_project(self.root,"SYNTHETIC session fixture")
  self.idea=add_item(self.root,kind="Idea",title="Research candidate",module="topic")
  self.claim=add_item(self.root,kind="Claim",title="Unverified claim",module="synthesis")
 def tearDown(self):self.tmp.cleanup()
 def payload(self,op,args):
  return {"operation":op,"params":args,"reason":"Human authorizes metadata reference only",
          "expected_revision":load(self.root)["project"]["revision"]}
 def commit(self,op,args):
  p=self.payload(op,args);before=load(self.root)
  preview=preview_proposal(self.root,p)
  self.assertFalse(preview["accepted"]);self.assertEqual(load(self.root),before)
  queued=queue_proposal(self.root,p)
  self.assertEqual(load(self.root),before)
  result=approve_proposal(self.root,queued["proposal_id"],confirmed=True)
  return result["result"]
 def test_many_to_many_ids_roles_and_unlink(self):
  a=self.commit("register-session",{"provider":"codex","workspace_id":"proj-A",
                                     "session_id":"real-session-a"})
  b=self.commit("register-session",{"provider":"other","workspace_id":"proj-A",
                                     "session_id":"real-session-b"})
  self.assertNotEqual(a["id"],b["id"])
  for ref,entity,role in ((a,self.idea,"idea-origin"),(a,self.claim,"decision"),
                          (b,self.idea,"experiment-analysis")):
   self.commit("link-session",{"session_ref_id":ref["id"],"entity_id":entity["id"],"role":role})
  state=load(self.root)
  self.assertEqual(len(state["session_refs"]),2)
  self.assertEqual(len(state["session_refs"][0]["entity_ids"]),2)
  self.assertFalse(any(s["url_verified"] for s in state["session_refs"]))
  graph=project_graph(state,limit=None)
  session_nodes=[n for n in graph["nodes"] if n["type"]=="SessionRef"]
  self.assertEqual(len(session_nodes),2)
  self.assertEqual(session_nodes[0]["metadata"]["roles"][self.idea["id"]],"idea-origin")
  self.assertEqual(sum(e["provenance"]["collection"]=="session_refs" for e in graph["edges"]),3)
  self.assertNotIn("chat_body",str(graph))
  self.commit("unlink-session",{"session_ref_id":a["id"],"entity_id":self.claim["id"]})
  self.assertEqual(load(self.root)["session_refs"][0]["entity_ids"],[self.idea["id"]])
  self.assertTrue(any(e["action"]=="session-entity-unlinked" for e in load(self.root)["events"]))
 def test_bad_url_and_duplicate_session_never_queued(self):
  before=load(self.root)
  for url in ("javascript:alert(1)","http://example.com/a",
              "https://u:p@example.org/a","https://example.org/a?secret=1"):
   with self.subTest(url=url),self.assertRaises(ResearchError):
    queue_proposal(self.root,self.payload("register-session",{
      "provider":"codex","workspace_id":"A","session_id":"B","url":url}))
  self.assertEqual(load(self.root),before)
  self.commit("register-session",{"provider":"codex","workspace_id":"A","session_id":"B",
                                   "url":"https://example.org/session"})
  with self.assertRaises(ResearchError):
   queue_proposal(self.root,self.payload("register-session",{
    "provider":"codex","workspace_id":"A","session_id":"B"}))
  self.assertFalse(load(self.root)["session_refs"][0]["url_verified"])
 def test_missing_session_role_duplicate_denied(self):
  session=self.commit("register-session",{"provider":"codex","workspace_id":"A","session_id":"B"})
  for params in ({"session_ref_id":session["id"],"entity_id":"IDEA-9999","role":"discussion"},
                 {"session_ref_id":session["id"],"entity_id":self.idea["id"],"role":"impossible"}):
   with self.assertRaises(ResearchError):
    queue_proposal(self.root,self.payload("link-session",params))
  self.commit("link-session",{"session_ref_id":session["id"],"entity_id":self.idea["id"],
                              "role":"discussion"})
  with self.assertRaises(ResearchError):
   queue_proposal(self.root,self.payload("link-session",{
      "session_ref_id":session["id"],"entity_id":self.idea["id"],"role":"discussion"}))
  with self.assertRaises(ResearchError):
   queue_proposal(self.root,self.payload("unlink-session",{
     "session_ref_id":session["id"],"entity_id":self.claim["id"]}))

if __name__=="__main__":unittest.main()
