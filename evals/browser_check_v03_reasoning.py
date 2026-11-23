#!/usr/bin/env python3
"""Real Chromium v0.3 reasoning inspector smoke, synthetic-only fixtures.

Requires playwright and Chromium; run in the v0.3 browser CI job.
"""
from pathlib import Path
import sys
import tempfile

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from browser_check_canvas import local_site
from rn_core import init_project, add_item, load
from rn_reasoning import create_run, record_run, create_decision_trace
from rn_domain import link_evidence
from build_dashboard import build


def main():
    with tempfile.TemporaryDirectory(prefix="rn-v03-browser-") as temp:
        root=Path(temp)
        init_project(root,"SYNTHETIC FIXTURE · Reasoning Canvas")
        exp=add_item(root,kind="Experiment",title="Toy evaluation protocol",module="experiment")
        claim=add_item(root,kind="Claim",title="Toy claim under review",module="synthesis")
        decision=add_item(root,kind="Decision",title="Decide next experiment",module="pivot")
        run=create_run(root,exp["id"],"Toy run attempt 1",1)
        logfile=root/"toy.log"
        logfile.write_text("SYNTHETIC FIXTURE; not an actual research result",encoding="utf-8")
        pair=record_run(root,run["id"],dataset="toy-data",protocol="toy-protocol",
            code_revision="synthetic-commit",seed=7,artifact_path="toy.log",
            observation="Toy F1 0.6 with limitations",outcome="inconclusive",
            metrics=[{"name":"F1","value":0.6,"unit":"ratio","direction":"higher"}],
            started_at="2026-11-23T08:00:00+08:00",
            ended_at="2026-11-23T08:05:00+08:00",synthetic=True)
        link_evidence(root,claim["id"],pair["result"]["id"],"qualifies",
                      "synthetic dataset only",quality="experiment-observed")
        event_id=load(root)["events"][0]["event_id"]
        trace=create_decision_trace(root,decision_id=decision["id"],
            title="Why another toy attempt was planned",scope="synthetic toy only",
            options=["rerun","park"],selected="rerun",
            rationale="Low sample power; not a validated result",
            event_ids=[event_id],claim_ids=[claim["id"]],run_ids=[run["id"]])
        original=load(root)
        build(root)
        with local_site(root) as origin, sync_playwright() as p:
            browser=p.chromium.launch(headless=True)
            page=browser.new_page(viewport={"width":1440,"height":920})
            errors=[]
            page.on("pageerror",lambda err:errors.append(str(err)))
            page.goto(origin+"/research/canvas/index.html",wait_until="load")
            page.locator('#view').select_option('reasoning')
            page.locator('#search').fill(run["id"])
            page.locator('#fit').click()
            node=page.locator('[data-node="item:'+run["id"]+'"]')
            assert node.count()==1, "Run node missing from reasoning view"
            node.click()
            details=page.locator('#details').inner_text()
            assert "实验运行溯源" in details,details
            assert "artifact_sha256" in details,details
            assert "SYNTHETIC" not in details or "synthetic" in details
            page.locator('#search').fill(trace["id"])
            page.locator('#fit').click()
            trace_node=page.locator('[data-node="item:'+trace["id"]+'"]')
            assert trace_node.count()==1,"Trace node missing from reasoning view"
            trace_node.click()
            text=page.locator('#details').inner_text()
            assert "决策溯源" in text
            assert "event_ids" in text
            assert "不会还原缺失对话" in text
            assert not errors, errors
            assert load(root)==original, "Read-only inspector mutated canonical research state"
            browser.close()
    print("PASS v0.3 Chromium Run/DecisionTrace reasoning view + inspector + no canonical mutations")


if __name__=="__main__":
    main()
