"""The `t003-gui` command: start the window, or say what to install if the optional Qt part is missing."""
from __future__ import annotations

import sys

MISSING_QT = (
    "The T003 Label Studio window needs PySide6, which isn't installed.\n"
    "  pip install 't003-label-gui[gui]'\n"
    "The command-line tool works without it: t003-print --help"
)


def main() -> None:
    try:
        from .app import main as run
    except ImportError as e:
        if (e.name or "").split(".")[0] != "PySide6":
            raise  # a genuine bug, not the missing optional dependency
        sys.exit(MISSING_QT)
    run()
