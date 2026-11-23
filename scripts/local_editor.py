#!/usr/bin/env python3
"""Localhost-only, capability-protected Research Navigator proposal bridge.

Browser only queues draft proposals. A real person must approve a specific
proposal from an interactive terminal; no HTTP route can approve research edits.
No external packages, remote bind, CORS, or arbitrary filesystem access.
"""
from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import secrets
import sys
from urllib.parse import urlsplit

from rn_core import ResearchError, load, validate_state, now
from rn_proposals import (queue_proposal, inspect_proposal, approve_proposal,
                          preview_proposal, proposal_status)
from graph_projection import project_graph
from build_canvas import embedded_json
from pathlib import Path
import re

PAGE = """<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Research Navigator — Local Proposal Bridge</title>
<style>
:root{color-scheme:light dark;font-family:system-ui,sans-serif}
body{max-width:780px;margin:2rem auto;padding:0 1rem;line-height:1.5}
button,input,textarea,select{font:inherit;padding:.45rem;margin:.15rem}
textarea{display:block;box-sizing:border-box;width:100%;min-height:9rem}
#output{white-space:pre-wrap;overflow-wrap:anywhere;border:1px solid #888;padding:1rem;min-height:4rem}
small{opacity:.8}fieldset{margin-top:1.3rem}legend{font-weight:bold}
</style>
<h1>Research Navigator — Local Proposal Bridge</h1>
<p><strong>Proposals only.</strong> This page cannot approve, retire,
revive, validate claims, or save research changes directly. Approval requires
a separate interactive terminal command.</p>
<p id="status">Checking local connection…</p>
<button id="refresh">Refresh status</button>
<p><a id="canvasLink" href="#">Open interactive Research Canvas</a> — full canvas proposals,
preview and human approval workflow (no direct browser research writes)</p>
<fieldset><legend>Create a draft proposal</legend>
<label>Operation <select id="operation">
<option value="add-item">Create research item</option>
<option value="add-relation">Link two items</option>
<option value="set-status">Suggest noncritical status change</option>
</select></label>
<p><label>Reason (at least 8 characters)<input id="reason" size="55" value="Explore a potential research direction"></label></p>
<p><label>Parameters (JSON object)<textarea id="params">{"type":"Idea","title":"Candidate direction","module":"topic"}</textarea></label></p>
<button id="submit">Queue proposal (no approval)</button>
</fieldset>
<h2>Result</h2><pre id="output" aria-live="polite"></pre>
<small>Project state is canonical. Session token stays in this browser tab;
no outbound requests or third-party assets. Missing bridge means read-only.</small>
<script nonce="__NONCE__">
"use strict";
const token=decodeURIComponent(location.hash.replace(/^#token=/,""));
history.replaceState(null,"",location.pathname);
let revision=null;
const output=document.getElementById("output");
document.getElementById("canvasLink").href="/canvas#token="+encodeURIComponent(token);
function show(value){output.textContent=typeof value==="string"?value:JSON.stringify(value,null,2);}
async function request(path,method="GET",payload=null){
  if(!token) throw Error("No access token; reopen the URL printed in your terminal.");
  const options={method,cache:"no-store",headers:{"X-RN-Token":token}};
  if(payload!==null){options.headers["Content-Type"]="application/json";options.body=JSON.stringify(payload);}
  const res=await fetch(path,options);
  const data=await res.json();
  if(!res.ok) throw Error(data.error || "Request failed "+res.status);
  return data;
}
async function refresh(){
  try{
    const data=await request("/api/state");
    revision=data.revision;
    document.getElementById("status").textContent=
      "Project "+data.project_name+" · revision "+data.revision+
      " · "+data.items.length+" items · canonical writes require terminal approval";
  }catch(err){document.getElementById("status").textContent="Read-only or disconnected: "+err.message;}
}
document.getElementById("refresh").addEventListener("click",refresh);
document.getElementById("operation").addEventListener("change",ev=>{
  const examples={
    "add-item":{type:"Idea",title:"Candidate direction",module:"topic"},
    "add-relation":{source:"IDEA-0001",target:"BR-0001",relation:"member-of"},
    "set-status":{item_id:"IDEA-0001",field:"workflow_status",value:"in-progress"}
  };
  document.getElementById("params").value=JSON.stringify(examples[ev.target.value],null,2);
});
document.getElementById("submit").addEventListener("click",async()=>{
  try{
    if(revision===null) throw Error("Refresh state before proposing an edit.");
    const data=await request("/api/proposals","POST",{
      operation:document.getElementById("operation").value,
      reason:document.getElementById("reason").value,
      params:JSON.parse(document.getElementById("params").value),
      expected_revision:revision
    });
    show({status:"Pending terminal approval (NOT APPLIED)",...data,
      next_step:"Use local_editor.py inspect /PROJECT/ROOT "+data.proposal_id+
                " then local_editor.py approve /PROJECT/ROOT "+data.proposal_id});
  }catch(err){show("No changes applied: "+err.message);}
});
refresh();
</script></html>"""


def state_view(root):
    state = load(root)
    validate_state(state, strict=True)
    return {
        "project_id": state["project"]["project_id"],
        "project_name": state["project"]["name"],
        "revision": state["project"]["revision"],
        "schema_version": state["project"]["schema_version"],
        "read_only_without_terminal_approval": True,
        "items": [{"id":i["id"],"title":i["title"],"type":i["type"],
                   "module":i["module"],"lifecycle_status":i["lifecycle_status"],
                   "impact_status":i["impact_status"]} for i in state["items"]],
        "relations": state["relations"],
    }


def create_handler(root, token, port):
    """Inject a fixed project root; requests never accept a filesystem path."""
    allowed_host = f"127.0.0.1:{port}"
    allowed_origin = f"http://{allowed_host}"

    class Handler(BaseHTTPRequestHandler):
        server_version = "ResearchNavigatorLocal/0.2"
        sys_version = ""

        def log_message(self, fmt, *args):
            # No HTTP logs: never leak token, proposal text or research contents.
            return

        def _headers(self, code, *, content_type="application/json", nonce=None):
            self.send_response(code)
            self.send_header("Content-Type", content_type + "; charset=utf-8")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Cross-Origin-Resource-Policy", "same-origin")
            self.send_header("Cross-Origin-Opener-Policy", "same-origin")
            if nonce is not None:
                self.send_header("Content-Security-Policy",
                                 "default-src 'none'; script-src 'nonce-"+nonce+
                                 "'; style-src 'unsafe-inline'; connect-src 'self'; "
                                 "base-uri 'none'; frame-ancestors 'none'; form-action 'none'")
            else:
                self.send_header("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'")
            self.end_headers()

        def _send(self, status, data):
            raw = json.dumps(data, ensure_ascii=False).encode("utf-8")
            self._headers(status)
            self.wfile.write(raw)

        def _guard(self, *, mutation=False):
            # Reject DNS rebinding, proxy host aliases and browser cross-origin fetches.
            if self.headers.get("Host") != allowed_host:
                self._send(403, {"error":"Invalid Host"})
                return False
            if self.headers.get("X-RN-Token") != token:
                self._send(403, {"error":"Invalid local capability"})
                return False
            origin = self.headers.get("Origin")
            if origin is not None and origin != allowed_origin:
                self._send(403, {"error":"Cross-origin requests forbidden"})
                return False
            if mutation and origin != allowed_origin:
                self._send(403, {"error":"Same-origin browser request required"})
                return False
            if self.headers.get("Sec-Fetch-Site", "same-origin") not in ("same-origin", "none"):
                self._send(403, {"error":"Cross-site request forbidden"})
                return False
            return True

        def do_GET(self):
            if self.path == "/dashboard/index.html":
                # The response is a shell with no scientific data, even before
                # token verification; authenticated JS requests /api/dashboard.
                if self.headers.get("Host") != allowed_host:
                    return self._send(403, {"error":"Invalid Host"})
                if self.headers.get("Sec-Fetch-Site","same-origin") not in ("same-origin","none"):
                    return self._send(403, {"error":"Cross-site request forbidden"})
                template = Path(__file__).resolve().parent.parent/"templates"/"dashboard.html"
                nonce = secrets.token_urlsafe(18)
                page = (template.read_text(encoding="utf-8")
                        .replace("__EMBEDDED_STATE_JSON__", "null")
                        .replace("__DASHBOARD_NONCE__", nonce))
                self._headers(200, content_type="text/html", nonce=nonce)
                self.wfile.write(page.encode("utf-8"))
                return
            if self.path == "/api/dashboard":
                if not self._guard():
                    return
                try:
                    state = load(root)
                    validate_state(state, strict=True)
                    self._send(200, {
                        "project":state["project"],"items":state["items"],
                        "relations":state["relations"],"sources":state["sources"],
                        "events":state["events"][-80:],"generated_at":now(),
                        "interactive_edits":False,
                        "graph_engine":"native SVG fallback (Archify schema not assumed)"})
                except (ResearchError,ValueError,OSError) as exc:
                    self._send(409,{"error":str(exc)})
                return
            if self.path == "/canvas":
                # Public shell contains NO project data. Only authenticated
                # X-RN-Token /api/graph requests return project information.
                if self.headers.get("Host") != allowed_host:
                    return self._send(403, {"error":"Invalid Host"})
                if self.headers.get("Sec-Fetch-Site","same-origin") not in ("same-origin","none"):
                    return self._send(403, {"error":"Cross-site request forbidden"})
                template = Path(__file__).resolve().parent.parent/"templates"/"research_canvas.html"
                nonce = secrets.token_urlsafe(18)
                empty_graph = {"project_id":"","project_revision":0,"nodes":[],"edges":[]}
                empty_views = {"schema_version":"canvas-views-v1","project_id":"","views":{}}
                page = (template.read_text(encoding="utf-8")
                        .replace("__RN_GRAPH_JSON__",embedded_json(empty_graph))
                        .replace("__RN_VIEWS_JSON__",embedded_json(empty_views))
                        .replace("__CANVAS_NONCE__",nonce))
                raw = page.encode("utf-8")
                self._headers(200,content_type="text/html",nonce=nonce)
                self.wfile.write(raw)
                return
            if self.path == "/api/graph":
                if not self._guard():
                    return
                try:
                    # Canonical source of truth, not cached static snapshot.
                    self._send(200,project_graph(load(root),limit=None))
                except (ResearchError, ValueError, OSError) as e:
                    self._send(409, {"error":str(e)})
                return
            if self.path.startswith("/api/proposals/"):
                if not self._guard():
                    return
                pid = self.path[len("/api/proposals/"):]
                if not re.fullmatch(r"[0-9a-f]{32}",pid):
                    return self._send(404,{"error":"Not found"})
                try:
                    self._send(200,proposal_status(root,pid))
                except (ResearchError,OSError) as e:
                    self._send(404,{"error":str(e)})
                return
            if self.path == "/":
                if self.headers.get("Host") != allowed_host:
                    return self._send(403, {"error":"Invalid Host"})
                nonce = secrets.token_urlsafe(18)
                page = PAGE.replace("__NONCE__",nonce).encode("utf-8")
                self._headers(200,content_type="text/html",nonce=nonce)
                self.wfile.write(page)
                return
            if self.path == "/api/state":
                if not self._guard():
                    return
                try:
                    self._send(200,state_view(root))
                except (ResearchError, ValueError, OSError) as e:
                    self._send(409,{"error":str(e)})
                return
            self._send(404,{"error":"Not found"})

        def do_POST(self):
            if self.path not in ("/api/proposals","/api/preview"):
                return self._send(404,{"error":"No HTTP approval endpoint"})
            if not self._guard(mutation=True):
                return
            if self.headers.get("Content-Type") != "application/json":
                return self._send(415,{"error":"Content-Type must be application/json"})
            try:
                length = int(self.headers.get("Content-Length","0"))
            except ValueError:
                length = 0
            if length < 1 or length > 16384 or self.headers.get("Transfer-Encoding"):
                return self._send(413,{"error":"Invalid request size"})
            try:
                raw = self.rfile.read(length)
                data = json.loads(raw)
                if self.path == "/api/preview":
                    return self._send(200,preview_proposal(root,data))
                result = queue_proposal(root,data)
                return self._send(202,result)
            except (UnicodeDecodeError,json.JSONDecodeError):
                return self._send(400,{"error":"Malformed JSON"})
            except (ResearchError, ValueError) as e:
                status = 409 if "stale" in str(e) or "transaction" in str(e) else 400
                return self._send(status,{"error":str(e)})
            except OSError:
                return self._send(500,{"error":"Local filesystem error"})

        def do_OPTIONS(self):
            self._send(405,{"error":"No CORS support"})

        def do_PUT(self):
            self._send(405,{"error":"Method not allowed"})

        def do_DELETE(self):
            self._send(405,{"error":"Method not allowed"})

    return Handler


def serve(root, port=0):
    from pathlib import Path
    root = Path(root).expanduser().resolve(strict=True)
    state_view(root)
    token = secrets.token_urlsafe(32)
    # Reserve a server then set the handler with the selected port. Only bind loopback.
    server = ThreadingHTTPServer(("127.0.0.1",port), BaseHTTPRequestHandler)
    actual_port = server.server_address[1]
    server.RequestHandlerClass = create_handler(root,token,actual_port)
    server.daemon_threads = True
    try:
        print(f"Research Navigator local bridge (proposals only):")
        print(f"http://127.0.0.1:{actual_port}/#token={token}")
        print("Keep this URL private. Closing the terminal stops the bridge.")
        sys.stdout.flush()
        server.serve_forever(poll_interval=0.2)
    finally:
        server.server_close()


def main():
    p = argparse.ArgumentParser(description="Research Navigator: loopback proposal bridge and terminal approval")
    sub = p.add_subparsers(dest="operation",required=True)
    sp = sub.add_parser("serve")
    sp.add_argument("root")
    sp.add_argument("--port",type=int,default=0,help="0 chooses a random loopback port")
    sp = sub.add_parser("inspect")
    sp.add_argument("root")
    sp.add_argument("proposal_id")
    sp = sub.add_parser("approve")
    sp.add_argument("root")
    sp.add_argument("proposal_id")
    sp = sub.add_parser("reject")
    sp.add_argument("root")
    sp.add_argument("proposal_id")
    args = p.parse_args()
    try:
        if args.operation == "serve":
            if not 0 <= args.port <= 65535:
                raise ResearchError("port out of range")
            serve(args.root,args.port)
            return
        proposal = inspect_proposal(args.root,args.proposal_id)
        print(json.dumps(proposal,ensure_ascii=False,indent=2))
        # Terminal operator sees the same before/after and downstream impact
        # that the browser preview showed, before confirming any mutation.
        preview_error = None
        if proposal.get("status") == "pending":
            try:
                payload = {key:proposal[key] for key in
                           ("operation","params","reason","expected_revision")}
                preview = preview_proposal(args.root,payload)
                print("\\nSIMULATED BEFORE / AFTER / IMPACT (NOT APPLIED):")
                print(json.dumps(preview,ensure_ascii=False,indent=2))
            except (ResearchError,KeyError) as exc:
                preview_error = str(exc)
                print("Preview unavailable (stale or invalid): "+preview_error)
        if args.operation == "inspect":
            return
        if args.operation == "approve" and preview_error:
            raise ResearchError("Cannot approve without a valid current preview: "+preview_error)
        if not sys.stdin.isatty():
            raise ResearchError("Approval/rejection must be performed from an interactive local terminal")
        phrase = "APPROVE "+args.proposal_id if args.operation=="approve" else "REJECT "+args.proposal_id
        print(f"To {args.operation}, type exactly: {phrase}")
        answer = input("Confirmation: ")
        if answer != phrase:
            raise ResearchError("Explicit confirmation does not match; nothing applied")
        if args.operation == "approve":
            print(json.dumps(approve_proposal(args.root,args.proposal_id,confirmed=True),
                             ensure_ascii=False,indent=2))
        else:
            from rn_proposals import reject_proposal
            print(json.dumps(reject_proposal(args.root,args.proposal_id,confirmed=True),
                             ensure_ascii=False,indent=2))
    except (ResearchError,OSError,ValueError) as exc:
        print("Local bridge error: "+str(exc),file=sys.stderr)
        raise SystemExit(2)


if __name__=="__main__":
    main()
