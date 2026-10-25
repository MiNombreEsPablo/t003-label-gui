"""The `t003-gui` command: start the window, or say what to install if the optional Qt part is missing."""
from __future__ import annotations

import sys
from pathlib import Path

MISSING_QT = (
    "The T003 Label Studio window needs PySide6, which isn't installed.\n"
    "  pip install 't003-label-gui[gui]'\n"
    "The command-line tool works without it: t003-print --help"
)


MISSING_WEBVIEW = (
    "The web window needs pywebview, which isn't installed.\n"
    "  pip install 't003-label-gui[web]'      (Linux without WebKitGTK: 't003-label-gui[web-qt]')"
)
NO_TOOLKIT = (
    "pywebview found no window toolkit. On Linux install WebKitGTK and PyGObject from your distribution\n"
    "(Arch: webkit2gtk-4.1 python-gobject; Debian/Ubuntu: gir1.2-webkit2-4.1 python3-gi), or use QtWebEngine:\n"
    "  pip install 't003-label-gui[web-qt]'"
)


def shell_main() -> None:
    """The entry of the packaged web app: the window, or `--selftest` to prove the bundle is complete."""
    if "--selftest" in sys.argv:
        from .selftest import run

        sys.exit(run(web=True))
    web_shell()


def web_shell() -> None:
    """The web UI in a native window (src/t003gui/web/desktop.py), the Qt window's successor."""
    web = Path(__file__).resolve().parent / "web"
    sys.path.insert(0, str(web))  # the shell and the dev server import each other as plain modules
    try:
        import desktop
        desktop.main()
    except ImportError as e:
        if (e.name or "").split(".")[0] != "webview":
            raise
        sys.exit(MISSING_WEBVIEW)
    except Exception as e:
        if type(e).__name__ == "WebViewException":  # pywebview's own: no toolkit it can use
            sys.exit(f"{NO_TOOLKIT}\n({e})")
        raise


def main() -> None:
    if "--web" in sys.argv[1:]:
        return web_shell()
    try:
        from .app import main as run
    except ImportError as e:
        if (e.name or "").split(".")[0] != "PySide6":
            raise  # a genuine bug, not the missing optional dependency
        sys.exit(MISSING_QT)
    run()
