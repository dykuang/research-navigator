#!/usr/bin/env python3
"""Real Chromium interaction smoke for the offline v0.2 Infinite Research Canvas.

Optional manual test, and runnable in CI's browser job after installing Playwright.
The HTTP server serves only a synthetic generated project; no external services.
"""
from __future__ import annotations
from contextlib import contextmanager
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sys
import tempfile
import threading
from playwright.sync_api import sync_playwright

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from rn_core import init_project,add_item,add_relation,load
from rn_domain import create_branch,create_milestone
from build_dashboard import build

@contextmanager
def local_site(root):
    class Quiet(SimpleHTTPRequestHandler):
        def log_message(self,format,*args):return
    handler=partial(Quiet,directory=str(root))
    server=ThreadingHTTPServer(("127.0.0.1",0),handler)
    t=threading.Thread(target=server.serve_forever,daemon=True);t.start()
    try:yield "http://127.0.0.1:"+str(server.server_address[1])
    finally:
        server.shutdown();server.server_close();t.join(timeout=4)

def main():
    with tempfile.TemporaryDirectory(prefix="rn-canvas-browser-") as temp:
        root=Path(temp)
        init_project(root,"SYNTHETIC browser canvas")
        base=add_item(root,kind="Baseline",title="Shared baseline",module="literature")
        branches=[create_branch(root,"Synthetic branch "+str(i),"Research "+str(i),["Stop if invalid"]) for i in range(3)]
        for b in branches:add_relation(root,base["id"],b["id"],"member-of")
        milestone=create_milestone(root,"Milestone",["Synthetic evidence"])
        add_relation(root,branches[0]["id"],milestone["id"],"contributes-to")
        for i in range(18):
            add_item(root,kind="Idea",title="Idea synthetic "+str(i),module="topic")
        original=load(root)
        build(root)
        with local_site(root) as origin,sync_playwright() as p:
            browser=p.chromium.launch(headless=True)
            page=browser.new_page(viewport={"width":1440,"height":920},accept_downloads=True)
            errors=[]
            page.on("pageerror",lambda error:errors.append(str(error)))
            page.goto(origin+"/research/canvas/index.html",wait_until="load")
            page.locator(".node").first.wait_for()
            assert page.locator(".node").count()==23
            assert page.locator("#minimap rect").count()>=23
            assert page.locator("#inspector").count()==1

            # Zoom and pan through real browser pointer events.
            initial=page.locator("#world").get_attribute("style")
            page.locator("#zoomIn").click()
            assert page.locator("#world").get_attribute("style")!=initial
            node=page.locator('[data-node="item:IDEA-0001"]')
            start=node.get_attribute("style")
            rect=node.bounding_box()
            assert rect is not None
            page.mouse.move(rect["x"]+40,rect["y"]+35)
            page.mouse.down()
            page.mouse.move(rect["x"]+105,rect["y"]+79,steps=6)
            page.mouse.up()
            after=page.locator('[data-node="item:IDEA-0001"]').get_attribute("style")
            assert after!=start,("Card did not drag",start,after)

            # Save/reload in same browser origin restores view coordinates.
            page.locator("#saveLayout").click()
            assert "布局已保存在此浏览器" in page.locator("#notice").inner_text()
            page.reload(wait_until="load")
            assert page.locator('[data-node="item:IDEA-0001"]').get_attribute("style")==after
            page.locator("#view").select_option("routes")
            assert page.locator(".node").count()<23
            page.locator("#view").select_option("all")
            page.locator("#search").fill("IDEA-0001")
            assert page.locator(".node").count()==1
            page.locator("#search").fill("")

            page.locator('[data-node="item:IDEA-0001"]').click()
            assert "IDEA-0001" in page.locator("#details").inner_text()
            page.locator("#pinGroup").click()
            assert "已固定模块组" in page.locator("#notice").inner_text()
            with page.expect_download() as downloaded:
                page.locator("#exportLayout").click()
            payload=json.loads(Path(downloaded.value.path()).read_text(encoding="utf-8"))
            assert payload["project_id"]==original["project"]["project_id"]
            assert payload["pinned_groups"]
            with page.expect_download() as svgdownload:
                page.locator("#exportSVG").click()
            assert "<svg" in Path(svgdownload.value.path()).read_text(encoding="utf-8")
            page.goto(origin+"/research/dashboard/index.html",wait_until="load")
            page.locator('[data-view="graph"]').click()
            assert page.locator("#relationSvg g").count()>=23
            assert not errors, errors
            assert load(root)==original, "Browser layout operations mutated research state"
            browser.close()
    print("PASS: Chromium pan/zoom/node drag, minimap, filters, local layout save/reload, exported JSON/SVG, classic dashboard, no JS errors or canonical state edits")

if __name__=="__main__":
    main()
