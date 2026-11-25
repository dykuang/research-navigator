#!/usr/bin/env python3
"""Build a single-file offline interactive Research Canvas (#8).

State is read-only. Node positions are only presentation metadata.
No package/CDN JS dependencies; the classic dashboard is unchanged.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

from rn_core import load, now, paths, ResearchError
from graph_projection import project_graph


def embedded_json(value):
    return (json.dumps(value,ensure_ascii=False,separators=(",",":"),allow_nan=False)
            .replace("<","\\u003c").replace(">","\\u003e")
            .replace("&","\\u0026").replace("\u2028","\\u2028")
            .replace("\u2029","\\u2029"))


def build_canvas(root):
    project_root=paths(root)["root"]
    state=load(root)
    graph=project_graph(state,view="all",limit=None)
    from canvas_views import load_views
    views=load_views(root)
    template=Path(__file__).resolve().parent.parent/"templates"/"research_canvas.html"
    src=template.read_text(encoding="utf-8")
    if src.count("__RN_GRAPH_JSON__")!=1 or src.count("__RN_VIEWS_JSON__")!=1:
        raise ResearchError("canvas template injection placeholders missing")
    html=(src.replace("__RN_GRAPH_JSON__",embedded_json(graph))
             .replace("__RN_VIEWS_JSON__",embedded_json(views)))
    dest=project_root/"research"/"canvas"/"index.html"
    dest.parent.mkdir(parents=True,exist_ok=True)
    from rn_core import atomic_text
    # Only offline export carries the read-only decision snapshot.
    # The authenticated local bridge remains responsible for interactive proposals.
    from build_decision import build as build_decision
    build_decision(root)
    from build_interview import build as build_interview
    interview_page=build_interview(root)
    html=html.replace('<a href="../dashboard/index.html">返回经典工作台</a>',
                      ('<a href="interview.html">科研访谈</a> · ' if interview_page else '') +
                      '<a href="decisions.html">研究决策</a> · <a href="../dashboard/index.html">返回经典工作台</a>')
    atomic_text(dest,html)
    return dest


def main():
    p=argparse.ArgumentParser(description="Generate offline interactive research canvas")
    p.add_argument("root")
    args=p.parse_args()
    try:
        print(build_canvas(args.root))
    except (ResearchError,ValueError,OSError) as exc:
        p.error(str(exc))


if __name__=="__main__":
    main()
