"""CLI backend for future GUI: save/list/show/restore. No daemon, no polling."""
import argparse
import json
import sys

from . import store
from .snapshot import collect_snapshot, restore_snapshot
from . import store


def cmd_save(args):
    snap = collect_snapshot()
    if args.doing is not None:
        snap["summary"]["doing"] = args.doing
    if args.done is not None:
        snap["summary"]["done"] = args.done
    if args.todo is not None:
        snap["summary"]["todo"] = args.todo
    path = store.save(snap, args.out)
    print(str(path))
    print(snap["summary"]["auto"])


def cmd_list(_args):
    for p in store.list_snapshots():
        print(p.name)


def cmd_show(args):
    snap, path = store.load(args.name)
    print(f"# {path}")
    print(f"taken: {snap.get('taken_at')}")
    print(f"apps: {len(snap.get('apps', []))}  terminals: {len(snap.get('terminals', []))}  "
          f"tabs: {len(snap.get('chrome', {}).get('tabs', []))}")
    print("summary:", snap.get("summary", {}).get("auto", ""))
    if args.json:
        print(json.dumps(snap, indent=2)[:8000])


def cmd_restore(args):
    snap, path = store.load(args.name)
    report = restore_snapshot(
        snap,
        move_windows=not args.no_move,
        open_terminals=not args.no_terminals,
        open_chrome=not args.no_chrome,
    )
    print(f"restored from {path.name}: {report}")


def build_parser():
    ap = argparse.ArgumentParser(prog="prevstate", description="Snapshot/restore machine state")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("save", help="take a snapshot and exit")
    s.add_argument("--out", default=None, help="output filename")
    s.add_argument("--doing", default=None)
    s.add_argument("--done", default=None)
    s.add_argument("--todo", default=None)
    s.set_defaults(fn=cmd_save)
    l = sub.add_parser("list", help="list snapshots")
    l.set_defaults(fn=cmd_list)
    sh = sub.add_parser("show", help="show a snapshot")
    sh.add_argument("name", help="filename from list")
    sh.add_argument("--json", action="store_true")
    sh.set_defaults(fn=cmd_show)
    r = sub.add_parser("restore", help="relaunch terminals + chrome")
    r.add_argument("name", help="filename from list")
    r.add_argument("--no-chrome", action="store_true")
    r.add_argument("--no-terminals", action="store_true")
    r.add_argument("--no-move", action="store_true")
    r.set_defaults(fn=cmd_restore)
    return ap


def main(argv=None):
    args = build_parser().parse_args(argv)
    args.fn(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
