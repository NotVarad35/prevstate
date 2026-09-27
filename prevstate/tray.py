"""System-tray entrypoint: Set new environment / Restore prevstate / Quit.

Icon is drawn at runtime with Pillow — no asset files needed.
Win+Shift+R hotkey is best-effort: enabled when the `keyboard` package is
installed, silently skipped otherwise (tray menu always works).
"""
import threading
import tkinter as tk


def _make_icon():
    from PIL import Image, ImageDraw

    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([4, 4, size - 4, size - 4], radius=14, fill="#2f7cf6")
    d.arc([16, 20, 42, 46], start=120, end=60, fill="white", width=5)  # clock face
    d.line([29, 26, 29, 35], fill="white", width=4)
    d.line([29, 35, 37, 35], fill="white", width=4)
    return img


def _hotkey(root):
    try:
        import keyboard  # optional; tray menu is the supported path
    except Exception:
        return
    try:
        from .ui import open_restore_window

        keyboard.add_hotkey("windows+shift+r",
                            lambda: root.after(0, open_restore_window),
                            suppress=False)
    except Exception:
        pass


def main():
    import pystray

    from .ui import open_restore_window, open_setup_window

    root = tk.Tk()
    root.withdraw()  # tray owns the lifecycle; windows are Toplevels
    threading.Thread(target=_hotkey, args=(root,), daemon=True).start()

    def show_setup(icon=None, _item=None):
        root.after(0, open_setup_window)

    def show_restore(icon=None, _item=None):
        root.after(0, open_restore_window)

    def quit_app(icon=None, _item=None):
        try:
            icon.stop()
        except Exception:
            pass
        root.after(0, root.destroy)

    menu = pystray.Menu(
        pystray.MenuItem("Set a new environment", show_setup, default=True),
        pystray.MenuItem("Restore prevstate", show_restore),
        pystray.MenuItem("Quit", quit_app),
    )
    icon = pystray.Icon("prevstate", _make_icon(), "prevstate", menu)

    threading.Thread(target=icon.run, daemon=True).start()
    root.mainloop()
    try:
        icon.stop()
    except Exception:
        pass


if __name__ == "__main__":
    main()
