# prevstate

Save your machine's working state, restore it later. On-demand snapshots of running apps (with window positions), Chrome tabs (per profile), and Windows Terminal sessions (folder + venv) — plus a short doing/done/todo note. No daemon, no background polling.

## Install

```sh
pip install -r requirements.txt
```

Requires Python 3.12 on Windows. Backend deps: `psutil`, `pywin32`. UI deps (your side): `pystray`, `pillow`.

## Usage

Tray app (matches `design/prevstate-suite-canvas.png`):

```sh
python -m prevstate
```

Right-click the tray icon → **Set a new environment** (tick apps/tabs/terminals, name it, Save) or **Restore prevstate** (pick a snapshot, Restore/Delete). `Win+Shift+R` opens Restore when the optional `keyboard` package is installed.

CLI (same backend, no window):

```sh
python -m prevstate.cli save [--doing X --done Y --todo Z] [--out name.json]
python -m prevstate.cli list
python -m prevstate.cli show <file> [--json]
python -m prevstate.cli restore <file> [--no-chrome --no-terminals]
```

Snapshots live in `%LOCALAPPDATA%\prevstate\snapshot-*.json`.

### Chrome tabs

Chromium exposes tab URLs only over the DevTools protocol, so each Chrome profile needs its own debug port:

```sh
chrome.exe --remote-debugging-port=9222
chrome.exe --remote-debugging-port=9232 --profile-directory="Profile 1"
```

Without this, snapshots record `cdp_available=false` (CDP OFF badge in the UI) and restore reports "no urls".

### Typical flow

1. End of day: tray → **Set a new environment** → tick the apps, tabs, and terminals to keep → name it, fill doing/done/todo → Save.
2. Later: tray → **Restore prevstate** → pick a snapshot → terminals reopen in their folders with venvs re-activated, Chrome reopens per profile.

## Documentation

### Architecture

- `prevstate/windows.py` — one `EnumWindows` pass (`pywin32`, `ctypes` fallback). One row per window: `{title, rect, pid, exe, name, label}`. The `label` (`title — WxH @ X,Y`) lets the UI tell same-exe instances apart.
- `prevstate/chrome.py` — discovers `--remote-debugging-port` / `--profile-directory` from running chrome processes (stdlib `urllib`, one request per port). Returns flat `tabs` (each tagged `profile` + `port`) plus grouped `instances[{port, profile, cdp_available, tabs}]`.
- `prevstate/terminal.py` — Windows Terminal children with `{shell, cwd, venv, conda, history_tail}`. `environ()` is read only for terminal PIDs (it's expensive).
- `prevstate/store.py` — atomic JSON writes to `%LOCALAPPDATA%\prevstate\`, keeps the newest 20. Old `%LOCALAPPDATA%\previousstate\` snapshots are still readable.
- `prevstate/snapshot.py` — `collect_snapshot()`, auto summary heuristic, `restore_snapshot()`.
- `prevstate/__init__.py` — stable UI contract (see below). `prevstate/cli.py` — matching CLI.

### UI contract

```python
import prevstate

snap = prevstate.collect()          # full snapshot
prevstate.save_filtered(            # save what the user ticked
    snap, keep_apps=[0, 2],         # indices into snap["apps"] (None = all)
    keep_tabs=[0, 1],               # indices into flat snap["chrome"]["tabs"]
    keep_terminals=None,
    name="feature-x.json",
    doing="...", done="...", todo="...",
)
prevstate.list_names()              # ["snapshot-....json", ...]
snap = prevstate.load_snapshot(name)
prevstate.restore_snapshot(snap)    # {"chrome": ..., "terminals": [...]}
```

Group apps by exe/name and show `label`; group tabs under `instances[]` headers (`Profile — port`), with the CDP OFF badge when `cdp_available` is false.

### Restore behavior

Restore is relaunch, not hibernate: fresh shells in the same folder with the venv activation command, one Chrome process per profile. Unsaved files, live process output, and SSH sessions don't come back. Window `rect`s are recorded for the UI to apply; PIDs in snapshots are stale by definition.

### Power notes

No daemon or watchers — collect runs once and exits. Imports of `psutil`/`pywin32` are lazy, process enumeration is a single pass, and Chrome is queried at most once per debug port.
