#!/usr/bin/env python3
"""Create self-contained, read-only local HTML dashboard. No network or external JS."""
import argparse
from pathlib import Path
import json, html
from rn_core import load, validate_state, paths, now, ResearchError

def build(root):
    state=load(root);validate_state(state,strict=True)
    template=Path(__file__).resolve().parent.parent/"templates"/"dashboard.html"
    p=paths(root)
    payload={"project":state["project"],"items":state["items"],"relations":state["relations"],"sources":state["sources"],"events":state["events"][-80:],"generated_at":now(),"interactive_edits":False,"graph_engine":"native SVG fallback (Archify schema not assumed)"}
    data=json.dumps(payload,ensure_ascii=False,separators=(",",":"),allow_nan=False).replace("<","\\u003c").replace(">","\\u003e").replace("&","\\u0026").replace("\u2028","\\u2028").replace("\u2029","\\u2029")
    content=template.read_text(encoding="utf-8").replace("__EMBEDDED_STATE_JSON__",data)
    p["dash"].parent.mkdir(parents=True,exist_ok=True)
    p["dash"].write_text(content,encoding="utf-8")
    cards=[i for i in state["items"] if i["lifecycle_status"] in ("parked","quarantined","retired","under-revival-review")]
    if cards:
        arc=p["root"]/"research"/"archive"; folder=arc/"cards";folder.mkdir(parents=True,exist_ok=True)
        idx=["# 想法冷藏库（派生视图；权威状态在 research/state）","","| ID | 标题 | 生命周期 | 原因 | 回收触发 |","|---|---|---|---|---|"]
        for i in cards:
            a=i.get("archive") or {}
            safe=lambda x:str(x or "").replace("|","\\|").replace("\n"," ")
            idx.append(f"| {i['id']} | {safe(i['title'])} | {i['lifecycle_status']} | {safe(a.get('reason'))} | {safe(a.get('revival_triggers'))} |")
            content="\n".join([f"# {i['id']} · {i['title']}","","> 派生归档卡；不覆盖旧失败结论。","",f"- 原假设/方法：{i['description']}",f"- 当前状态：{i['lifecycle_status']}",f"- 原因：{a.get('reason','')}",f"- 失败类型：{a.get('failure_category','')}",f"- 适用/失败范围：{a.get('failure_scope','')}",f"- 诊断置信度：{a.get('diagnostic_confidence','')}",f"- 证据：{', '.join(a.get('evidence_refs',[]))}",f"- 已付出成本：{a.get('cost','')}",f"- 避免重复错误：{a.get('lesson','')}",f"- 回收前提：{a.get('revival_triggers','')}",f"- 决策者与日期：{a.get('decided_by','')} / {a.get('decided_at','')}","","## 下游依赖",*[f"- {x['from']} — {x['type']} → {x['to']}" for x in state['relations'] if x['from']==i['id'] or x['to']==i['id']]])
            (folder/f"{i['id']}.md").write_text(content+"\n",encoding="utf-8")
        (arc/"idea-index.md").write_text("\n".join(idx)+"\n",encoding="utf-8")
    return p["dash"]

if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("root");args=parser.parse_args()
    try:print(build(args.root))
    except ResearchError as e:parser.error(str(e))
