"""The `t003-gui` command: open the web UI in a native window (the Qt window is the legacy one, `--qt`)."""
from __future__ import annotations

import sys
from pathlib import Path

MISSING_QT = (
    "The legacy Qt window needs PySide6, which isn't installed.\n"
    "  pip install 't003-label-gui[gui]'\n"
    "The command-line tool works without it: t003-print --help"
)
MISSING_WEBVIEW = (
    "The T003 Label Studio window needs pywebview, which isn't installed.\n"
    "  pip install 't003-label-gui[web]'      (Linux without WebKitGTK: 't003-label-gui[web-qt]')\n"
    "The command-line tool works without it: t003-print --help"
)
NO_TOOLKIT = (
    "pywebview found no window toolkit. On Linux install WebKitGTK and PyGObject from your distribution\n"
    "(Arch: webkit2gtk-4.1 python-gobject; Debian/Ubuntu: gir1.2-webkit2-4.1 python3-gi), or use QtWebEngine:\n"
    "  pip install 't003-label-gui[web-qt]'"
)


class ShellUnavailable(Exception):
    """The web window can't start here: pywebview or its window toolkit is missing."""


def qt_window() -> None:
    try:
        from .app import main as run
    except ImportError as e:
        if (e.name or "").split(".")[0] != "PySide6":
            raise  # a genuine bug, not the missing optional dependency
        sys.exit(MISSING_QT)
    run()


def run_shell() -> None:
    """The web UI in a native window (src/t003gui/web/desktop.py); raises ShellUnavailable when it can't open."""
    web = Path(__file__).resolve().parent / "web"
    sys.path.insert(0, str(web))  # the shell and the dev server import each other as plain modules
    try:
        import desktop
        desktop.main()
    except ImportError as e:
        if (e.name or "").split(".")[0] != "webview":
            raise
        raise ShellUnavailable(MISSING_WEBVIEW) from e
    except Exception as e:
        if type(e).__name__ == "WebViewException":  # pywebview's own: no toolkit it can use
            raise ShellUnavailable(f"{NO_TOOLKIT}\n({e})") from e
        raise


def web_shell() -> None:
    try:
        run_shell()
    except ShellUnavailable as e:
        sys.exit(str(e))


def shell_main() -> None:
    """The entry of the packaged app: the window, or `--selftest` to prove the bundle is complete."""
    from . import applog

    applog.start()  # a windowed build has no console: whatever goes wrong is in this file
    if "--selftest" in sys.argv:
        from .selftest import run

        sys.exit(run(web=True))
    try:
        run_shell()
    except ShellUnavailable as e:
        applog.record(e)
        sys.exit(f"{e}\n\nLog: {applog.log_path()}")
    except Exception as e:
        applog.record(e)
        raise SystemExit(f"T003 Label Studio couldn't start: {e}\n\nLog: {applog.log_path()}") from e


def main() -> None:
    if "--qt" in sys.argv[1:]:
        return qt_window()
    if "--web" in sys.argv[1:]:  # what the flag said before the web window became the default
        return web_shell()
    try:
        run_shell()
    except ShellUnavailable as e:
        try:  # an install that has only the old window still works, with a pointer to the new one
            import PySide6  # noqa: F401
        except ImportError:
            sys.exit(str(e))
        print("The web window isn't available here, opening the legacy Qt window instead.\n" + str(e), file=sys.stderr)
        qt_window()
