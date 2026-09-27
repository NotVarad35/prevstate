# AGENTS.md

`prevstate` (previous state). Python 3.12, Windows-only backend. Deps in `requirements.txt`: `psutil`, `pywin32` (backend); `pystray`, `pillow` (UI side, owned by user).

## Commands
- Setup: `pip install -r requirements.txt`
- Snapshot: `python -m prevstate.cli save [--doing X --done Y --todo Z]`
- List/show: `python -m prevstate.cli list` / `show <file> [--json]`
- Restore: `python -m prevstate.cli restore <file> [--no-chrome --no-terminals]`
- Snapshots: `%LOCALAPPDATA%\prevstate\snapshot-*.json` (`prevstate/store.py`); legacy `%LOCALAPPDATA%\previousstate\` read-only fallback.

## Architecture
- No daemon — on-demand collect then exit. Don't add polling/watchers.
- `prevstate/windows.py`: single `EnumWindows` pass; `pywin32` preferred, `ctypes` fallback. Lazy imports. Each window is a separate app row — UI groups by exe and shows `label` (`title — WxH @ X,Y`) for instance picking.
- `prevstate/chrome.py`: discovers `--remote-debugging-port`/`--profile-directory` from chrome processes, one stdlib HTTP call per port. Returns flat `tabs` (each tagged `profile`+`port`) + grouped `instances[]`; unreachable ports get `cdp_available=false` (CDP OFF badge). Start each profile's Chrome with its own debug port or its URLs are invisible.
- `prevstate/terminal.py`: only terminal PIDs get `environ()` (expensive). Venv re-activation via `activate_command()` per shell.
- `prevstate/snapshot.py:build_summary`: auto summary; `doing/done/todo` filled by UI.
- `prevstate/__init__.py`: stable UI contract — `collect()`, `save_filtered(snap, keep_apps, keep_tabs, keep_terminals, ...)`, `list_names()`, `load_snapshot()`, `restore_snapshot()`. UI (tkinter+pystray tray: Set new environment / Restore prevstate / Quit) is user-owned; keep backend UI-free.
- Restore relaunches (fresh shells + one Chrome process), never resumes in-memory state. PIDs stale — window moves best-effort.

## Rules
- Reuse stdlib/`psutil`/`pywin32` before custom code. Keep imports lazy and single-pass.
- Don't touch UI files; backend contract lives in `prevstate/__init__.py` + `cli.py`.
