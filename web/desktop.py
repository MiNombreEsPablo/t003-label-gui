"""The desktop shell: the same web UI in a native window, with the engine and printer running natively in Python.

    python web/desktop.py          (needs pywebview and a web engine: `pip install pywebview`; on Linux Qt or GTK)

The page is served by the dev server on a free local port and opened with ?client=desktop, which makes it use the
bridge (src/t003gui/bridge.py) instead of Pyodide and Web Bluetooth.
"""
from __future__ import annotations

import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import dev_server  # noqa: E402

from t003gui.bridge import Bridge  # noqa: E402


def main() -> None:
    import webview  # imported here so that the rest of this file can be tested without it

    server = dev_server.make_server(port=0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{server.server_address[1]}/?client=desktop"
    webview.create_window("T003 Label Studio", url, js_api=Bridge(), width=520, height=860)
    webview.start()


if __name__ == "__main__":
    main()
