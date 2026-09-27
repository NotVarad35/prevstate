"""Chrome tabs via DevTools Protocol. stdlib HTTP + psutil discovery, no polling.

Multi-instance / multi-profile: each Chrome instance/profile that was
launched with its own --remote-debugging-port is queried once per snapshot.
Instances without a debug port report cdp_available=False (Chromium exposes
no URL API for them); the UI shows the CDP OFF badge for those.
"""
import json
import re
import urllib.request

DEFAULT_PORT = 9222

_PORT_RE = re.compile(r"--remote-debugging-port[= ](\d+)", re.IGNORECASE)
_PROFILE_RE = re.compile(r"--profile-directory[= ]([^\s\"']+)", re.IGNORECASE)


def _parse_debug_port(cmdline):
    try:
        m = _PORT_RE.search(" ".join(cmdline or []))
        return int(m.group(1)) if m else None
    except Exception:
        return None


def _parse_profile(cmdline):
    try:
        m = _PROFILE_RE.search(" ".join(cmdline or []))
        return m.group(1) if m else ""
    except Exception:
        return ""


def _discover_ports():
    """Ports from running chrome processes + default. Cheap: one process_iter."""
    ports = {}  # port -> profile
    try:
        import psutil  # lazy: keeps `list`/`show` light

        for p in psutil.process_iter(attrs=["name", "cmdline"]):
            try:
                name = (p.info.get("name") or "").lower()
                if name not in ("chrome.exe", "chrome"):
                    continue
                cmd = p.info.get("cmdline") or []
                port = _parse_debug_port(cmd)
                if port:
                    ports.setdefault(port, _parse_profile(cmd))
            except Exception:
                continue
    except Exception:
        pass
    ports.setdefault(DEFAULT_PORT, ports.get(DEFAULT_PORT, ""))
    return ports


def _query_port(port, timeout):
    with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def _extract_tabs(data):
    tabs = []
    for t in data or []:
        if not isinstance(t, dict) or t.get("type") != "page":
            continue
        url = t.get("url", "")
        if not url or url.startswith(("chrome://", "chrome-extension://", "devtools://")):
            continue
        tabs.append({"url": url[:2048], "title": str(t.get("title", ""))[:256]})
    return tabs


def get_chrome_tabs(timeout=1.5, ports=None):
    """Return {'cdp_available': bool, 'tabs': flat [...], 'instances': [...]}.

    Each tab carries 'profile' + 'port'. 'instances' groups them per
    debug port: [{port, profile, cdp_available, tabs|error}].
    Flat 'tabs' + top-level 'cdp_available' are kept for backward compat.
    """
    port_profile = dict(ports) if ports else _discover_ports()
    instances = []
    flat = []
    for port, profile in sorted(port_profile.items()):
        try:
            tabs = _extract_tabs(_query_port(port, timeout))
        except Exception as e:
            instances.append({"port": port, "profile": profile, "cdp_available": False,
                              "error": f"{type(e).__name__}: {e}", "tabs": []})
            continue
        tagged = [{**t, "profile": profile, "port": port} for t in tabs]
        flat.extend(tagged)
        instances.append({"port": port, "profile": profile or "Default",
                          "cdp_available": True, "tabs": tagged})
    return {"cdp_available": any(i["cdp_available"] for i in instances),
            "tabs": flat, "instances": instances}


def chrome_exe_hint():
    """Common Chrome locations; no registry walk on every call."""
    import os

    candidates = [
        os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
    ]
    for p in candidates:
        if p and os.path.isfile(p):
            return p
    return "chrome.exe"  # rely on PATH
