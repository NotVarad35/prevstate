"""tkinter UI: Set-new-environment + Restore picker. Dark theme, matches design canvas.

Import-safe: no Tk objects are created at import time, so the backend and
tests can import this module headless. All windows are built by functions.
"""
import queue
import threading
import tkinter as tk
from datetime import datetime, timezone
from tkinter import messagebox

BG = "#1b1d20"
PANEL = "#24262b"
CARD = "#2b2e33"
BORDER = "#3a3d44"
TEXT = "#e8eaed"
DIM = "#9aa0a6"
ACCENT = "#2f7cf6"
GREEN_BG = "#1d3a2a"
GREEN_FG = "#4ade80"
RED = "#ef4444"
ORANGE_BG = "#3d2c14"
ORANGE_FG = "#fbbf24"

FONT_TITLE = ("Segoe UI", 10, "bold")
FONT = ("Segoe UI", 9)
FONT_DIM = ("Segoe UI", 9)


def rel_time(iso):
    try:
        dt = datetime.fromisoformat(iso)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        mins = int((datetime.now(timezone.utc) - dt).total_seconds() // 60)
        if mins < 1:
            return "just now"
        if mins < 60:
            return f"{mins} minute{'s' if mins != 1 else ''} ago"
        hours = mins // 60
        if hours < 24:
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        return dt.astimezone().strftime("Yesterday, %H:%M" if hours < 48 else "%Y-%m-%d, %H:%M")
    except Exception:
        return ""


def _style(win):
    win.configure(bg=BG)
    win.option_add("*Background", BG)
    win.option_add("*Foreground", TEXT)
    win.option_add("*Font", FONT)


def _section(parent, title):
    tk.Label(parent, text=title, font=FONT_TITLE, bg=BG, fg=TEXT,
             anchor="w").pack(fill="x", padx=12, pady=(12, 4))
    frame = tk.Frame(parent, bg=BG)
    frame.pack(fill="x", padx=12)
    return frame


def _badge(parent, text, bg, fg):
    return tk.Label(parent, text=text, font=("Segoe UI", 8), bg=bg, fg=fg, padx=6, pady=1)


def _row(parent, var, title, sub="", badges=()):
    """One checkbox row. Returns nothing; appends to layout."""
    card = tk.Frame(parent, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
    card.pack(fill="x", pady=2)
    cb = tk.Checkbutton(card, variable=var, bg=CARD, activebackground=CARD,
                        highlightthickness=0)
    cb.pack(side="left", padx=(8, 4), pady=6)
    texts = tk.Frame(card, bg=CARD)
    texts.pack(side="left", fill="x", expand=True)
    tk.Label(texts, text=title, bg=CARD, fg=TEXT, font=FONT, anchor="w").pack(fill="x")
    if sub:
        tk.Label(texts, text=sub, bg=CARD, fg=DIM, font=FONT_DIM, anchor="w").pack(fill="x")
    for text, bg, fg in badges:
        _badge(card, text, bg, fg).pack(side="right", padx=4)


def _scrollable(parent):
    canvas = tk.Canvas(parent, bg=BG, highlightthickness=0)
    scrollbar = tk.Scrollbar(parent, orient="vertical", command=canvas.yview)
    inner = tk.Frame(canvas, bg=BG)
    inner.bind("<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=inner, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
    # Keep inner width in sync so rows fill the window.
    canvas.bind("<Configure>", lambda e: canvas.itemconfig("all", width=e.width))
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    return inner


# ---------------------------------------------------------------- setup window

def open_setup_window():
    from . import collect_snapshot  # lazy: keeps CLI/import light

    win = tk.Toplevel()
    win.title("prevstate — Set new environment")
    win.geometry("560x720")
    win.minsize(480, 500)
    _style(win)

    status = tk.Label(win, text="Scanning running apps…", bg=BG, fg=DIM, font=FONT)
    status.pack(pady=40)

    def build(snap):
        status.destroy()
        body = tk.Frame(win, bg=BG)
        body.pack(fill="both", expand=True)
        inner = _scrollable(body)

        app_vars, tab_vars, term_vars = [], [], []

        # Apps, grouped by exe so multiple instances expand underneath.
        sec = _section(inner, "APPS IN CURRENT WORKSPACE")
        groups = {}
        for i, a in enumerate(snap.get("apps", [])):
            groups.setdefault(a.get("name") or a.get("exe") or "?", []).append((i, a))
        for exe, rows in sorted(groups.items()):
            tk.Label(sec, text=exe, bg=BG, fg=DIM, font=FONT_DIM, anchor="w").pack(fill="x")
            for i, a in rows:
                v = tk.BooleanVar(value=True)
                app_vars.append((i, v))
                _row(sec, v, a.get("title", "?"), a.get("label", ""))

        # Chrome, grouped per instance/profile.
        sec = _section(inner, "ACTIVE CHROME TABS")
        chrome = snap.get("chrome", {})
        flat_index = {id(t): n for n, t in enumerate(chrome.get("tabs", []))}
        for inst in chrome.get("instances", []):
            header = f"Profile: {inst.get('profile') or 'Default'}  (:{inst.get('port')})"
            tk.Label(sec, text=header, bg=BG, fg=DIM, font=FONT_DIM, anchor="w").pack(fill="x")
            if not inst.get("cdp_available"):
                r = tk.Frame(sec, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
                r.pack(fill="x", pady=2)
                tk.Label(r, text="No tab URLs — start this profile with --remote-debugging-port",
                         bg=CARD, fg=DIM, font=FONT_DIM).pack(side="left", padx=8, pady=6)
                _badge(r, "CDP OFF", ORANGE_BG, ORANGE_FG).pack(side="right", padx=8)
                continue
            for t in inst.get("tabs", []):
                v = tk.BooleanVar(value=True)
                tab_vars.append((flat_index[id(t)], v))
                _row(sec, v, t.get("title") or t["url"], t["url"])

        # Terminals.
        sec = _section(inner, "TERMINAL INSTANCES")
        for n, t in enumerate(snap.get("terminals", [])):
            v = tk.BooleanVar(value=True)
            term_vars.append((n, v))
            env = t.get("venv") or t.get("conda") or ""
            badges = []
            if env:
                short = env.replace("\\", "/").rstrip("/").split("/")[-2:]
                badges.append(("venv: " + "/".join(short), GREEN_BG, GREEN_FG))
            _row(sec, v, f"{t.get('shell', '?')} — {t.get('cwd', '')}", t.get("cmdline", ""),
                 badges)

        # Meta fields.
        meta = tk.Frame(inner, bg=BG)
        meta.pack(fill="x", padx=12, pady=8)
        entries = {}
        for key, label in (("name", "Snapshot name"), ("doing", "Doing"),
                           ("done", "Done"), ("todo", "Todo")):
            tk.Label(meta, text=label, bg=BG, fg=DIM, font=FONT_DIM, width=14,
                     anchor="w").grid(row=len(entries), column=0, sticky="w", pady=3)
            e = tk.Entry(meta, bg=CARD, fg=TEXT, insertbackground=TEXT,
                         highlightbackground=BORDER, highlightthickness=1,
                         relief="flat", width=40)
            e.grid(row=len(entries), column=1, sticky="ew", pady=3)
            entries[key] = e
        meta.columnconfigure(1, weight=1)
        entries["name"].insert(0, datetime.now().strftime("snapshot-%Y%m%d-%H%M"))

        preview = tk.Label(inner, text="", bg=BG, fg=DIM, font=("Segoe UI", 9, "italic"),
                           wraplength=500, justify="left")
        preview.pack(fill="x", padx=12, pady=4)

        def refresh_preview(*_a):
            na = sum(1 for _, v in app_vars if v.get())
            nt = sum(1 for _, v in tab_vars if v.get())
            nm = sum(1 for _, v in term_vars if v.get())
            nm_ = entries["name"].get().strip() or "(unnamed)"
            preview.config(text=f"Preview: Will save {na} apps, {nt} tabs, and {nm} terminals under '{nm_}'")

        for _, v in app_vars + tab_vars + term_vars:
            v.trace_add("write", refresh_preview)
        entries["name"].bind("<KeyRelease>", refresh_preview)
        refresh_preview()

        btns = tk.Frame(win, bg=PANEL)
        btns.pack(fill="x", side="bottom")
        tk.Button(btns, text="Cancel", command=win.destroy, bg=CARD, fg=TEXT,
                  activebackground=BORDER, relief="flat", padx=16).pack(side="right", padx=8, pady=10)

        def on_save():
            from . import save_filtered  # lazy

            try:
                path = save_filtered(
                    snap,
                    keep_apps=[i for i, v in app_vars if v.get()],
                    keep_tabs=[i for i, v in tab_vars if v.get()],
                    keep_terminals=[n for n, v in term_vars if v.get()],
                    name=(entries["name"].get().strip() or None),
                    doing=entries["doing"].get().strip(),
                    done=entries["done"].get().strip(),
                    todo=entries["todo"].get().strip(),
                )
            except Exception as e:
                messagebox.showerror("prevstate", f"Save failed:\n{e}", parent=win)
                return
            messagebox.showinfo("prevstate", f"Saved:\n{path.name}", parent=win)
            win.destroy()

        tk.Button(btns, text="Save", command=on_save, bg=ACCENT, fg="white",
                  activebackground=ACCENT, relief="flat", padx=20).pack(side="right", pady=10)

    def worker(q):
        try:
            q.put(("ok", collect_snapshot()))
        except Exception as e:
            q.put(("err", e))

    q: queue.Queue = queue.Queue()
    threading.Thread(target=worker, args=(q,), daemon=True).start()

    def poll():
        try:
            status_kind, payload = q.get_nowait()
        except queue.Empty:
            if status.winfo_exists():
                win.after(100, poll)
            return
        if status_kind == "err":
            if status.winfo_exists():
                status.config(text=f"Scan failed: {payload}")
            return
        build(payload)

    win.after(100, poll)


# -------------------------------------------------------------- restore window

def open_restore_window():
    from . import load_snapshot, restore_snapshot  # lazy
    from .store import delete, list_snapshots

    win = tk.Toplevel()
    win.title("prevstate — Restore State Picker")
    win.geometry("520x560")
    win.minsize(440, 400)
    _style(win)
    tk.Label(win, text="SAVED SNAPSHOTS", font=FONT_TITLE, bg=BG, fg=TEXT,
             anchor="w").pack(fill="x", padx=12, pady=(12, 4))
    body = tk.Frame(win, bg=BG)
    body.pack(fill="both", expand=True)
    inner = _scrollable(body)

    def refresh():
        for w in inner.winfo_children():
            w.destroy()
        for path in list_snapshots():
            try:
                snap, _ = load_snapshot(path.name)
            except Exception:
                continue
            summary = snap.get("summary", {})
            card = tk.Frame(inner, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
            card.pack(fill="x", padx=12, pady=4)
            top = tk.Frame(card, bg=CARD)
            top.pack(fill="x", padx=10, pady=(8, 0))
            tk.Label(top, text=path.stem, bg=CARD, fg=TEXT,
                     font=("Segoe UI", 10, "bold"), anchor="w").pack(fill="x")
            sub = f"Saved {rel_time(snap.get('taken_at', ''))}"
            if summary.get("doing"):
                sub += f' • "{summary["doing"]}"'
            tk.Label(card, text=sub, bg=CARD, fg=DIM, font=FONT_DIM,
                     anchor="w", wraplength=460, justify="left").pack(fill="x", padx=10)
            row = tk.Frame(card, bg=CARD)
            row.pack(fill="x", padx=10, pady=8)
            counts = (f"{len(snap.get('apps', []))} apps",
                      f"{len(snap.get('chrome', {}).get('tabs', []))} tabs",
                      f"{len(snap.get('terminals', []))} terminals")
            for c in counts:
                _badge(row, c, GREEN_BG, GREEN_FG).pack(side="left", padx=2)

            def do_restore(p=path):
                try:
                    s, _ = load_snapshot(p.name)
                    report = restore_snapshot(s)
                except Exception as e:
                    messagebox.showerror("prevstate", f"Restore failed:\n{e}", parent=win)
                    return
                lines = [f"Chrome: {report.get('chrome')}"]
                lines += list(report.get("terminals", [])) or ["No terminals"]
                messagebox.showinfo("prevstate", "\n".join(lines), parent=win)

            def do_delete(p=path):
                if messagebox.askyesno("prevstate", f"Delete {p.name}?", parent=win):
                    delete(p.name)
                    refresh()

            tk.Button(row, text="Delete", command=do_delete, bg=CARD, fg=RED,
                      activebackground=BORDER, relief="flat", highlightbackground=RED,
                      highlightthickness=1, padx=10).pack(side="right", padx=4)
            tk.Button(row, text="Restore", command=do_restore, bg=ACCENT, fg="white",
                      activebackground=ACCENT, relief="flat", padx=14).pack(side="right")

    refresh()
    tk.Button(win, text="Close", command=win.destroy, bg=CARD, fg=TEXT,
              activebackground=BORDER, relief="flat", padx=20).pack(side="bottom", pady=10)
