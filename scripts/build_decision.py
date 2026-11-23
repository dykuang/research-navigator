#!/usr/bin/env python3
"""v0.4 self-contained offline decision report, adjacent to Research Canvas."""
import argparse
import html
import json
from pathlib import Path

from rn_core import atomic_text, paths
from rn_decision import summarize

def build(root):
    report=summarize(root,"brief")
    dest=paths(root)["root"]/"research"/"canvas"/"decisions.html"
    dest.parent.mkdir(parents=True,exist_ok=True)
    packed=json.dumps(report,ensure_ascii=False,separators=(",",":"),allow_nan=False)
    for old,new in (("<","\\u003c"),(">","\\u003e"),("&","\\u0026"),
                    ("\u2028","\\u2028"),("\u2029","\\u2029")):
        packed=packed.replace(old,new)
    page="""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Research Navigator · Decision Intelligence</title>
<style>
:root{font-family:system-ui,"Segoe UI","Microsoft Yahei",sans-serif;color:#21344a;background:#f3f6fa}
*{box-sizing:border-box}body{margin:0}header{padding:17px 5%;background:#12334b;color:white;
display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px}
header a{color:#c3e9e8}main{max-width:1220px;margin:auto;padding:23px 24px 60px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:13px}
.card{background:white;border:1px solid #dce5ec;border-radius:13px;padding:16px;margin:9px 0}
.muted{color:#617588;font-size:12px}.tag{background:#e5eef4;color:#39566f;
font-size:11px;padding:3px 8px;border-radius:7px;margin-right:5px;display:inline-block}
.tag.blocker{background:#ffebe5;color:#92433e}.tag.review{background:#fff2d9;color:#956b19}
section{margin-top:28px}h1{font-size:23px}h2{font-size:17px}h3{font-size:14px;margin:8px 0}
label{display:block;margin:9px 0;font-weight:600;font-size:12px}
input,select{padding:9px;border:1px solid #cbd8e2;border-radius:8px;max-width:100%;min-width:220px}
article p{margin:6px 0}a{color:#106c80}ul{padding-left:19px}
.warning{border-left:4px solid #b97c39;background:#fff8ee;padding:12px;font-size:12px}
@media(max-width:600px){main{padding:14px}input,select{width:100%}}
</style></head><body>
<script id="rn-decision" type="application/json">__REPORT__</script>
<header><strong>◈ Research Decision Intelligence · v0.4</strong>
<a href="index.html">返回无限科研画布</a></header>
<main><div class="muted">OFFLINE SNAPSHOT · READ ONLY · revision <b id="revision"></b></div>
<h1 id="project"></h1><p id="question"></p>
<div class="warning">所有建议均需人工审查。此页不能批准、执行实验、证明科学结论或恢复归档思路。
归档路线仅用于风险提示和经授权的复审。</div>
<section><h2>科学 Milestone 验收</h2><div id="milestones" class="grid"></div></section>
<section><h2>证据缺口与风险</h2>
<label>筛选缺口 <input id="search" type="search" placeholder="输入实体 ID、代码、描述"></label>
<label>严重度 <select id="severity"><option value="">全部</option><option value="blocker">阻塞</option>
<option value="review">待审</option></select></label>
<div id="gaps" class="grid"></div></section>
<section><h2>最小区分性检查 · 未获执行许可</h2><div id="checks" class="grid"></div></section>
<section><h2>已搁置思路的复审提示 · 默认隔离</h2><div id="archive" class="grid"></div></section>
<footer class="muted">Canonical data lives in research/state. Regenerate this report after changing state.</footer>
</main><script>
"use strict";
const R=JSON.parse(document.getElementById("rn-decision").textContent);
const $=id=>document.getElementById(id);
function el(t,c){const x=document.createElement(t);if(c)x.className=c;return x}
function text(parent,value,tag="p",cls){const x=el(tag,cls);x.textContent=String(value??"");
parent.appendChild(x);return x}
function cards(target,rows,renderer){const out=$(target);out.replaceChildren();
if(!rows.length){text(out,"暂无相关记录","p","muted");return}
for(const r of rows){const article=el("article","card");renderer(article,r);out.appendChild(article)}}
$("revision").textContent=R.revision;
$("project").textContent=R.project_name;
$("question").textContent=R.research_question;
cards("milestones",R.milestones,(a,m)=>{text(a,m.id+" · "+m.title,"h3");
text(a,m.accepted?"已有人工验收记录（不代表已证明）":"尚未通过验收","p","muted");
for(const c of m.criteria)text(a,c.id+" "+c.text+"；证据 "+(c.evidence_ids.join(", ")||"缺失"),"p")});
function renderGaps(){const q=$("search").value.toLowerCase().trim(),s=$("severity").value;
cards("gaps",R.pending_gaps.filter(g=>(!s||g.severity===s)
&&JSON.stringify([g.code,g.subject_id,g.description]).toLowerCase().includes(q)),
(a,g)=>{text(a,g.subject_id+" · "+g.code,"h3");
text(a,g.severity,"span","tag "+g.severity);text(a,g.description);
text(a,"关联："+(g.related_ids.join(", ")||"无"),"p","muted")})}
$("search").addEventListener("input",renderGaps);
$("severity").addEventListener("change",renderGaps);renderGaps();
cards("checks",R.proposed_next_checks,(a,o)=>{text(a,o.subject_id+" · "+o.title,"h3");
text(a,o.proposed_minimum_check);
text(a,"区分问题："+o.expected_discriminating_observation,"p","muted");
text(a,"成本："+o.estimated_cost+" · 信息价值："+o.expected_information_value,"p","muted");
text(a,"需人工批准；执行许可："+(o.execution_approved?"已获批":"未获批"),"p","muted")});
cards("archive",R.archive_review_watchlist,(a,x)=>{text(a,x.id+" · "+x.title,"h3");
text(a,x.lifecycle_status,"span","tag review");
text(a,"失败范围："+x.failure_scope);text(a,"复审条件："+x.revival_conditions);
text(a,"自动恢复：禁止；条件是否核验：否","p","muted")});
</script></body></html>"""
    atomic_text(dest,page.replace("__REPORT__",packed))
    return dest

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("root")
    print(build(parser.parse_args().root))
