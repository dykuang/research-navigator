"""Presentation-only Research Canvas layouts (#9).

Layouts are separate from canonical research/state and never change events,
research revision, evidence or scientific approval. Stdlib-only.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import re

from rn_core import ResearchError, atomic_json, load, now, paths, read_json, workspace_lock

SCHEMA="canvas-layout-v1"
LAYOUT_NAME=re.compile(r"^[\w \-]{1,80}$",re.UNICODE)
NODE_ID=re.compile(r"^(item|source|evidence|session|criterion|interview|question|answer):[A-Za-z0-9-]{1,180}$")
MAX_NODES=20000
MAX_VIEW_COUNT=100


def view_path(root):
    return paths(root)["root"]/"research"/"canvas"/"views.json"


def empty_views(project_id):
    return {"schema_version":"canvas-views-v1","project_id":project_id,
            "views":{},"updated_at":None}


def load_views(root):
    state=load(root)
    path=view_path(root)
    if not path.exists():
        return empty_views(state["project"]["project_id"])
    data=read_json(path)
    if data.get("schema_version")!="canvas-views-v1" or data.get("project_id")!=state["project"]["project_id"]:
        raise ResearchError("Canvas view registry schema or project ID mismatch")
    if not isinstance(data.get("views"),dict):
        raise ResearchError("Canvas views must be a dictionary")
    return data


def validate_layout(layout,project_id):
    """Normalize a client-exported view without ever importing scientific data."""
    if not isinstance(layout,dict):
        raise ResearchError("Layout must be a JSON object")
    allowed={"schema_version","project_id","graph_revision","view_name","author",
             "saved_at","positions","viewport","collapsed","pinned_groups"}
    if set(layout)-allowed:
        raise ResearchError("Unknown layout keys; scientific attributes are forbidden")
    if layout.get("schema_version")!=SCHEMA or layout.get("project_id")!=project_id:
        raise ResearchError("Layout schema/project mismatch")
    name=layout.get("view_name","default")
    if not isinstance(name,str) or not LAYOUT_NAME.fullmatch(name):
        raise ResearchError("Invalid view name")
    positions=layout.get("positions")
    if not isinstance(positions,dict) or len(positions)>MAX_NODES:
        raise ResearchError("Invalid node positions")
    normalized={}
    def valid_number(value,limit):
        return type(value) in (int,float) and math.isfinite(value) and abs(value)<=limit
    for ident,p in positions.items():
        if not isinstance(ident,str) or not NODE_ID.fullmatch(ident):
            raise ResearchError("Invalid layout node ID")
        if not isinstance(p,dict) or set(p)!={"x","y"}:
            raise ResearchError("Each node position needs only x and y")
        if not valid_number(p["x"],1e7) or not valid_number(p["y"],1e7):
            raise ResearchError("Invalid layout coordinates")
        normalized[ident]={"x":float(p["x"]),"y":float(p["y"])}
    camera=layout.get("viewport")
    if not isinstance(camera,dict) or set(camera)!={"x","y","z"}:
        raise ResearchError("Invalid viewport object")
    if not valid_number(camera["x"],1e7) or not valid_number(camera["y"],1e7):
        raise ResearchError("Invalid viewport position")
    if not valid_number(camera["z"],4.5) or not .12<=camera["z"]<=4.5:
        raise ResearchError("Invalid viewport zoom")
    collapsed=layout.get("collapsed",[])
    if (not isinstance(collapsed,list) or len(collapsed)>MAX_NODES or
        any(not isinstance(i,str) or not NODE_ID.fullmatch(i) for i in collapsed) or
        len(set(collapsed))!=len(collapsed)):
        raise ResearchError("Invalid collapsed node IDs")
    pinned=layout.get("pinned_groups",[])
    if not isinstance(pinned,list) or len(pinned)>1000 or any(not isinstance(i,str) or len(i)>120 for i in pinned):
        raise ResearchError("Invalid pinned groups")
    rev=layout.get("graph_revision")
    if rev is not None and (type(rev)!=int or rev<0):
        raise ResearchError("Invalid source graph revision")
    author=layout.get("author","local-user")
    if not isinstance(author,str) or len(author)>120:
        raise ResearchError("Invalid author label")
    return {"schema_version":SCHEMA,"project_id":project_id,
      "graph_revision":rev,"view_name":name,"author":author,
      "saved_at":now(),"positions":normalized,
      "viewport":{k:float(camera[k]) for k in ("x","y","z")},
      "collapsed":collapsed,"pinned_groups":pinned}


def save_layout(root,layout,*,name=None):
    with workspace_lock(root):
        state=load(root)
        project_id=state["project"]["project_id"]
        if name is not None:
            layout=dict(layout)
            layout["view_name"]=name
        checked=validate_layout(layout,project_id)
        p=view_path(root)
        if p.exists():
            current=read_json(p)
            if current.get("project_id")!=project_id or current.get("schema_version")!="canvas-views-v1":
                raise ResearchError("Canvas layout registry mismatch")
        else:
            current=empty_views(project_id)
        views=current.get("views",{})
        if checked["view_name"] not in views and len(views)>=MAX_VIEW_COUNT:
            raise ResearchError("Too many saved canvas views")
        views[checked["view_name"]]=checked
        current["updated_at"]=now()
        # Only a layout file is replaced. No rn_core.write, project revision, or research event.
        atomic_json(p,current)
        return checked


def delete_layout(root,name):
    if not LAYOUT_NAME.fullmatch(name):
        raise ResearchError("Invalid view name")
    with workspace_lock(root):
        data=load_views(root)
        if name not in data["views"]:
            raise ResearchError("Saved view not found")
        del data["views"][name]
        data["updated_at"]=now()
        atomic_json(view_path(root),data)
        return {"deleted":name}


def main():
    p=argparse.ArgumentParser(description="Persist presentation-only canvas views")
    sub=p.add_subparsers(dest="command",required=True)
    show=sub.add_parser("list");show.add_argument("root")
    save=sub.add_parser("save");save.add_argument("root")
    save.add_argument("json_file",help="local exported layout JSON file")
    save.add_argument("--name")
    delete=sub.add_parser("delete");delete.add_argument("root");delete.add_argument("name")
    args=p.parse_args()
    try:
        if args.command=="list":result=load_views(args.root)
        elif args.command=="delete":result=delete_layout(args.root,args.name)
        else:
            path=Path(args.json_file).expanduser().resolve(strict=True)
            if path.stat().st_size>2_000_000:
                raise ResearchError("Layout file too large")
            layout=json.loads(path.read_text(encoding="utf-8"))
            result=save_layout(args.root,layout,name=args.name)
        print(json.dumps(result,indent=2,ensure_ascii=False))
    except (ResearchError,ValueError,OSError,KeyError) as exc:
        p.error(str(exc))


if __name__=="__main__":
    main()
