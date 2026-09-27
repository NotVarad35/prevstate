"""Orchestrator: single-pass collect, summary heuristic, restore."""
import os
import subprocess
from collections import Counter
from datetime import datetime, timezone
from urllib.parse import urlparse

from . import chrome as chrome_mod
from . import terminal as terminal_mod
from . import windows as windows_mod


def collect_snapshot():
    # One process_iter pass for pid -> exe/cmdline (avoids N syscalls).
    pid_meta = {}
    try:
        import psutil  # lazy import: `show`/`list` stay light

        for p in psutil.process_iter(attrs=["pid", "name", "exe", "cmdline"]):
            try:
                info = p.info
                pid_meta[info["pid"]] = {
                    "exe": info.get("exe") or "",
                    "name": info.get("name") or "",
                    "cmdline": " ".join((info.get("cmdline") or [])[:6])[:512],
                }
            except Exception:
                continue
    except Exception:
        pass

    wins = windows_mod.enum_windows()
    apps = []
    for w in wins:
        meta = pid_meta.get(w["pid"], {})
        # Skip our own snapshot console to reduce noise? Keep — cheap to filter in GUI.
        apps.append({
            "title": w["title"], "rect": w["rect"], "pid": w["pid"],
            "exe": meta.get("exe", ""), "name": meta.get("name", ""),
        })

    chrome_data = chrome_mod.get_chrome_tabs()
    terms = terminal_mod.get_terminals()

    snapshot = {
        "version": 1,
        "taken_at": datetime.now(timezone.utc).isoformat(),
        "apps": apps,
        "chrome": chrome_data,
        "terminals": terms,
        "summary": build_summary(apps, chrome_data, terms),
    }
    return snapshot


def build_summary(apps, chrome_data, terms):
    top = Counter(a.get("name") or a.get("exe") for a in apps).most_common(8)
    cwds = sorted({t["cwd"] for t in terms if t.get("cwd")})[:10]
    venvs = sorted({t["venv"] or t["conda"] for t in terms if t.get("venv") or t.get("conda")})[:10]
    domains = Counter()
    for t in chrome_data.get("tabs", []):
        try:
            domains[urlparse(t["url"]).netloc].update()
        except Exception:
            continue
    lines = []
    if top:
        lines.append("Apps: " + ", ".join(f"{n or '?'}({c})" for n, c in top))
    if cwds:
        lines.append("Terminal cwds: " + "; ".join(cwds))
    if venvs:
        lines.append("Envs: " + "; ".join(venvs))
    if domains:
        lines.append("Tabs: " + ", ".join(f"{d}({c})" for d, c in domains.most_common(6)))
    return {
        "auto": " | ".join(lines)[:2000],
        "doing": "", "done": "", "todo": "",  # filled by user/GUI
    }


def restore_snapshot(snap, move_windows=True, open_terminals=True, open_chrome=True):
    """Best-effort relaunch. Returns report dict."""
    report = {"chrome": "skipped", "terminals": [], "window_moves": 0}

    if open_chrome:
        tabs = snap.get("chrome", {}).get("tabs", [])
        urls = [t["url"] for t in tabs if t.get("url")]
        if urls:
            exe = chrome_mod.chrome_exe_hint()
            try:
                # One Chrome process for all URLs (low power) instead of N launches.
                subprocess.Popen([exe, *urls[:30]],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                report["chrome"] = f"opened {min(len(urls), 30)} urls"
            except Exception as e:
                report["chrome"] = f"failed: {e}"
        else:
            report["chrome"] = "no urls (CDP off at snapshot?)" if not snap.get("chrome", {}).get("cdp_available") else "no tabs"

    if open_terminals:
        wt = _find_wt()
        for t in snap.get("terminals", [])[:10]:
            cwd = t.get("cwd") or os.path.expanduser("~")
            if not os.path.isdir(cwd):
                cwd = os.path.expanduser("~")
            act = terminal_mod.activate_command(t.get("shell", ""), t.get("venv", ""), t.get("conda", ""))
            shell = t.get("shell", "powershell.exe")
            try:
                if wt:
                    # wt new-tab keeps one Terminal window (cheaper than N windows).
                    cmd = [wt, "new-tab", "-d", cwd]
                    if act:
                        cmd += [shell, "-NoExit", "-Command", act]
                    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                else:
                    subprocess.Popen([shell], cwd=cwd,
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                report["terminals"].append(f"{shell} @ {cwd} {'+venv' if act else ''}")
            except Exception as e:
                report["terminals"].append(f"failed {shell} @ {cwd}: {e}")

    # Window moves intentionally skipped on restore: PIDs are stale.
    # Rects are kept in snapshot for the future GUI to apply to matched windows.
    return report


def _find_wt():
    import shutil

    for c in ("wt.exe", "wt"):
        p = shutil.which(c)
        if p:
            return p
    return None
