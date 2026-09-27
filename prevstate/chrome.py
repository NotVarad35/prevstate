"""Chrome tabs via DevTools Protocol. stdlib only, single HTTP call, short timeout."""
import json
import urllib.request

CDP_URL = "http://127.0.0.1:9222/json/list"


def get_chrome_tabs(timeout=1.5):
    """Return {'cdp_available': bool, 'tabs': [{url, title}]}.

    Requires Chrome started once with --remote-debugging-port=9222.
    No polling, no scraping — one request per snapshot.
    """
    try:
        with urllib.request.urlopen(CDP_URL, timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8", "replace"))
    except Exception as e:
        return {"cdp_available": False, "error": f"{type(e).__name__}: {e}", "tabs": []}
    tabs = []
    for t in data:
        if not isinstance(t, dict) or t.get("type") != "page":
            continue
        url = t.get("url", "")
        if not url or url.startswith(("chrome://", "chrome-extension://", "devtools://")):
            continue
        tabs.append({"url": url[:2048], "title": str(t.get("title", ""))[:256]})
    return {"cdp_available": True, "tabs": tabs}


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
