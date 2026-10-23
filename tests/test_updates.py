import http.server
import threading
import time

import pytest
from PySide6.QtWidgets import QApplication

from t003gui import about, updates


def test_parse_version():
    assert updates.parse_version("v0.1.1") == (0, 1, 1)
    assert updates.parse_version("1.2") == (1, 2)
    assert updates.parse_version("1.0.0-rc1") is None  # prereleases are never offered
    assert updates.parse_version("nightly") is None


def test_tag_from_url():
    assert updates.tag_from_url("https://github.com/o/r/releases/tag/v0.2.0") == "v0.2.0"
    assert updates.tag_from_url("https://github.com/o/r/releases") is None


@pytest.mark.parametrize("current, tag, kind", [
    ("0.1.0", "v0.1.1", "newer"),
    ("0.1.0", "v0.1.0", "current"),
    ("0.2.0", "v0.1.9", "current"),  # a build newer than the newest release
    ("0.2", "v0.2.0", "current"),
    ("0.9.0", "v0.10.0", "newer"),  # numeric, not string, comparison
    ("0.1.0", "weird-tag", "unknown"),
    ("0.1.0", None, "unknown"),
])
def test_evaluate(current, tag, kind):
    assert updates.evaluate(current, tag).kind == kind


def test_describe_always_shows_the_running_version():
    for result in (updates.evaluate("0.1.0", "v0.1.1"), updates.evaluate("0.1.0", "v0.1.0"),
                   updates.UpdateResult("error", detail="offline")):
        assert "0.1.0" in updates.describe("0.1.0", result)
    assert "0.1.1" in updates.describe("0.1.0", updates.evaluate("0.1.0", "v0.1.1"))
    assert "offline" in updates.describe("0.1.0", updates.UpdateResult("error", detail="offline"))
    assert updates.evaluate("0.1.0", "v0.1.1").url.startswith(about.RELEASES_URL)


class _Server:
    """A local stand-in for GitHub: HEAD /releases/latest -> 302 to a tag page, or whatever `status` says."""

    def __init__(self, status=302, tag="v9.9.9"):
        outer = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_HEAD(self):
                self.send_response(outer.status)
                if outer.status == 302:
                    self.send_header("Location", f"/o/r/releases/tag/{outer.tag}")
                self.send_header("Content-Length", "0")
                self.end_headers()

            def log_message(self, *args):
                pass

        self.status, self.tag = status, tag
        self.httpd = http.server.HTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.httpd.server_port}/o/r/releases/latest"
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def close(self):
        self.httpd.shutdown()
        self.httpd.server_close()


def _check(url, current="0.1.0"):
    app = QApplication.instance() or QApplication([])
    checker = updates.UpdateChecker(current=current, url=url)
    results = []
    checker.finished.connect(results.append)
    checker.check()
    deadline = time.monotonic() + 10
    while not results and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.01)
    assert results, "no answer from the checker"
    return results[0]


def test_checker_reads_the_latest_tag_from_the_redirect():
    server = _Server(tag="v9.9.9")
    try:
        result = _check(server.url)
    finally:
        server.close()
    assert (result.kind, result.latest) == ("newer", "v9.9.9")
    assert _check_same_version_is_current()


def _check_same_version_is_current():
    server = _Server(tag="v0.1.0")
    try:
        return _check(server.url, current="0.1.0").kind == "current"
    finally:
        server.close()


def test_checker_handles_no_releases_and_no_network():
    server = _Server(status=404)
    try:
        assert _check(server.url).kind == "unknown"
    finally:
        server.close()
    result = _check("http://127.0.0.1:9/o/r/releases/latest")  # nothing listens on the discard port
    assert result.kind == "error" and result.url == about.RELEASES_URL


def test_checker_can_be_dropped_while_a_request_is_pending():
    import socket

    app = QApplication.instance() or QApplication([])
    silent = socket.socket()  # accepts connections (via the backlog) but never answers
    silent.bind(("127.0.0.1", 0))
    silent.listen(1)
    try:
        checker = updates.UpdateChecker(url=f"http://127.0.0.1:{silent.getsockname()[1]}/o/r/releases/latest")
        checker.check()
        app.processEvents()
        checker.deleteLater()  # what closing the dialog does
        for _ in range(20):
            app.processEvents()
            time.sleep(0.01)
    finally:
        silent.close()
