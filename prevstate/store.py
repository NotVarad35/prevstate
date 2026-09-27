"""Snapshot store: atomic writes, rotation. stdlib only."""
import json
import os
import tempfile
from datetime import datetime
from pathlib import Path

RETAIN = 20


def snapshot_dir():
    base = os.environ.get("LOCALAPPDATA") or str(Path.home())
    d = Path(base) / "prevstate"
    d.mkdir(parents=True, exist_ok=True)
    return d


def legacy_dir():
    """Pre-rename dir; read-only fallback so old snapshots aren't lost."""
    base = os.environ.get("LOCALAPPDATA") or str(Path.home())
    return Path(base) / "previousstate"


def snapshot_path(name=None):
    d = snapshot_dir()
    if name:
        p = Path(name)
        return p if p.is_absolute() else d / p
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    return d / f"snapshot-{ts}.json"


def save(data, name=None):
    path = snapshot_path(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except Exception:
            pass
        raise
    prune()
    return path


def load(name_or_path):
    p = snapshot_path(name_or_path)
    if not p.exists():
        # Try legacy pre-rename location.
        legacy = legacy_dir() / Path(name_or_path).name
        if legacy.exists():
            p = legacy
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f), p


def list_snapshots():
    files = []
    for d in (snapshot_dir(), legacy_dir()):
        try:
            files.extend(d.glob("snapshot-*.json"))
        except Exception:
            continue
    # De-dupe by name (new dir wins), newest first.
    seen = {}
    for f in files:
        seen.setdefault(f.name, f)
    return sorted(seen.values(), reverse=True)


def prune(retain=RETAIN):
    files = list_snapshots()
    for old in files[retain:]:
        try:
            old.unlink()
        except Exception:
            pass
