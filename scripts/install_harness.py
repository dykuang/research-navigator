#!/usr/bin/env python3
"""Opt-in installation of both Research Navigator skills; no project-state writes."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import sys
import tempfile

NAMES = ("research-navigator", "ask-research-navigator")
MANIFEST = ".research-navigator-install.json"

def skill_root(provider, scope, project=None, home=None):
    if provider not in ("shared", "codex", "deepseek") or scope not in ("project","user"):
        raise ValueError("unknown provider/scope")
    if scope == "project":
        if project is None or not Path(project).is_dir():
            raise ValueError("explicit existing project root required")
        root = Path(project).resolve()
        # DSH finds nearest git root; refuse a nested cwd rather than silently writing there.
        if provider in ("shared","deepseek") and not (root/".git").exists():
            if any((p/".git").exists() for p in root.parents):
                raise ValueError("select the Git project root, not a nested directory")
        return root / (".dsh" if provider == "deepseek" else ".agents") / "skills"
    home = Path(home or Path.home()).resolve()
    if provider == "deepseek":
        return Path(os.environ.get("DSH_HOME", str(home/".dsh"))).expanduser().resolve()/"skills"
    if provider == "codex":
        return Path(os.environ.get("CODEX_HOME", str(home/".codex"))).expanduser().resolve()/"skills"
    return Path(os.environ.get("DSH_AGENTS_HOME", str(home/".agents"))).expanduser().resolve()/"skills"

def _regular_files(root):
    for p in sorted(root.rglob("*")):
        if p.is_symlink():
            raise ValueError("symlinks not supported: "+str(p))
        if p.is_file():
            yield p
        elif not p.is_dir():
            raise ValueError("non-regular file not supported: "+str(p))

def _bundle_files(source, name):
    if name == NAMES[0]:
        includes = ["SKILL.md","README.md","LICENSE","references","scripts","templates"]
        root = source
    else:
        includes = ["SKILL.md","references"]
        root = source / name
    files = {}
    for item in includes:
        entry = root / item
        if entry.is_symlink():
            raise ValueError("symlink source: "+str(entry))
        if not entry.exists():
            raise ValueError("incomplete source: "+str(entry))
        for p in ([entry] if entry.is_file() else _regular_files(entry)):
            if "__pycache__" in p.parts or p.suffix in (".pyc",".pyo"):
                continue
            files[p.relative_to(root).as_posix()] = p
    return files

def _hash(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def _generated_cache(rel, tracked):
    """Recognize only conventional interpreter caches for manifest-owned .py files."""
    if rel.parent.name != "__pycache__":
        return False
    match=re.fullmatch(r"(.+)\.(?:cpython|pypy)-[0-9]+[a-z]*(?:\.opt-[12])?\.pyc",rel.name)
    if not match:
        return False
    return (rel.parent.parent/(match.group(1)+".py")).as_posix() in tracked

def _owned(dest, name):
    if dest.is_symlink() or not dest.is_dir():
        return False
    try:
        manifest = dest / MANIFEST
        if manifest.is_symlink():
            return False
        obj = json.loads(manifest.read_text(encoding="utf-8"))
        if obj.get("format") != 1 or obj.get("skill") != name:
            return False
        tracked=obj.get("files")
        if not isinstance(tracked,dict) or not tracked:
            return False
        actual={}
        cache_dirs=set()
        for p in _regular_files(dest):
            if p == manifest:
                continue
            rel=p.relative_to(dest)
            key=rel.as_posix()
            if key not in tracked and _generated_cache(rel,tracked):
                cache_dirs.add(str(rel.parent))
                continue
            actual[key]=_hash(p)
        # Unknown cache contents and arbitrary extra directories still block removal.
        expected_dirs={str(parent) for key in actual for parent in Path(key).parents if str(parent)!="."}
        actual_dirs={str(p.relative_to(dest)) for p in dest.rglob("*") if p.is_dir()}
        return actual == tracked and actual_dirs == expected_dirs | cache_dirs
    except (OSError, ValueError, TypeError, AttributeError):
        return False

def _inspect(root):
    rows=[]
    for name in NAMES:
        dest=root/name
        exists=dest.exists() or dest.is_symlink()
        owned=_owned(dest,name) if exists else False
        rows.append({"skill":name,"path":str(dest),"exists":exists,
                     "owned_unmodified":owned,
                     "skill_file_present":not dest.is_symlink() and (dest/"SKILL.md").is_file()})
    return rows

def operate(root, action, apply=False, source=None):
    root=Path(root).expanduser().absolute()
    source=Path(source or Path(__file__).resolve().parents[1]).resolve()
    if action not in ("install","uninstall","doctor"):
        raise ValueError("unknown action")
    rows=_inspect(root)
    result={"action":action,"root":str(root),"applied":False,"skills":rows,
            "runtime_verified":False}
    if action=="doctor":
        return result
    if action=="install":
        if any(r["exists"] for r in rows):
            raise ValueError("installation conflict; refusing to overwrite existing skills")
        bundles={n:_bundle_files(source,n) for n in NAMES}
    else:
        if not all(r["owned_unmodified"] for r in rows):
            raise ValueError("refusing to delete missing, modified, or unowned skills")
    for row in rows:
        dest=Path(row["path"]).resolve()
        if dest==source or dest in source.parents:
            raise ValueError("target overlaps source repository")
    if not apply:
        return result
    root.mkdir(parents=True,exist_ok=True)
    lock=root/".research-navigator-install.lock"
    lock.mkdir()  # exclusive among installer processes; stale lock needs manual review
    try:
        if _inspect(root)!=rows:
            raise ValueError("installation changed during preview; retry after inspection")
        if action=="install":
            with tempfile.TemporaryDirectory(prefix=".rn-stage-",dir=root) as tmp:
                stage=Path(tmp)
                for name,files in bundles.items():
                    dest=stage/name
                    dest.mkdir()
                    for rel,p in files.items():
                        out=dest/rel
                        out.parent.mkdir(parents=True,exist_ok=True)
                        shutil.copyfile(p,out)
                    manifest={"format":1,"skill":name,"files":{rel:_hash(dest/rel) for rel in files}}
                    (dest/MANIFEST).write_text(json.dumps(manifest,indent=2,sort_keys=True),encoding="utf-8")
                published=[]
                try:
                    for name in NAMES:
                        dest=root/name
                        if dest.exists() or dest.is_symlink():
                            raise ValueError("destination appeared during install")
                        (stage/name).rename(dest)
                        published.append(name)
                except Exception:
                    for name in reversed(published):
                        dest=root/name
                        if _owned(dest,name):
                            dest.rename(stage/name)
                    raise
        else:
            # Rename only verified bundles into a private staging directory.
            # If either move fails, restore earlier moves; never delete user edits.
            stage=Path(tempfile.mkdtemp(prefix=".rn-remove-",dir=root))
            moved=[]
            try:
                for name in NAMES:
                    dest=root/name
                    if not _owned(dest,name):
                        raise ValueError("skill changed during uninstall")
                    dest.rename(stage/name)
                    moved.append(name)
                if not all(_owned(stage/n,n) for n in moved):
                    raise ValueError("staged skill changed during uninstall")
            except Exception:
                for name in reversed(moved):
                    dest=root/name
                    if not dest.exists() and not dest.is_symlink():
                        try:
                            (stage/name).rename(dest)
                        except OSError:
                            pass
                if any(stage.iterdir()):
                    raise ValueError("uninstall interrupted; recover staged files at "+str(stage))
                stage.rmdir()
                raise
            shutil.rmtree(stage)
        result.update(applied=True,skills=_inspect(root))
        return result
    finally:
        lock.rmdir()

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("action",choices=("install","uninstall","doctor"))
    p.add_argument("--provider",choices=("shared","codex","deepseek"),default="shared")
    p.add_argument("--scope",choices=("project","user"),default="project")
    p.add_argument("--project",type=Path)
    p.add_argument("--skills-dir",type=Path,help="Explicit custom skill root; caller verifies runtime configuration")
    p.add_argument("--apply",action="store_true",help="Actually write/remove owned skill bundles")
    a=p.parse_args()
    try:
        root=a.skills_dir or skill_root(a.provider,a.scope,a.project)
        print(json.dumps(operate(root,a.action,a.apply),ensure_ascii=False,indent=2))
        return 0
    except (OSError,ValueError) as exc:
        print("Skill install error: "+str(exc),file=sys.stderr)
        return 2

if __name__=="__main__":
    sys.exit(main())
