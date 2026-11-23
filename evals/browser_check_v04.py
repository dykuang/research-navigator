"""Chromium smoke: generated v0.4 report controls + inherited canvas functionality."""
import sys
from pathlib import Path
import tempfile

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from rn_core import init_project,add_item,change_status
from build_canvas import build_canvas

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    raise SystemExit("Install playwright and Chromium in CI or run in a supported browser environment")

def main():
    with tempfile.TemporaryDirectory(prefix="v04-canvas-fixture-") as tmp:
        root=Path(tmp)/"project"
        init_project(root,"SYNTHETIC UAT - NO REAL SCIENCE","Toy question; no scientific claims")
        h=add_item(root,kind="Hypothesis",title="SYNTHETIC uncertain hypothesis",module="topic")
        parked=add_item(root,kind="Idea",title="SYNTHETIC archived route",module="pivot")
        change_status(root,parked["id"],"lifecycle_status","parked",
                      "Toy condition failed",actor="user",
                      failure_scope="toy dataset",revival_triggers="new protocol")
        canvas=build_canvas(root)
        report=canvas.parent/"decisions.html"
        assert report.exists()
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True)
            page=browser.new_page(viewport={"width":1250,"height":850})
            errs=[]
            page.on("pageerror",lambda e:errs.append(str(e)))
            page.goto(report.as_uri())
            page.wait_for_load_state("load")
            assert "SYNTHETIC UAT" in page.locator("#project").inner_text()
            assert page.locator("#gaps .card").count()>=1
            assert page.locator("#checks .card").count()>=1
            assert page.locator("#archive .card").count()==1
            page.locator("#search").fill("UNLIKELYMATCH")
            assert page.locator("#gaps .card").count()==0
            page.locator("#search").fill("")
            page.locator("#severity").select_option("review")
            assert page.locator("#gaps .card").count()>=1
            page.locator("header a").click()
            assert "Research Canvas" in page.title()
            assert "decisions.html" in page.locator("header").inner_html()
            page.set_viewport_size({"width":390,"height":844})
            page.goto(report.as_uri())
            assert page.locator("#checks").is_visible()
            assert not errs,repr(errs)
            browser.close()
    print("PASS: offline decision canvas, filters, responsive view, archive isolation, no JS errors; temporary project cleaned")

if __name__=="__main__":
    main()
