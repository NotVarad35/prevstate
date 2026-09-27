"""Windows Terminal state: cwd + venv. Only inspects terminal PIDs (cheap)."""
import os

TERMINAL_EXES = {"windowsterminal.exe", "wtexe", "wt.exe", "openconsole.exe"}
SHELL_EXES = {
    "powershell.exe", "pwsh.exe", "cmd.exe", "wsl.exe", "bash.exe",
    "ubuntu.exe", "python.exe", "pythonw.exe",
}

PS_HISTORY = os.path.expandvars(
    r"%APPDATA%\Microsoft\Windows\PowerShell\PSReadLine\ConsoleHost_history.txt"
)
PS_HISTORY5 = os.path.expandvars(
    r"%APPDATA%\Microsoft\Windows\PowerShell\PSReadLine\PowerShell_history.txt"
)


def _history_tail(path, n=20):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.read().splitlines()
        return lines[-n:]
    except Exception:
        return []


def _safe_cwd(proc):
    try:
        return proc.cwd()
    except Exception:
        return ""


def _safe_environ(proc):
    # environ() is expensive — call only for terminal candidates.
    try:
        return proc.environ()
    except Exception:
        return {}


def get_terminals():
    """Return [{shell, exe, pid, cwd, venv, conda, cmdline, history_tail}]."""
    import psutil  # lazy: keeps `list`/`show` imports light

    procs = list(psutil.process_iter(attrs=["pid", "name", "exe", "cmdline"]))
    by_pid = {p.info["pid"]: p for p in procs}
    terminals = []

    wt_pids = {p.info["pid"] for p in procs
               if (p.info.get("name") or "").lower() in TERMINAL_EXES}
    wt_children = set()
    for pid in wt_pids:
        try:
            parent = by_pid.get(pid)
            if parent is not None:
                for child in parent.children(recursive=True):
                    wt_children.add(child.pid)
        except Exception:
            continue

    for p in procs:
        name = (p.info.get("name") or "").lower()
        if name not in SHELL_EXES:
            continue
        if wt_pids and p.info["pid"] not in wt_children:
            # Shell running outside Windows Terminal — still record, flag it.
            outside = True
        else:
            outside = False
        proc = by_pid.get(p.info["pid"])
        cwd = _safe_cwd(proc) if proc else ""
        env = _safe_environ(proc) if proc else {}
        venv = env.get("VIRTUAL_ENV", "") or ""
        conda = env.get("CONDA_PREFIX", "") or ""
        try:
            cmdline = " ".join((p.info.get("cmdline") or [])[:8])[:512]
        except Exception:
            cmdline = ""
        terminals.append({
            "shell": name,
            "exe": p.info.get("exe") or "",
            "pid": p.info["pid"],
            "cwd": cwd,
            "venv": venv,
            "conda": conda,
            "cmdline": cmdline,
            "in_windows_terminal": not outside,
        })

    hist = _history_tail(PS_HISTORY) or _history_tail(PS_HISTORY5)
    if hist:
        for t in terminals:
            if t["shell"] in ("powershell.exe", "pwsh.exe"):
                t["history_tail"] = hist
    return terminals


def activate_command(shell, venv, conda):
    """Shell-specific venv re-activation string for restore. Empty if none."""
    target = venv or conda
    if not target:
        return ""
    s = shell.lower()
    if s in ("powershell.exe", "pwsh.exe"):
        return f'& "{target}\\Scripts\\Activate.ps1"'
    if s == "cmd.exe":
        return f'"{target}\\Scripts\\activate.bat"'
    # wsl/bash/python: best effort for Win venvs
    return f'source "{target}/Scripts/activate"'
