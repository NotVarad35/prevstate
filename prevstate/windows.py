"""Window enumeration: one EnumWindows pass. pywin32 preferred, ctypes fallback."""
import ctypes


def _enum_via_pywin32():
    import win32gui
    import win32process

    out = []

    def cb(hwnd, _):
        try:
            if not win32gui.IsWindowVisible(hwnd):
                return
            title = win32gui.GetWindowText(hwnd)
            if not title or not title.strip():
                return
            rect = win32gui.GetWindowRect(hwnd)
            x0, y0, x1, y1 = rect
            if x1 - x0 <= 0 or y1 - y0 <= 0:
                return
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            out.append({"hwnd": hwnd, "title": title[:256], "rect": [x0, y0, x1, y1], "pid": pid})
        except Exception:
            return

    win32gui.EnumWindows(cb, None)
    return out


def _enum_via_ctypes():
    user32 = ctypes.windll.user32
    out = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def cb(hwnd, _):
        try:
            if not user32.IsWindowVisible(hwnd):
                return True
            length = user32.GetWindowTextLengthW(hwnd)
            if not length:
                return True
            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buf, length + 1)
            title = buf.value
            if not title or not title.strip():
                return True
            from ctypes import wintypes

            rect = wintypes.RECT()
            if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
                return True
            pid = ctypes.c_ulong()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            w, h = rect.right - rect.left, rect.bottom - rect.top
            if w <= 0 or h <= 0:
                return True
            out.append({
                "hwnd": int(hwnd),
                "title": title[:256],
                "rect": [rect.left, rect.top, rect.right, rect.bottom],
                "pid": int(pid.value),
            })
        except Exception:
            pass
        return True

    user32.EnumWindows(cb, None)
    return out


def enum_windows():
    """Single enumeration pass. Never polls; caller decides frequency."""
    try:
        return _enum_via_pywin32()
    except Exception:
        return _enum_via_ctypes()


def move_window(pid, title_hint, rect, timeout_s=10):
    """Best-effort move of a restored window. Short poll, then give up (low power)."""
    import time

    try:
        import win32gui
        import win32process
    except Exception:
        return False
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        found = []

        def cb(hwnd, _):
            try:
                if not win32gui.IsWindowVisible(hwnd):
                    return
                _, wpid = win32process.GetWindowThreadProcessId(hwnd)
                if wpid == pid:
                    found.append(hwnd)
            except Exception:
                return

        try:
            win32gui.EnumWindows(cb, None)
        except Exception:
            return False
        if found:
            try:
                x0, y0, x1, y1 = rect
                win32gui.SetWindowPos(found[0], 0, x0, y0, x1 - x0, y1 - y0, 0x0004)  # SWP_NOZORDER
                return True
            except Exception:
                return False
        time.sleep(0.5)
    return False
