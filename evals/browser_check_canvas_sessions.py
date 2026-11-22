#!/usr/bin/env python3
"""Issue #12 actual Chromium live SessionRef inspector smoke."""
from pathlib import Path
import sys,tempfile,threading
from http.server import ThreadingHTTPServer
from playwright.sync_api import sync_playwright,expect
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from rn_core import init_project,add_item,load
from rn_domain import create_session,session_entity_link
from local_editor import create_handler

def main():
 with tempfile.TemporaryDirectory(prefix="rn-session-browser-") as temp:
  root=Path(temp);init_project(root,"Synthetic SessionRef UI")
  idea=add_item(root,kind="Idea",title="Synthetic Idea A",module="topic")
  claim=add_item(root,kind="Claim",title="Synthetic Claim C",module="synthesis")
  s1=create_session(root,"codex","workspace-red","codex-session-abc",url="https://example.org/session")
  s2=create_session(root,"chatgpt","workspace-blue","chatgpt-session-def")
  session_entity_link(root,s1["id"],idea["id"],"idea-origin")
  session_entity_link(root,s1["id"],claim["id"],"decision")
  session_entity_link(root,s2["id"],idea["id"],"experiment-analysis")
  before=load(root)
  server=ThreadingHTTPServer(("127.0.0.1",0),object)
  port=server.server_address[1]; token="test-session-ui-only"
  server.RequestHandlerClass=create_handler(root,token,port);server.daemon_threads=True
  thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
  try:
   with sync_playwright() as playwright:
    browser=playwright.chromium.launch(headless=True)
    page=browser.new_page(viewport={"width":1500,"height":1000})
    errors=[];page.on("pageerror",lambda e:errors.append(str(e)))
    page.goto(f"http://127.0.0.1:{port}/canvas#token={token}")
    page.locator('[data-node="item:'+idea["id"]+'"]').click()
    expect(page.locator("#sessionRecords")).to_contain_text("codex-session-abc")
    expect(page.locator("#sessionRecords")).to_contain_text("chatgpt-session-def")
    expect(page.locator("#sessionRecords")).to_contain_text("idea-origin")
    expect(page.locator("#sessionRecords")).to_contain_text("experiment-analysis")
    expect(page.locator("#sessionRecords")).to_contain_text("未验证的 provider 深链接")
    assert page.locator("#sessionRecords button").count()==2
    page.locator("#sessionProviderFilter").select_option("codex")
    expect(page.locator("#sessionRecords")).not_to_contain_text("chatgpt-session-def")
    page.locator("#sessionWorkspaceFilter").fill("workspace-red")
    expect(page.locator("#sessionRecords")).to_contain_text("codex-session-abc")
    page.locator("#sessionWorkspaceFilter").fill("workspace-blue")
    expect(page.locator("#sessionRecords")).not_to_contain_text("codex-session-abc")
    page.locator("#sessionWorkspaceFilter").fill("")
    page.locator("#sessionProviderFilter").select_option("")
    page.locator('[data-node="item:'+claim["id"]+'"]').click()
    expect(page.locator("#sessionRecords")).to_contain_text("codex-session-abc")
    expect(page.locator("#sessionRecords")).not_to_contain_text("chatgpt-session-def")
    expect(page.locator("#sessionRecords")).to_contain_text("decision")
    page.locator("#semanticOperation").select_option("link-session")
    expect(page.locator("#semanticParams")).to_contain_text("session_ref_id")
    assert not errors,errors
    assert load(root)==before
    browser.close()
  finally:
   server.shutdown();server.server_close();thread.join(timeout=3)
 print("PASS: Chromium SessionRef many-to-many, role labels, provider/workspace filters and no fabricated navigation")

if __name__=="__main__":main()
