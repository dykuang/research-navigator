#!/usr/bin/env python3
"""Build one offline unified research node editor, preserving the classic Canvas."""
from pathlib import Path
import argparse

from rn_core import paths, atomic_text, ResearchError
from unified_graph import unified_graph
from canvas_views import load_views
from build_canvas import embedded_json

def build_unified(root):
    graph = unified_graph(root)
    views = load_views(root)
    template = Path(__file__).resolve().parents[1] / "templates" / "unified_canvas.html"
    src = template.read_text(encoding="utf-8")
    if src.count("__RN_GRAPH_JSON__") != 1 or src.count("__RN_VIEWS_JSON__") != 1:
        raise ResearchError("unified canvas template payload markers are invalid")
    html = (src.replace("__RN_GRAPH_JSON__", embedded_json(graph))
               .replace("__RN_VIEWS_JSON__", embedded_json(views)))
    destination = paths(root)["root"] / "research" / "canvas" / "unified.html"
    atomic_text(destination, html)
    return destination

if __name__=="__main__":
    p=argparse.ArgumentParser(description="Generate offline unified Research Node Editor")
    p.add_argument("root")
    args=p.parse_args()
    try: print(build_unified(args.root))
    except (ResearchError,ValueError,OSError) as exc: p.error(str(exc))
