#!/usr/bin/env python3
"""Read-only, self-contained interview snapshot; no session transcript or approvals."""
from pathlib import Path
import argparse
import json

from rn_core import ResearchError, atomic_text, paths
from rn_interview import read, frontier, handoff

def build(root):
    try:
        interview=read(root)
        todo=frontier(interview)
        packet=handoff(root)
    except ResearchError as exc:
        # An uninitialized interview is a valid state for a project.
        if "没有持久化访谈" not in str(exc):
            raise
        return None
    dest=paths(root)["root"]/"research"/"canvas"/"interview.html"
    dest.parent.mkdir(parents=True,exist_ok=True)
    payload={
        "project_id":interview["project_id"],
        "topic":interview["topic"],
        "status":interview["status"],"revision":interview["revision"],
        "round":interview["round"],
        "confirmed":packet["confirmed"],
        "ready":todo["ready"],"blocked":todo["blocked"],
        "consensus_note":interview["consensus_note"],
        "accepted_open_questions":interview["accepted_open_questions"],
        "startup_hint":packet["startup_hint"],
    }
    safe=json.dumps(payload,ensure_ascii=False,allow_nan=False,separators=(",",":"))
    for original,escaped in (("<","\\u003c"),(">","\\u003e"),("&","\\u0026"),
                              ("\u2028","\\u2028"),("\u2029","\\u2029")):
        safe=safe.replace(original,escaped)
    page="""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Research Navigator · Persistent Interview</title>
<style>:root{font:14px system-ui,"Segoe UI","Microsoft YaHei",sans-serif;color:#183047;background:#f4f7fa}
*{box-sizing:border-box}body{margin:0}header{background:#163348;color:#fff;padding:18px 5%;
display:flex;justify-content:space-between;gap:12px}a{color:inherit}
main{max-width:1000px;margin:auto;padding:24px}section{margin:22px 0}
.card{padding:15px;background:#fff;border:1px solid #dbe5ec;border-radius:12px;margin:9px 0;overflow-wrap:anywhere}
.note{background:#fff3dc;padding:13px;border-radius:9px;color:#684a13}
.muted{color:#637789;font-size:12px}h1{font-size:23px}h2{font-size:17px}
p{line-height:1.6}code{overflow-wrap:anywhere}
.choice{display:block;border:1px solid #d4e0e9;border-radius:8px;margin:6px 0;padding:9px;cursor:pointer}
.choice input{margin-right:8px}.other-input{display:block;width:100%;max-width:100%;min-height:75px;
margin:8px 0;padding:8px;border:1px solid #b6c7d4;border-radius:8px}
.other-input[hidden],.draft[hidden]{display:none}
button{background:#176a82;color:white;padding:8px 14px;border:0;border-radius:8px;cursor:pointer}
button:disabled{background:#a7b6c2;cursor:not-allowed}.draft{white-space:pre-wrap;overflow-wrap:anywhere}
.choice:focus-within{outline:2px solid #176a82}
@media(max-width:600px){main{padding:12px}}
</style></head><body>
<script type="application/json" id="interview-data">__INTERVIEW_JSON__</script>
<header><strong>◈ Research Grilling · v0.4.2</strong><a href="index.html">返回无限画布</a></header>
<main><p class="muted">OFFLINE SNAPSHOT · READ ONLY · R<span id="revision"></span></p>
<h1 id="topic"></h1><p id="status"></p>
<p class="note">本页面不会自动启动、确认或结束访谈；也不会让新 Codex Session 自动继承 Skill。
本页的选项仅能生成可复制的回答草案，**不会写入项目状态或提交确认**。
在新会话中请明确调用 research-navigator 并恢复项目访谈。访谈答案不是经过验证的科学证据。</p>
<section><h2>待回答的核心问题</h2><div id="ready"></div></section>
<section><h2>等待前置答案</h2><div id="blocked"></div></section>
<section><h2>已确认的共识</h2><div id="confirmed"></div></section>
<section><h2>共识审查与退出</h2><div id="consensus"></div></section>
<section><h2>恢复说明</h2><div id="hint"></div></section>
</main>
<script>"use strict";
const data=JSON.parse(document.getElementById("interview-data").textContent);
const $=id=>document.getElementById(id);
function t(parent,element,value,cls){const node=document.createElement(element);node.textContent=String(value??"");
if(cls)node.className=cls;parent.appendChild(node);return node}
function cards(name,rows,render){const container=$(name);container.replaceChildren();
if(!rows.length)t(container,"p","暂无","muted");
for(const x of rows){const c=document.createElement("article");c.className="card";render(c,x);container.appendChild(c)}}
$("revision").textContent=data.revision;$("topic").textContent=data.topic;
$("status").textContent="状态："+data.status+" · 第 "+data.round+" 轮";
cards("ready",data.ready,(c,x)=>{t(c,"h3",x.id+" "+x.text);
t(c,"p","重要性："+x.why);t(c,"p","备选与权衡："+x.options);
t(c,"p","建议："+x.recommendation);t(c,"p","最低成本验证："+x.lowest_cost_check);
t(c,"p","状态："+x.status,"muted");
const choices=Array.isArray(x.choices)?x.choices:[];
if(!choices.length){
  t(c,"p","旧版自由文本问题：请直接在 Codex 对话里回复你的答案。","muted");return;
}
const group=document.createElement("div");group.setAttribute("role","radiogroup");
group.setAttribute("aria-label",x.id+" 备选答案");c.appendChild(group);
const name="rn-"+x.id;
function entry(id,label,desc){
  const shell=document.createElement("label");shell.className="choice";
  const input=document.createElement("input");input.type="radio";input.name=name;input.value=id;
  shell.appendChild(input);t(shell,"strong",label);if(desc)t(shell,"p",desc,"muted");
  group.appendChild(shell);return input;
}
const entries=choices.map(ch=>entry(ch.id,ch.label,ch.description));
const other=entry("other","其他／自定义","我有与备选方案不同的答案");
const custom=document.createElement("textarea");custom.className="other-input";
custom.placeholder="请输入你自己的研究目标、原因或备选方案";
custom.setAttribute("aria-label",x.id+" 自定义答案");
custom.hidden=true;c.appendChild(custom);
const draft=document.createElement("pre");draft.className="card draft";
draft.hidden=true;c.appendChild(draft);
const generate=document.createElement("button");generate.type="button";
generate.textContent="生成回答草案（不会保存）";generate.disabled=true;c.appendChild(generate);
const all=entries.concat([other]);
function refresh(){
 const selected=all.find(el=>el.checked);
 custom.hidden=!(selected&&selected.value==="other");
 generate.disabled=!(selected&&(selected.value!=="other"||custom.value.trim()));
 draft.hidden=true;
}
all.forEach(input=>input.addEventListener("change",refresh));
custom.addEventListener("input",refresh);
generate.addEventListener("click",()=>{
 const selected=all.find(el=>el.checked);
 if(!selected||generate.disabled)return;
 const item=choices.find(ch=>ch.id===selected.value);
 const content=selected.value==="other"?
   x.id+" 其他／自定义："+custom.value.trim():
   x.id+" 选择："+item.id+"（"+item.label+"）";
 draft.textContent=content+"\\n请将这段内容粘贴到 Codex 会话，由 Agent 确认后保存。";
 draft.hidden=false;
});
});
cards("blocked",data.blocked,(c,x)=>t(c,"p",x.id+" 依赖："+x.depends_on.join(", ")));
cards("confirmed",data.confirmed,(c,x)=>{t(c,"h3",x.id+" "+x.question);t(c,"p",x.answer)});
t($("consensus"),"p",data.consensus_note||"尚未请求退出；请继续追问，直到用户确认。");
t($("consensus"),"p","仍未解决且由用户明确接受："+(data.accepted_open_questions.join(", ")||"无"),"muted");
t($("hint"),"p",data.startup_hint);
</script></body></html>"""
    atomic_text(dest,page.replace("__INTERVIEW_JSON__",safe))
    return dest

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("root")
    result=build(parser.parse_args().root)
    print(result if result else "No active or recorded interview; interview snapshot not created")
