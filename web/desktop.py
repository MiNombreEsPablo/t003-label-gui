"""The desktop shell: the same web UI in a native window, with the engine and printer running natively in Python.

    python web/desktop.py          (needs pywebview and a web engine: `pip install pywebview`; on Linux Qt or GTK)

The page is served by the dev server on a free local port and opened with ?client=desktop, which makes it use the
bridge (src/t003gui/bridge.py) instead of Pyodide and Web Bluetooth.
"""
from __future__ import annotations

import os
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import dev_server  # noqa: E402

from t003gui.bridge import Bridge  # noqa: E402


class Dialogs:
    """The shell's native file dialogs, for the bridge (which doesn't know the toolkit)."""

    def __init__(self) -> None:
        self.window = None  # set once the window exists

    def save(self, suggested_name: str, kind: str) -> str | None:
        import webview

        suffix = os.path.splitext(suggested_name)[1]  # the file type: ".png", ".t003label"
        result = self.window.create_file_dialog(
            webview.SAVE_DIALOG, save_filename=suggested_name, file_types=(f"{kind} (*{suffix})",))
        if isinstance(result, (list, tuple)):  # some toolkits answer with a tuple of one path
            result = result[0] if result else None
        if result and suffix and not result.lower().endswith(suffix.lower()):
            result += suffix
        return result or None


def main() -> None:
    import webview  # imported here so that the rest of this file can be tested without it

    server = dev_server.make_server(port=0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{server.server_address[1]}/?client=desktop"
    dialogs = Dialogs()
    dialogs.window = webview.create_window("T003 Label Studio", url, js_api=Bridge(dialogs=dialogs), width=520, height=860)
    webview.start()


if __name__ == "__main__":
    main()
