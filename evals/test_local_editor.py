"""Security and end-to-end tests for #6 local proposal bridge.

All fixtures are synthetic and confined to temporary local project directories.
"""
from __future__ import annotations
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from rn_core import ResearchError, add_item, init_project, load
from rn_proposals import (approve_proposal, inspect_proposal, queue_proposal,
                          reject_proposal, validate_proposal)
from local_editor import create_handler, state_view


class ProposalSecurityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "research-project"
        init_project(self.root, "SYNTHETIC local bridge", "synthetic research question")

    def tearDown(self):
        self.temp.cleanup()

    def proposal(self, *, op="add-item", params=None, revision=None):
        s = load(self.root)
        return {
            "operation": op,
            "params": params or {"type":"Idea","title":"Synthetic idea","module":"topic"},
            "reason":"Evaluate a synthetic research candidate",
            "expected_revision": s["project"]["revision"] if revision is None else revision,
        }

    def test_http_proposal_creates_no_canonical_event_until_terminal_confirm(self):
        before = load(self.root)
        submitted = queue_proposal(self.root,self.proposal())
        after_queue = load(self.root)
        self.assertEqual(after_queue,before)
        row = inspect_proposal(self.root,submitted["proposal_id"])
        self.assertEqual(row["status"],"pending")
        self.assertEqual(row["expected_revision"],before["project"]["revision"])
        with self.assertRaisesRegex(ResearchError,"terminal"):
            approve_proposal(self.root,submitted["proposal_id"])
        approved = approve_proposal(self.root,submitted["proposal_id"],confirmed=True)
        self.assertEqual(approved["status"],"applied")
        after = load(self.root)
        self.assertEqual(after["project"]["revision"],before["project"]["revision"]+1)
        self.assertEqual(len(after["events"]),len(before["events"])+1)
        self.assertEqual(after["events"][-1]["proposal_id"],submitted["proposal_id"])
        with self.assertRaises(ResearchError):
            approve_proposal(self.root,submitted["proposal_id"],confirmed=True)
        self.assertEqual(load(self.root),after)

    def test_reject_does_not_mutate_project(self):
        before=load(self.root)
        row=queue_proposal(self.root,self.proposal())
        self.assertEqual(reject_proposal(self.root,row["proposal_id"],confirmed=True)["status"],"rejected")
        self.assertEqual(load(self.root),before)
        with self.assertRaises(ResearchError):
            approve_proposal(self.root,row["proposal_id"],confirmed=True)

    def test_stale_proposal_and_approval_reject(self):
        row=queue_proposal(self.root,self.proposal())
        add_item(self.root,kind="Idea",title="Other editor",module="topic")
        before=load(self.root)
        with self.assertRaisesRegex(ResearchError,"stale"):
            approve_proposal(self.root,row["proposal_id"],confirmed=True)
        self.assertEqual(before,load(self.root))
        with self.assertRaisesRegex(ResearchError,"stale"):
            queue_proposal(self.root,self.proposal(revision=0))

    def test_disallowed_lifecycle_status_and_approval_fields(self):
        risky=[
            self.proposal(op="set-status",params={"item_id":"IDEA-0001","field":"lifecycle_status","value":"active"}),
            self.proposal(op="set-status",params={"item_id":"IDEA-0001","field":"review_status","value":"user-confirmed"}),
            self.proposal(op="set-status",params={"item_id":"IDEA-0001","field":"workflow_status","value":"done"}),
            self.proposal(op="add-item",params={"type":"Milestone","title":"Bad","module":"topic"}),
            self.proposal(op="add-item",params={"type":"Idea","title":"Bad","module":"topic","review":"user-confirmed"}),
        ]
        for payload in risky:
            with self.subTest(payload=payload):
                with self.assertRaises(ResearchError):
                    queue_proposal(self.root,payload)
        self.assertEqual(len(load(self.root)["items"]),0)

    def test_revival_relation_cannot_be_queued(self):
        idea=add_item(self.root,kind="Idea",title="Old idea",module="topic")
        for relation in ("revives","derived-from","supersedes","blocks","contradicts","supports"):
            with self.subTest(relation=relation):
                p=self.proposal(op="add-relation",params={"source":idea["id"],
                                  "target":idea["id"],"relation":relation})
                with self.assertRaises(ResearchError):
                    queue_proposal(self.root,p)

    def test_archived_outcome_cannot_be_modified_by_bridge(self):
        from rn_core import change_status
        idea=add_item(self.root,kind="Idea",title="Archived synthetic idea",module="topic")
        change_status(self.root,idea["id"],"lifecycle_status","parked",
                      "Human parked synthetic idea",actor="user",
                      failure_scope="Small synthetic test",revival_triggers="New sample")
        original=load(self.root)
        p=self.proposal(op="set-status",params={"item_id":idea["id"],
                          "field":"outcome","value":"positive"})
        with self.assertRaisesRegex(ResearchError,"archived"):
            queue_proposal(self.root,p)
        self.assertEqual(load(self.root),original)

    def test_scientific_result_outcome_requires_primary_workflow(self):
        result=add_item(self.root,kind="Result",title="Synthetic result",
                        module="experiment",observation="Toy observation",
                        artifact_path="synthetic-result.log")
        before=load(self.root)
        with self.assertRaisesRegex(ResearchError,"scientific result"):
            queue_proposal(self.root,self.proposal(op="set-status",
                params={"item_id":result["id"],"field":"outcome","value":"positive"}))
        self.assertEqual(load(self.root),before)

    def test_valid_status_and_relation_gated_by_terminal(self):
        idea=add_item(self.root,kind="Idea",title="Existing idea",module="topic")
        before=load(self.root)
        p=self.proposal(op="set-status",params={"item_id":idea["id"],
                      "field":"workflow_status","value":"in-progress"})
        ref=queue_proposal(self.root,p)["proposal_id"]
        self.assertEqual(load(self.root),before)
        approve_proposal(self.root,ref,confirmed=True)
        self.assertEqual(load(self.root)["items"][0]["workflow_status"],"in-progress")
        self.assertEqual(load(self.root)["items"][0]["review_status"],"needs-user-confirmation")

    def test_invalid_relation_does_not_write(self):
        idea=add_item(self.root,kind="Idea",title="Idea",module="topic")
        before=load(self.root)
        p=self.proposal(op="add-relation",params={"source":idea["id"],
                         "target":"IDEA-9999","relation":"depends-on"})
        with self.assertRaises(ResearchError):
            queue_proposal(self.root,p)
        self.assertEqual(before,load(self.root))

    def test_terminal_noninteractive_refused(self):
        cli=Path(__file__).resolve().parents[1] / "scripts" / "local_editor.py"
        ref=queue_proposal(self.root,self.proposal())["proposal_id"]
        out=subprocess.run([sys.executable,str(cli),"approve",str(self.root),ref],
                           input="APPROVE "+ref+"\n",text=True,capture_output=True,timeout=15)
        self.assertNotEqual(out.returncode,0)
        self.assertIn("interactive local terminal",out.stderr)
        self.assertEqual(load(self.root)["project"]["revision"],0)

    def test_no_arbitrary_paths_and_bad_proposal_id(self):
        for pid in ("../research/state/project.json","../../etc/passwd","foo", "0"*33):
            with self.assertRaises(ResearchError):
                inspect_proposal(self.root,pid)
        payload=self.proposal()
        payload["params"]["artifact_path"]="../../secret"
        with self.assertRaises(ResearchError):
            queue_proposal(self.root,payload)

    def test_read_only_state_is_scoped_without_raw_chat(self):
        i=add_item(self.root,kind="Idea",title="Synthetic topic",module="topic")
        data=state_view(self.root)
        self.assertTrue(data["read_only_without_terminal_approval"])
        self.assertEqual(data["items"][0]["id"],i["id"])
        self.assertNotIn("events",data)
        self.assertNotIn("session_refs",data)


class HttpBridgeSecurityTests(ProposalSecurityTests):
    def setUp(self):
        super().setUp()
        self.token="synthetic-capability-test-token"
        # Bind first to obtain a kernel-assigned loopback port, then attach handler.
        self.server=ThreadingHTTPServer(("127.0.0.1",0),object)
        self.port=self.server.server_address[1]
        self.server.RequestHandlerClass=create_handler(self.root,self.token,self.port)
        self.server.daemon_threads=True
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)
        super().tearDown()

    def request(self,path="/api/state",method="GET",body=None,token=None,
                origin=None,host=None,content_type="application/json"):
        url=f"http://127.0.0.1:{self.port}{path}"
        headers={"Host":host or f"127.0.0.1:{self.port}"}
        if token is not False:
            headers["X-RN-Token"]=token if token is not None else self.token
        if origin is not False:
            headers["Origin"]=origin if origin is not None else f"http://127.0.0.1:{self.port}"
        if method=="POST":
            headers["Content-Type"]=content_type
        request=Request(url,headers=headers,
                        data=json.dumps(body).encode("utf-8") if body is not None else None,
                        method=method)
        try:
            with urlopen(request,timeout=3) as response:
                return response.status, json.loads(response.read())
        except HTTPError as exc:
            return exc.code,json.loads(exc.read())

    def test_cross_site_host_token_and_missing_origin_blocked(self):
        initial=load(self.root)
        p=self.proposal()
        variants=[
            {"token":False},
            {"token":"invalid"},
            {"origin":"http://evil.example"},
            {"origin":False},
            {"host":"attacker.example"},
        ]
        for kw in variants:
            with self.subTest(kw=kw):
                status,_=self.request("/api/proposals","POST",p,**kw)
                self.assertEqual(status,403)
        self.assertEqual(load(self.root),initial)

    def test_no_http_approval_mutation_or_cors(self):
        data=self.proposal()
        status,row=self.request("/api/proposals","POST",data)
        self.assertEqual(status,202)
        self.assertEqual(row["status"],"pending")
        initial=load(self.root)
        for endpoint in ("/api/approve","/api/commit","/api/proposals/"+row["proposal_id"]+"/approve"):
            with self.subTest(endpoint=endpoint):
                code,_=self.request(endpoint,"POST",{"approval":True})
                self.assertEqual(code,404)
        code,_=self.request("/api/proposals","OPTIONS")
        self.assertEqual(code,405)
        self.assertEqual(load(self.root),initial)

    def test_http_stale_revision_and_validation_errors(self):
        p=self.proposal(revision=99)
        code,_=self.request("/api/proposals","POST",p)
        self.assertEqual(code,409)
        p=self.proposal(op="set-status",params={"item_id":"IDEA-0001",
                          "field":"lifecycle_status","value":"active"})
        code,_=self.request("/api/proposals","POST",p)
        self.assertEqual(code,400)
        code,_=self.request("/api/proposals","POST",self.proposal(),
                            content_type="text/plain")
        self.assertEqual(code,415)
        self.assertEqual(load(self.root)["project"]["revision"],0)

    def test_http_read_requires_capability(self):
        code,_=self.request("/api/state",token=False)
        self.assertEqual(code,403)
        code,state=self.request("/api/state")
        self.assertEqual(code,200)
        self.assertEqual(state["revision"],0)
        self.assertEqual(state["project_name"],"SYNTHETIC local bridge")


if __name__=="__main__":
    unittest.main()
