"""Chromium offline interview choices, Other, legacy, and safe draft UX."""
import sys
import tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from rn_core import init_project,load
from rn_interview import start,add_questions,read
from build_canvas import build_canvas
from playwright.sync_api import sync_playwright

def question(title,structured=True):
    q={"text":title,"why":"Define one research objective","options":"A or B",
       "recommendation":"Prefer explicit transfer metric",
       "lowest_cost_check":"Synthetic pilot","depends_on":[]}
    if structured:
        q["choices"]=[
            {"id":"metric","label":"提高精度","description":"以 F1 优先"},
            {"id":"budget","label":"降低预算","description":"控制实验成本"}]
        q["recommended_choice_id"]="metric"
    return q

def main():
    with tempfile.TemporaryDirectory(prefix="v042-choice-ui-") as tmp:
        root=Path(tmp)/"project"
        init_project(root,"SYNTHETIC choice UI")
        start(root,topic="SYNTHETIC objective")
        add_questions(root,[question('<script>window.pwned=true</script>'),question("旧版题目",False)])
        before=read(root)
        scientific=load(root)
        canvas=build_canvas(root)
        html=(canvas.parent/"interview.html")
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True)
            page=browser.new_page(viewport={"width":1200,"height":850})
            errors=[]
            page.on("pageerror",lambda e:errors.append(str(e)))
            page.goto(html.as_uri())
            assert page.locator("#ready article").count()==2
            one=page.locator("#ready article").first
            assert one.get_by_role("radio").count()==3
            assert "<script>window.pwned=true</script>" in one.inner_text()
            assert not page.evaluate("Boolean(window.pwned)")
            button=one.get_by_role("button",name="生成回答草案（不会保存）")
            assert button.is_disabled()
            one.get_by_role("radio",name="其他／自定义").check()
            assert one.locator("textarea").is_visible()
            assert button.is_disabled()
            one.locator("textarea").fill("新的研究目标：泛化稳健性")
            assert button.is_enabled()
            button.click()
            draft=one.locator("pre.draft")
            assert draft.is_visible()
            assert "其他／自定义：新的研究目标" in draft.inner_text()
            assert "请将这段内容粘贴到 Codex" in draft.inner_text()
            one.get_by_role("radio",name="提高精度").check()
            assert not one.locator("textarea").is_visible()
            button.click()
            assert "选择：metric" in draft.inner_text()
            page.set_viewport_size({"width":390,"height":800})
            page.reload()
            assert page.locator("#ready article").first.is_visible()
            assert not errors, errors
            browser.close()
        assert read(root)==before
        assert load(root)==scientific
    assert not Path(tmp).exists()
    print("PASS: offline choice/Other drafts, valid mobile radios, no writes, sanitized input, cleanup")

if __name__=="__main__":
    main()
