"""prevstate backend — on-demand snapshot/restore, no daemon (low power).

UI contract (you own tkinter+pystray, this package owns data):
  collect() -> full snapshot dict (apps, chrome, terminals, summary)
  save_filtered(snap, keep, meta) -> Path  (keep = indices/urls UI selected)
  list_names() / load_snapshot(name) / restore_snapshot(snap)
"""
from .snapshot import build_summary, collect_snapshot, restore_snapshot
from .store import list_snapshots, load, save

__all__ = [
    "collect_snapshot",
    "restore_snapshot",
    "build_summary",
    "list_snapshots",
    "load",
    "save",
    "collect",
    "save_filtered",
    "list_names",
    "load_snapshot",
]


def collect():
    return collect_snapshot()


def save_filtered(snap, keep_apps=None, keep_tabs=None, keep_terminals=None,
                  name=None, doing="", done="", todo=""):
    """Save a UI-filtered subset. keep_* are index lists, or None = keep all."""
    s = dict(snap)
    if keep_apps is not None:
        s["apps"] = [snap["apps"][i] for i in keep_apps if 0 <= i < len(snap["apps"])]
    if keep_tabs is not None:
        tabs = snap.get("chrome", {}).get("tabs", [])
        s["chrome"] = {**snap.get("chrome", {}),
                       "tabs": [tabs[i] for i in keep_tabs if 0 <= i < len(tabs)]}
    if keep_terminals is not None:
        s["terminals"] = [snap["terminals"][i] for i in keep_terminals
                          if 0 <= i < len(snap["terminals"])]
    s["summary"] = {**s.get("summary", {}), "doing": doing, "done": done, "todo": todo}
    return save(s, name)


def list_names():
    return [p.name for p in list_snapshots()]


def load_snapshot(name):
    snap, path = load(name)
    return snap
