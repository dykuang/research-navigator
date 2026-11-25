"""Offline interview HTML browser smoke; synthetic fixtures auto removed."""
import sys
import tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from rn_core import init_project
from rn_interview import start,add_questions,answer,request_exit,confirm_exit
from build_canvas import build_canvas
from playwright.sync_api import sync_playwright

def main():
    with tempfile.TemporaryDirectory(prefix="rn-v041-browser-") as dirname:
        root=Path(dirname)/"project"
        init_project(root,"SYNTHETIC interview UI")
        start(root,topic="SYNTHETIC HTML topic")
        add_questions(root,[{"text":'<script>window.pwned=true</script>',
                            "why":"Evaluate risk",
                            "options":"A/B",
                            "recommendation":"Review",
                            "lowest_cost_check":"Toy check"}])
        path=build_canvas(root)
        page_path=path.parent/"interview.html"
        assert page_path.exists()
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True)
            page=browser.new_page(viewport={"width":1200,"height":800})
            errors=[]
            page.on("pageerror",lambda e:errors.append(str(e)))
            page.goto(page_path.as_uri())
            assert page.title()=="Research Navigator · Persistent Interview"
            assert "SYNTHETIC HTML topic" in page.locator("#topic").inner_text()
            assert page.locator("#ready article").count()==1
            assert "<script>window.pwned=true</script>" in page.locator("#ready").inner_text()
            assert page.evaluate("Boolean(window.pwned)") is False
            assert "READ ONLY" in page.locator("main").inner_text()
            page.locator("header a").click()
            assert "Research Canvas" in page.title()
            assert page.locator('header a[href="interview.html"]').count()==1
            page.set_viewport_size({"width":380,"height":760})
            page.goto(page_path.as_uri())
            assert page.locator("#ready").is_visible()
            assert not errors, errors
            browser.close()
    assert not Path(dirname).exists()
    print("PASS: offline interview canvas, escaped content, mobile visibility, no JS errors, fixture cleaned")

if __name__=="__main__":
    main()
