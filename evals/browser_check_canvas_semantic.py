#!/usr/bin/env python3
"""Real Chromium #10 smoke against a protected localhost Bridge and human-gated proposals."""
from __future__ import annotations

from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import sys
import tempfile
import threading

from playwright.sync_api import sync_playwright, expect

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from rn_core import init_project, add_item, load, change_status
from local_editor import create_handler
from rn_proposals import approve_proposal


def main():
    with tempfile.TemporaryDirectory(prefix="rn-semantic-browser-") as temp:
        root=Path(temp)
        init_project(root,"SYNTHETIC live canvas")
        idea=add_item(root,kind="Idea",title="Existing synthetic idea",module="topic")
        archived=add_item(root,kind="Idea",title="Synthetic old route",module="topic")
        change_status(root,archived["id"],"lifecycle_status","parked",
                      "Human archived toy direction",actor="user",
                      failure_scope="Toy negative case",revival_triggers="New toy observations")
        before=load(root)
        token="SYNTHETIC-PRIVATE-CAPABILITY"
        server=ThreadingHTTPServer(("127.0.0.1",0),object)
        port=server.server_address[1]
        server.RequestHandlerClass=create_handler(root,token,port)
        server.daemon_threads=True
        thread=threading.Thread(target=server.serve_forever,daemon=True)
        thread.start()
        base=f"http://127.0.0.1:{port}"
        try:
            with sync_playwright() as p:
                browser=p.chromium.launch(headless=True)
                page=browser.new_page(viewport={"width":1510,"height":940})
                errors=[]
                page.on("pageerror",lambda exc:errors.append(str(exc)))

                # Unauthenticated HTML response must not embed sensitive project graph.
                result=page.request.get(base+"/canvas")
                assert result.status==200
                shell=result.text()
                assert "Existing synthetic idea" not in shell
                assert "SYNTHETIC live canvas" not in shell

                page.goto(base+"/canvas#token="+token,wait_until="load")
                page.locator('[data-node="item:'+idea["id"]+'"]').wait_for()
                page.locator("#editMode").get_by_text("本机受控提案模式") if False else None
                assert "本机受控提案模式" in page.locator("#editMode").inner_text()
                assert page.locator(".node").count()==2
                # Browser refresh keeps the same-tab capability without putting it
                # back into the URL fragment. No secret stored in canonical state.
                page.reload(wait_until="load")
                page.locator('[data-node="item:'+idea["id"]+'"]').wait_for()
                assert "本机受控提案模式" in page.locator("#editMode").inner_text()
                assert "#token=" not in page.url
                initial=load(root)

                page.locator("#semanticOperation").select_option("add-branch")
                page.locator("#semanticParams").fill(json.dumps({
                    "title":"Synthetic candidate branch","goal":"Compare synthetic alternatives",
                    "stop_conditions":["No reproducible improvement"],"module":"topic"
                }))
                page.locator("#semanticReason").fill("Human review of novel research direction")
                page.locator("#previewSemantic").click()
                expect(page.locator("#queueSemantic")).to_be_enabled(timeout=5000)
                preview=json.loads(page.locator("#semanticDiff").inner_text())
                assert preview["accepted"] is False
                assert preview["scientifically_validated"] is False
                assert preview["impact"][0]["after"]["type"]=="ResearchBranch"
                assert load(root)==initial, "Preview mutated canonical research state"

                page.locator("#queueSemantic").click()
                expect(page.locator("#semanticState")).to_contain_text("待终端审批",timeout=5000)
                assert load(root)==initial, "Queued proposal mutated research state"
                status=page.locator("#semanticState").inner_text()
                import re
                pid=re.search(r"[0-9a-f]{32}",status).group()
                assert pid
                approve_proposal(root,pid,confirmed=True)  # Emulates terminal-reviewed approval in smoke.
                page.locator("#refreshSemantic").click()
                page.locator('[data-node="item:BR-0001"]').wait_for()
                assert "状态：applied" in page.locator("#semanticState").inner_text()
                assert load(root)["project"]["revision"]==initial["project"]["revision"]+1
                assert any(e.get("proposal_id")==pid for e in load(root)["events"])

                # Related archived entities cannot be linked into positive planning.
                page.locator("#semanticOperation").select_option("add-relation")
                page.locator("#semanticParams").fill(json.dumps({
                    "source":archived["id"],"target":"BR-0001","relation":"member-of"
                }))
                page.locator("#previewSemantic").click()
                expect(page.locator("#semanticDiff")).to_contain_text("预览拒绝",timeout=5000)
                assert page.locator("#queueSemantic").is_disabled()
                assert "archived" in page.locator("#semanticDiff").inner_text()

                # No browser approval endpoint can commit changes.
                bad=page.request.post(base+"/api/approve",data="{}",headers={
                    "X-RN-Token":token,"Origin":base,"Content-Type":"application/json"})
                assert bad.status==404
                assert not errors,errors
                browser.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)
    print("PASS: Chromium authenticated live graph, preview, pending queue, explicit terminal-approved refresh, archive guard, no HTTP approval")


if __name__=="__main__":
    main()
