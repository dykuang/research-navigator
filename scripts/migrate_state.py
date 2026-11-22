#!/usr/bin/env python3
"""Preview, apply and recover schema v0.1 -> v0.2 without changing scientific records."""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
import io
import json
from pathlib import Path
import sys
import zipfile

from rn_core import (
    SCHEMA_VERSION, LEGACY_SCHEMA_VERSION, ResearchError, paths,
    workspace_lock, load, validate_state, read_json, atomic_json, atomic_text,
    append_events, rollback_transaction, now
)

CORE_KEYS = ("project", "items", "relations", "sources", "events")
SIDECAR_KEYS = ("session_refs", "evidence_links")
ALL_KEYS = CORE_KEYS + SIDECAR_KEYS


def snapshot(p):
    return {key: p[key].read_text(encoding="utf-8") if p[key].exists() else None
            for key in ALL_KEYS}


def preview(root):
    p = paths(root)
    if p["journal"].exists():
        raise ResearchError("Pending transaction detected; recover it before migration")
    state = load(root)
    errors = validate_state(state)
    if errors:
        raise ResearchError("Pre-migration validation failed:\n- " + "\n- ".join(errors))
    version = state["project"].get("schema_version")
    if version not in (LEGACY_SCHEMA_VERSION, SCHEMA_VERSION):
        raise ResearchError("Unsupported schema version; refusing to change files")
    return {
        "project_id": state["project"]["project_id"],
        "from_version": version, "to_version": SCHEMA_VERSION,
        "needs_migration": version != SCHEMA_VERSION,
        "items": len(state["items"]), "relations": len(state["relations"]),
        "sources": len(state["sources"]), "events": len(state["events"]),
        "session_refs": len(state.get("session_refs", [])),
        "evidence_links": len(state.get("evidence_links", [])),
        "will_preserve_scientific_records": True,
        "sidecars_to_create": [key for key in SIDECAR_KEYS if not p[key].exists()],
    }


def backup(root, project_id, before):
    p = paths(root)
    folder = p["root"] / "research" / "backups"
    folder.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    candidate = folder / f"schema-0.1-to-0.2-{stamp}.zip"
    index = 1
    while candidate.exists():
        candidate = folder / f"schema-0.1-to-0.2-{stamp}-{index}.zip"
        index += 1
    manifest = {"project_id": project_id, "created_at": now(), "files": {}}
    with zipfile.ZipFile(candidate, mode="x", compression=zipfile.ZIP_DEFLATED) as z:
        for key in ALL_KEYS:
            data = before[key]
            if data is not None:
                relative = f"research/state/{p[key].name}"
                raw = data.encode("utf-8")
                z.writestr(relative, raw)
                manifest["files"][relative] = hashlib.sha256(raw).hexdigest()
        z.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
    with zipfile.ZipFile(candidate) as z:
        if z.testzip():
            raise ResearchError("Migration backup validation failed")
    return candidate


def apply(root):
    p = paths(root)
    with workspace_lock(root):
        info = preview(root)
        if not info["needs_migration"]:
            # No new files, revision increments or events on repeat apply.
            return {"status": "already-current", **info}
        previous = snapshot(p)
        backup_path = backup(root, info["project_id"], previous)
        old = read_json(p["project"])
        atomic_json(p["journal"], {"project_id": info["project_id"],
                                    "revision": old["revision"], "before": previous})
        try:
            updated = dict(old)
            updated["schema_version"] = SCHEMA_VERSION
            updated["revision"] += 1
            updated["updated_at"] = now()
            for key in SIDECAR_KEYS:
                if not p[key].exists():
                    atomic_json(p[key], {key: []})
            atomic_json(p["project"], updated)
            append_events(p, [{
                "action": "schema-migrated", "actor": "tool",
                "reason": "explicit v0.1-to-v0.2 migration; original data preserved",
                "before": {"schema_version": LEGACY_SCHEMA_VERSION},
                "after": {"schema_version": SCHEMA_VERSION, "backup": str(backup_path)}
            }])
            state = load_without_journal(p)
            validate_state(state, strict=True)
            p["journal"].unlink()
        except Exception:
            rollback_transaction(root, expected_id=info["project_id"])
            raise
    return {"status": "migrated", "backup": str(backup_path),
            "new_revision": updated["revision"], **info}


def load_without_journal(p):
    from rn_core import read_events
    return {
        "project": read_json(p["project"]),
        "items": read_json(p["items"])["items"],
        "relations": read_json(p["relations"])["relations"],
        "sources": read_json(p["sources"])["sources"],
        "session_refs": read_json(p["session_refs"])["session_refs"],
        "evidence_links": read_json(p["evidence_links"])["evidence_links"],
        "events": read_events(p["events"]),
    }


def recover(root):
    with workspace_lock(root):
        restored = rollback_transaction(root)
        if restored:
            state = load(root)
            validate_state(state, strict=True)
        return {"status": "rolled-back" if restored else "no-pending-transaction"}


def main():
    ap = argparse.ArgumentParser(description="Research Navigator v0.2 migration and recovery")
    ap.add_argument("operation", choices=("preview", "apply", "recover"))
    ap.add_argument("root", help="research project root, not skill directory")
    args = ap.parse_args()
    try:
        result = {"preview": preview, "apply": apply, "recover": recover}[args.operation](args.root)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (OSError, ValueError, KeyError) as exc:
        print("Research Navigator migration error: " + str(exc), file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
