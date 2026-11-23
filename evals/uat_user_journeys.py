#!/usr/bin/env python3
"""Independent v0.2 user-journey simulation (synthetic data only).

Diagnostic UAT, *not* a replacement for strict unit regression. Reports problems
without hiding the other scenarios or damaging the passing release CI matrix.
Run with --strict to return nonzero when at least one product issue is observed.
"""
from __future__ import annotations
from contextlib import contextmanager
from http.server import ThreadingHTTPServer
from pathlib import Path
import argparse
import copy
import json
import os
import sys
import tempfile
import threading
from urllib.parse import urljoin

from playwright.sync_api import sync_playwright

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from rn_core import (ResearchError, add_item, add_relation, init_project, load, query)
from rn_domain import create_branch, create_milestone
from rn_proposals import approve_proposal, preview_proposal, queue_proposal
from build_dashboard import build
from local_editor import create_handler

RESULTS = []
ARTIFACTS = Path("artifacts")
ARTIFACTS.mkdir(exist_ok=True)

def record(name, status, expected, observed, detail=""):
    row = {"scenario": name, "status": status, "expected": expected,
           "observed": observed, "detail": detail}
    RESULTS.append(row)
    print(f"[{status.upper()}] {name}\n  expected: {expected}\n  observed: {observed}")
    if detail:
        print("  detail:",detail[:500])
    return row

def proposal(root, op, params):
    return {"operation":op,"params":params,
            "reason":"Synthetic user reviewed the research limitations",
            "expected_revision":load(root)["project"]["revision"]}

def terminal_approve_simulated(root, op, params):
    payload=proposal(root,op,params)
    before=load(root)
    simulation=preview_proposal(root,payload)
    assert simulation["accepted"] is False, "preview returned an approved state"
    assert load(root)==before, "preview changed canonical state"
    pid=queue_proposal(root,payload)["proposal_id"]
    assert load(root)==before, "enqueue changed canonical state"
    approve_proposal(root,pid,confirmed=True)
    assert load(root)["project"]["revision"] == before["project"]["revision"]+1
    assert any(e.get("proposal_id")==pid for e in load(root)["events"])
    return pid

@contextmanager
def serve_bridge(root, token):
    server=ThreadingHTTPServer(("127.0.0.1",0),object)
    port=server.server_address[1]
    server.RequestHandlerClass=create_handler(root,token,port)
    server.daemon_threads=True
    thread=threading.Thread(target=server.serve_forever,daemon=True)
    thread.start()
    try:
        yield "http://127.0.0.1:"+str(port)
    finally:
        server.shutdown();server.server_close();thread.join(timeout=3)

def newbie_offline(browser):
    name="01 新手：创建中文项目 → 浏览画布 → 导出草案"
    with tempfile.TemporaryDirectory(prefix="rn-user-novice-") as temp:
        root=Path(temp)
        init_project(root,"合成科研演示：首次使用","多分支方法能否在小样本中复现？")
        idea=add_item(root,kind="Idea",title="新手研究想法 A",module="topic")
        before=load(root)
        build(root)
        page=browser.new_page(viewport={"width":1440,"height":900},accept_downloads=True)
        try:
            page.goto((root/"research"/"canvas"/"index.html").as_uri(),wait_until="load")
            page.locator('[data-node="item:'+idea["id"]+'"]').wait_for()
            assert page.locator("#previewSemantic").is_disabled()
            page.locator("#semanticOperation").select_option("add-branch")
            with page.expect_download() as dl:
                page.locator("#exportSemantic").click()
            data=json.loads(Path(dl.value.path()).read_text(encoding="utf-8"))
            assert data["operation"]=="add-branch"
            assert data["expected_revision"]==before["project"]["revision"]
            assert load(root)==before
            page.screenshot(path=str(ARTIFACTS/"uat-novice-desktop.png"),full_page=True)
            record(name,"pass","离线画布可浏览、导出草案，不能修改科研状态",
                   "中文节点显示、草案导出成功，预览/审批按钮不可用且权威状态不变")
        finally:
            page.close()

def researcher_archive():
    name="02 研究生：A/B/C 共享 Baseline → A 负结果 → 归档 → 二阶段回收"
    with tempfile.TemporaryDirectory(prefix="rn-user-archive-") as temp:
        root=Path(temp);init_project(root,"合成负结果路线")
        baseline=add_item(root,kind="Baseline",title="共享基线",module="literature")
        branches=[create_branch(root,"路线"+ch,"对比"+ch,["不再重复时停止"]) for ch in "ABC"]
        for branch in branches:
            add_relation(root,baseline["id"],branch["id"],"member-of")
        milestone=create_milestone(root,"可复现实验","条件") if False else create_milestone(root,"可复现实验",["基线可重复"])
        add_relation(root,branches[0]["id"],milestone["id"],"contributes-to")
        idea=add_item(root,kind="Idea",title="方法 A",module="topic")
        add_relation(root,idea["id"],branches[0]["id"],"member-of")
        result=add_item(root,kind="Result",title="合成弱负结果",module="experiment",
                        observation="合成指标：0.49 versus 0.50",artifact_path="fake-logs/run.txt")
        negative=copy.deepcopy(next(x for x in load(root)["items"] if x["id"]==result["id"]))
        terminal_approve_simulated(root,"archive-route",{
            "item_id":idea["id"],"lifecycle":"parked",
            "failure_scope":"只有一组小样本的弱负结果",
            "revival_triggers":"独立新数据复核",
            "failure_category":"evaluation","evidence_refs":[result["id"]]})
        archived=load(root)
        assert idea["id"] not in {x["item_id"] for x in query(archived,"planning")}
        assert idea["id"] in {x["item_id"] for x in query(archived,"risk-check")}
        assert next(x for x in archived["items"] if x["id"]==baseline["id"])["lifecycle_status"]=="active"
        assert next(x for x in archived["items"] if x["id"]==branches[1]["id"])["impact_status"]=="current"
        assert next(x for x in archived["items"] if x["id"]==milestone["id"])["impact_status"]=="needs-review"
        terminal_approve_simulated(root,"begin-revival-review",{
            "item_id":idea["id"],"question":"新数据是否改变结论？",
            "new_conditions":"新独立样本"})
        terminal_approve_simulated(root,"approve-revival-candidate",{
            "item_id":idea["id"],"title":"方法 A v2 待证伪候选",
            "new_conditions":"新数据、独立复现实验",
            "approval_note":"合成场景中的第二次独立批准"})
        final=load(root)
        assert next(x for x in final["items"] if x["id"]==idea["id"])["lifecycle_status"]=="parked"
        assert next(x for x in final["items"] if x["id"]==result["id"])==negative
        derived=[x for x in final["items"] if x.get("derived_from")==idea["id"]]
        assert len(derived)==1 and derived[0]["epistemic_status"]=="hypothesis"
        record(name,"pass","旧负结果不丢、其他共享分支不被归档；两阶段审批生成新候选",
               "模拟终端分两次批准后产生新 Idea；原档案/Result 保留，Milestone 需复核")

def session_analyst(browser):
    name="03 AI 用户：一个会话关联两个实体，Idea 同时关联两个会话"
    with tempfile.TemporaryDirectory(prefix="rn-user-sessions-") as temp:
        root=Path(temp);init_project(root,"Synthetic SessionRef")
        idea=add_item(root,kind="Idea",title="方法假设",module="topic")
        claim=add_item(root,kind="Claim",title="待证据支持的论点",module="synthesis")
        terminal_approve_simulated(root,"register-session",{
            "provider":"codex","workspace_id":"workspace-A","session_id":"synthetic-session-A",
            "url":"https://example.org/session-A"})
        terminal_approve_simulated(root,"register-session",{
            "provider":"other","workspace_id":"workspace-B","session_id":"synthetic-session-B"})
        for sid,entity,role in [
            ("SESS-0001",idea["id"],"idea-origin"),
            ("SESS-0001",claim["id"],"decision"),
            ("SESS-0002",idea["id"],"experiment-analysis"),
        ]:
            terminal_approve_simulated(root,"link-session",{
                "session_ref_id":sid,"entity_id":entity,"role":role})
        before=load(root)
        with serve_bridge(root,"uat-secret-token") as origin:
            page=browser.new_page(viewport={"width":1500,"height":940})
            try:
                page.goto(origin+"/canvas#token=uat-secret-token")
                page.locator('[data-node="item:'+idea["id"]+'"]').click()
                txt=page.locator("#sessionRecords").inner_text()
                assert "synthetic-session-A" in txt and "synthetic-session-B" in txt
                assert "idea-origin" in txt and "experiment-analysis" in txt
                assert page.locator("#sessionRecords button").count()==2  # copy only, not open
                page.locator("#sessionProviderFilter").select_option("codex")
                assert "synthetic-session-B" not in page.locator("#sessionRecords").inner_text()
                page.locator("#sessionProviderFilter").select_option("")
                page.locator('[data-node="item:'+claim["id"]+'"]').click()
                text=page.locator("#sessionRecords").inner_text()
                assert "synthetic-session-A" in text and "synthetic-session-B" not in text
                assert load(root)==before
                record(name,"pass","多对多 SessionRef，复制而不猜测链接，不导入聊天全文",
                       "Inspector 角色/Provider 筛选正确，未显示任何未经验证的打开按钮")
            finally:
                page.close()

def parallel_editor_conflict():
    name="04 两个浏览器窗口：同时创建提案，防止旧版本覆盖新内容"
    with tempfile.TemporaryDirectory(prefix="rn-user-concurrent-") as temp:
        root=Path(temp);init_project(root,"合成并发项目")
        old=load(root)
        p1=proposal(root,"add-item",{"type":"Idea","title":"窗口 A","module":"topic"})
        p2=proposal(root,"add-item",{"type":"Idea","title":"窗口 B","module":"topic"})
        id1=queue_proposal(root,p1)["proposal_id"]
        id2=queue_proposal(root,p2)["proposal_id"]
        assert load(root)==old
        approve_proposal(root,id1,confirmed=True)
        state=load(root)
        try:
            approve_proposal(root,id2,confirmed=True)
        except ResearchError as ex:
            assert "stale" in str(ex)
        else:
            raise AssertionError("stale proposal was silently applied")
        assert load(root)==state
        record(name,"pass","旧修订提案拒绝，不默默覆盖已批准变更",
               "第二张提案因版本过期被拒绝；第一张保留、没有数据丢失",
               "体验限制：用户需刷新后重新预览并提交第二张提案")

def branch_revival_boundary():
    name="05 导师：ResearchBranch 整条路线归档后申请 v2 新路线"
    with tempfile.TemporaryDirectory(prefix="rn-user-branch-") as temp:
        root=Path(temp);init_project(root,"分支回收边界")
        branch=create_branch(root,"重要路线 B","第二阶段验证",["多次重复无改进"])
        terminal_approve_simulated(root,"archive-route",{
            "item_id":branch["id"],"lifecycle":"parked",
            "failure_scope":"仅原采样条件下不稳定",
            "revival_triggers":"更大独立测试集"})
        terminal_approve_simulated(root,"begin-revival-review",{
            "item_id":branch["id"],"question":"新材料能否复现？",
            "new_conditions":"独立材料和新协议"})
        before=load(root)
        payload=proposal(root,"approve-revival-candidate",{
            "item_id":branch["id"],"title":"重要路线 B v2",
            "new_conditions":"新的独立复现实验条件",
            "goal":"在新独立材料和新版协议下复现路线 B",
            "stop_conditions":["新的基线不能独立复现时停止"],
            "approval_note":"第二次独立合成批准"})
        try:
            preview_proposal(root,payload)
            id_=queue_proposal(root,payload)["proposal_id"]
            approve_proposal(root,id_,confirmed=True)
            after=load(root)
            child=next(x for x in after["items"] if x.get("derived_from")==branch["id"])
            assert child["type"]=="ResearchBranch" and child.get("branch",{}).get("goal")
            assert next(x for x in after["items"] if x["id"]==branch["id"])["lifecycle_status"]=="parked"
            record(name,"pass","ResearchBranch 可按双阶段流程生成合法的新分支候选",
                   "分支候选生成，保留目标、停止条件及旧历史")
        except (ResearchError,AssertionError) as ex:
            assert load(root)==before,"failed branch proposal must not modify canonical state"
            record(name,"issue","ResearchBranch 应能像 Idea 一样回收并生成具备目标/停止条件的新分支",
                   "二次审批预览/提交无法完成，合法 ResearchBranch 候选未创建",
                   type(ex).__name__+": "+str(ex))

def live_classic_navigation(browser):
    name="06 桌面用户：本机 Bridge 画布点击「返回经典工作台」"
    with tempfile.TemporaryDirectory(prefix="rn-user-backnav-") as temp:
        root=Path(temp);init_project(root,"导航回退用户")
        add_item(root,kind="Idea",title="实例 A",module="topic")
        build(root)
        with serve_bridge(root,"synthetic-live-token") as origin:
            page=browser.new_page(viewport={"width":1400,"height":900})
            try:
                page.goto(origin+"/canvas#token=synthetic-live-token",wait_until="load")
                page.locator(".node").first.wait_for()
                href=page.get_by_role("link",name="返回经典工作台").get_attribute("href")
                target=urljoin(page.url,href)
                response=page.request.get(target)
                status=response.status
                if status==200 and "text/html" in response.headers.get("content-type",""):
                    record(name,"pass","返回经典工作台应打开真正可用的 HTML 页面",
                           f"HTTP {status} {target}")
                else:
                    record(name,"issue","从已连接的 Canvas 返回经典工作台仍可用",
                           f"点击链接会访问 {target}，HTTP {status}（非正常 HTML 工作台）",
                           "Broken in-app navigation; offline file dashboard is not served at this live URL.")
            finally:
                page.close()

def mobile_viewport(browser):
    name="07 手机用户：390px 窄屏查看详情及 SessionRef 操作"
    with tempfile.TemporaryDirectory(prefix="rn-user-mobile-") as temp:
        root=Path(temp);init_project(root,"手机视图项目")
        add_item(root,kind="Idea",title="移动端可见节点",module="topic")
        with serve_bridge(root,"mobile-uat-token") as origin:
            page=browser.new_page(viewport={"width":390,"height":844},is_mobile=True,
                                  has_touch=True,device_scale_factor=1)
            try:
                page.goto(origin+"/canvas#token=mobile-uat-token")
                page.locator(".node").first.wait_for()
                page.screenshot(path=str(ARTIFACTS/"uat-mobile-390.png"),full_page=True)
                display=page.locator("#inspector").evaluate("(el)=>getComputedStyle(el).display")
                if display=="none":
                    record(name,"issue","小屏幕应能访问节点详情、会话与提案编辑，或提示仅限桌面",
                           "宽度 390px 时整个 #inspector 为 display:none，节点详情/SessionRef/提案界面不可操作",
                           "The layout hides the entire right panel at max-width:680px.")
                else:
                    page.locator(".node").first.click()
                    assert page.locator("#details").is_visible()
                    record(name,"pass","移动端科研详情可访问","右侧面板可见")
            finally:
                page.close()

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--strict",action="store_true",help="nonzero exit if user-visible defects found")
    args=parser.parse_args()
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True)
        try:
            # Every scenario uses its own synthetic project root and local URL.
            newbie_offline(browser)
            researcher_archive()
            session_analyst(browser)
            parallel_editor_conflict()
            branch_revival_boundary()
            live_classic_navigation(browser)
            mobile_viewport(browser)
        finally:
            browser.close()
    report={"test_kind":"independent synthetic end-user journeys",
            "commit":os.environ.get("GITHUB_SHA","unknown"),
            "environment":{"python":sys.version.split()[0],"browser":"Chromium Playwright"},
            "scenarios":RESULTS,"counts":{
                "pass":sum(x["status"]=="pass" for x in RESULTS),
                "issue":sum(x["status"]=="issue" for x in RESULTS)}}
    (ARTIFACTS/"uat-user-journeys.json").write_text(
        json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print("UAT_RESULTS_JSON="+json.dumps(report["counts"],ensure_ascii=False))
    if args.strict and report["counts"]["issue"]:
        raise SystemExit(1)
    return 0

if __name__=="__main__":
    sys.exit(main())
