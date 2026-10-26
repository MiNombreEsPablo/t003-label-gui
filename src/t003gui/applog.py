"""The packaged app's log file: what to read when the window doesn't open.

A windowed build has no console, so a startup failure would only show as a dialog. `start()` records the environment and
everything the app logs or prints, and any uncaught error with its traceback, in one small file that
`log_path()` names. Qt-free, and it never raises: a log that can't be written is no reason to stop the app.
"""
from __future__ import annotations

import faulthandler
import logging
import os
import platform
import sys
import traceback
from pathlib import Path

from . import __version__

NAME = "t003-label-studio.log"
MAX_BYTES = 512 * 1024  # an older log this big is kept as .1 and a new one started
_stream = None  # kept open for faulthandler, which needs a real file


def log_path() -> Path:
    """Where the log lives (T003_LOG_DIR overrides it, for tests and for asking a user to put it somewhere findable)."""
    override = os.environ.get("T003_LOG_DIR")
    if override:
        return Path(override) / NAME
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local") / "T003 Label Studio"
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Logs" / "T003 Label Studio"
    else:
        base = Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local" / "state") / "t003-label-gui"
    return base / NAME


def start() -> Path | None:
    """Begin logging to the file; returns its path, or None if it can't be written."""
    global _stream
    try:
        path = log_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and path.stat().st_size > MAX_BYTES:
            path.replace(path.with_suffix(".log.1"))
        _stream = open(path, "a", encoding="utf-8", buffering=1)
    except OSError:
        return None
    if sys.stdout is None or sys.stderr is None:  # windowed: nothing to print to, so prints land in the file
        sys.stdout = sys.stdout or _stream
        sys.stderr = sys.stderr or _stream
    handler = logging.StreamHandler(_stream)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root = logging.getLogger()
    root.addHandler(handler)
    root.setLevel(logging.INFO)
    logging.getLogger("pywebview").setLevel(logging.DEBUG)  # the window toolkit says what it picked and why it failed
    faulthandler.enable(_stream)  # a crash inside native code leaves a Python stack

    def hook(kind, value, tb):
        logging.getLogger("t003gui").error("uncaught %s", kind.__name__, exc_info=(kind, value, tb))
        sys.__excepthook__(kind, value, tb)

    sys.excepthook = hook
    logging.getLogger("t003gui").info(
        "start: t003-label-gui %s, Python %s, %s, frozen=%s, exe=%s, args=%s",
        __version__, platform.python_version(), platform.platform(), getattr(sys, "frozen", False), sys.executable, sys.argv[1:])
    return path


def record(error: BaseException) -> None:
    """Write an error's traceback to the log (a caught one, the caller decides what to tell the user)."""
    logging.getLogger("t003gui").error("%s", "".join(traceback.format_exception(type(error), error, error.__traceback__)))
