"""`python -m prevstate` → tray app. `python -m prevstate.cli` → CLI."""
try:
    from .tray import main
except ImportError:
    # Running as a script: `python prevstate/__main__.py` from the repo root.
    import os
    import sys

    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from prevstate.tray import main

if __name__ == "__main__":
    main()
