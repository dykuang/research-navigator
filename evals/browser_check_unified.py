#!/usr/bin/env python3
"""Real Chromium v0.6 unified sockets, modal and approval smoke; temporary data only."""
from pathlib import Path
import json
import sys
import tempfile
import threading
from http.server import ThreadingHTTPServer

from playwright.sync_api import sync_playwright, expect

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from rn_core import init_project, add_item, load
from rn_domain import create_milestone, create_session, session_entity_link
from rn_interview import start, add_questions, answer, read
from rn_proposals import approve_proposal
from unified_graph import unified_graph, read_context
from build_canvas import build_canvas
from local_editor import create_handler

def question():
    return {"text":"Which falsifiable research objective?","why":"Defines limits",
            "options":"accuracy vs cost",
            "recommendation":"Start with a small baseline",
            "lowest_cost_check":"Toy comparison",
            "depends_on":[],
            "choices":[{"id":"a","label":"Accuracy","description":"Improve F1"},
                       {"id":"b","label":"Cost","description":"Less compute"}]}

def main():
    with tempfile.TemporaryDirectory(prefix="rn-v06-unified-browser-") as folder:
        root=Path(folder)
        init_project(root,"SYNTHETIC unified workspace")
        idea=add_item(root,kind="Idea",title="Synthetic research idea",module="topic")
        milestone=create_milestone(root,"Synthetic scientific milestone",["Result documented"])
        session=create_session(root,"deepseek","toy-workspace","synthetic-session-ref")
        session_entity_link(root,session["id"],idea["id"],"discussion")
        start(root,topic="Synthetic Grilling round")
        add_questions(root,[question()])
        interview=read(root)["interview_id"]
        answer(root,"Q-0001",choice_id="other",
               custom_answer="More robust transfer",
               supplement="Only synthetic discussion")
        original=load(root)
        canvas=build_canvas(root)
        assert (canvas.parent/"unified.html").exists()
        graph=unified_graph(root)
        assert len(graph["nodes"])>=7
        source="question:"+interview+"-Q-0001"
        target="item:"+idea["id"]
        server=ThreadingHTTPServer(("127.0.0.1",0),object)
        port=server.server_address[1]
        token="SYNTHETIC-V06-CAPABILITY"
        server.RequestHandlerClass=create_handler(root,token,port)
        server.daemon_threads=True
        thread=threading.Thread(target=server.serve_forever,daemon=True)
        thread.start()
        try:
            with sync_playwright() as playwright:
                browser=playwright.chromium.launch(headless=True)
                page=browser.new_page(viewport={"width":1450,"height":920})
                errors=[]
                page.on("pageerror",lambda e:errors.append(str(e)))
                base=f"http://127.0.0.1:{port}"
                # No project secrets or node text in unguarded shell.
                shell=page.request.get(base+"/unified")
                assert shell.status==200
                assert "More robust transfer" not in shell.text()
                forbidden=page.request.get(base+"/api/unified-graph")
                assert forbidden.status==403
                page.goto(base+"/unified#token="+token)
                page.locator('[data-node="'+source+'"]').wait_for()
                expect(page.locator("#projectName")).to_contain_text("节点")
                assert "Unified Research Node Editor" in page.title()
                assert page.locator('[data-node="criterion:'+milestone["id"]+'-C-001"]').count()==1
                assert page.locator('[data-node="session:'+session["id"]+'"]').count()==1
                page.locator("#view").select_option("interview")
                assert page.locator('[data-node="'+source+'"]').is_visible()
                page.locator("#view").select_option("all")
                # Grilling cards are included in the SAME editor. Drafts never write.
                before_interview=read(root)
                page.locator('[data-node="'+source+'"]').click()
                editor=page.locator("#details .interview-choices")
                expect(editor).to_be_visible()
                editor.get_by_role("radio",name=__import__("re").compile("其他")).check()
                editor.locator('textarea[aria-label="Grilling 自定义答案"]').fill("Original alternative hypothesis")
                editor.locator('textarea[aria-label="Grilling 补充说明"]').fill("Optional boundary condition")
                editor.get_by_role("button",name="生成回答草案（不会保存）").click()
                expect(editor.locator("pre")).to_contain_text("Original alternative hypothesis")
                expect(editor.locator("pre")).to_contain_text("Optional boundary condition")
                assert read(root)==before_interview
                page.locator("#sessionProviderFilter").select_option("deepseek")
                page.locator('[data-node="item:'+idea["id"]+'"]').click()
                expect(page.locator("#sessionRecords")).to_contain_text("deepseek")
                page.locator("#sessionProviderFilter").select_option("")
                page.locator("#search").fill("Scientific Milestone".lower())
                assert page.locator(".node").count()>=1
                page.locator("#search").fill("")
                # Type-safe port-to-port connection. Preview/queue cannot mutate science.
                page.locator('[data-output-node="'+source+'"]').click()
                page.locator('[data-input-node="'+target+'"]').click()
                assert "link-context"==page.locator("#semanticOperation").input_value()
                params=json.loads(page.locator("#semanticParams").input_value())
                assert params["from"]==source and params["to"]==target
                assert params["relation"]=="addresses"
                page.locator("#previewSemantic").click()
                expect(page.locator("#queueSemantic")).to_be_enabled()
                assert load(root)==original
                page.locator("#queueSemantic").click()
                expect(page.locator("#semanticState")).to_contain_text("待终端审批")
                assert read_context(root)["revision"]==0
                pending=sorted((root/"research"/"canvas"/"proposals").glob("*.json"))
                assert len(pending)==1
                pid=pending[0].stem
                # Test simulates an operator's *terminal-reviewed* explicit approval.
                approve_proposal(root,pid,confirmed=True)
                page.locator("#refreshSemantic").click()
                expect(page.locator("#contextLinks option")).to_have_count(2)
                assert read_context(root)["revision"]==1
                assert load(root)==original
                # Explicit unlink is also human gated.
                page.locator("#contextLinks").select_option(index=1)
                page.locator("#prepareUnlinkContext").click()
                page.locator("#previewSemantic").click()
                expect(page.locator("#queueSemantic")).to_be_enabled()
                page.locator("#queueSemantic").click()
                expect(page.locator("#semanticState")).to_contain_text("待终端审批")
                pending=[p for p in (root/"research"/"canvas"/"proposals").glob("*.json")
                         if json.loads(p.read_text(encoding="utf-8"))["status"]=="pending"]
                assert len(pending)==1
                approve_proposal(root,pending[0].stem,confirmed=True)
                page.locator("#refreshSemantic").click()
                assert read_context(root)["links"]==[]
                assert load(root)==original
                # Link a provider-specific SessionRef to the Grilling question.
                page.locator('[data-output-node="session:'+session["id"]+'"]').click()
                page.locator('[data-input-node="'+source+'"]').click()
                params=json.loads(page.locator("#semanticParams").input_value())
                assert params["relation"]=="discussed-in-session"
                assert params["from"]=="session:"+session["id"]
                page.locator("#previewSemantic").click()
                expect(page.locator("#queueSemantic")).to_be_enabled()
                page.locator("#queueSemantic").click()
                expect(page.locator("#semanticState")).to_contain_text("待终端审批")
                pending=[p for p in (root/"research"/"canvas"/"proposals").glob("*.json")
                         if json.loads(p.read_text(encoding="utf-8"))["status"]=="pending"]
                assert len(pending)==1
                approve_proposal(root,pending[0].stem,confirmed=True)
                page.locator("#refreshSemantic").click()
                page.locator('[data-node="'+source+'"]').click()
                page.locator("#sessionProviderFilter").select_option("deepseek")
                expect(page.locator("#sessionRecords")).to_contain_text("deepseek")
                page.locator("#sessionProviderFilter").select_option("")
                assert load(root)==original
                # Narrow viewport keeps inspector accessible.
                page.set_viewport_size({"width":385,"height":800})
                page.locator("#mobileInspectorToggle").click()
                expect(page.locator("#inspector")).to_have_class(__import__("re").compile("open"))
                page.locator("#closeMobileInspector").click()
                assert not errors,errors
                browser.close()
        finally:
            server.shutdown();server.server_close();thread.join(timeout=5)
    assert not Path(folder).exists(),"synthetic project not cleaned"
    print("PASS: unified Chromium sockets, full protected proposal cycle, read-only offline, mobile, SessionRef and cleanup")

if __name__=="__main__":
    main()
