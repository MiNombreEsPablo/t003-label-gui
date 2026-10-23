"""Manual "Check for updates": ask GitHub which release is latest and compare it to this build.

`https://github.com/<repo>/releases/latest` answers with a 302 whose target ends in `/releases/tag/<tag>`, so one HEAD
request tells us the newest published release without the REST API (no JSON, no 60-calls-an-hour limit). Prereleases and
drafts are never "latest". Nothing here runs unless the user asks, and nothing is downloaded or installed.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from html import escape
from urllib.parse import unquote, urlparse

from PySide6.QtCore import QObject, QUrl, Signal
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest, QSslSocket

from . import __version__
from .about import RELEASES_URL

LATEST_URL = f"{RELEASES_URL}/latest"
TIMEOUT_MS = 8000


def parse_version(tag: str) -> tuple[int, ...] | None:
    """'v0.1.1' -> (0, 1, 1); None for anything that isn't plain numbers (e.g. '1.0.0-rc1')."""
    m = re.fullmatch(r"[vV]?(\d+(?:\.\d+)*)", tag.strip())
    return tuple(int(p) for p in m.group(1).split(".")) if m else None


def tag_from_url(url: str) -> str | None:
    path = urlparse(url).path
    return unquote(path.rsplit("/", 1)[-1]) if "/releases/tag/" in path else None


@dataclass(frozen=True)
class UpdateResult:
    kind: str  # "current" | "newer" | "unknown" | "error"
    latest: str | None = None  # the release tag, when known
    url: str | None = None  # where to download it / read about it
    detail: str = ""  # why a check failed


def evaluate(current: str, tag: str | None, page: str = RELEASES_URL) -> UpdateResult:
    """Compare this build's version with the latest release tag."""
    mine, theirs = parse_version(current), parse_version(tag or "")
    if tag is None or mine is None or theirs is None:
        return UpdateResult("unknown", tag, page, "couldn't tell which version is newest")
    width = max(len(mine), len(theirs))
    pad = lambda v: v + (0,) * (width - len(v))  # noqa: E731  (0.2 == 0.2.0)
    if pad(theirs) > pad(mine):
        return UpdateResult("newer", tag, f"{RELEASES_URL}/tag/{tag}")
    return UpdateResult("current", tag, f"{RELEASES_URL}/tag/{tag}")


def describe(current: str, result: UpdateResult) -> str:
    """Rich-text body for the update dialog; always starts with the version the user is running."""
    head = f"<p>You have version <b>{escape(current)}</b>.</p>"
    if result.kind == "current":
        return head + f"<p>You're up to date (latest release: {escape(result.latest or '')}).</p>"
    if result.kind == "newer":
        return head + f"<p>Version <b>{escape((result.latest or '').lstrip('vV'))}</b> is available.</p>"
    return head + f"<p>Couldn't check for updates: {escape(result.detail)}.</p>"


class UpdateChecker(QObject):
    finished = Signal(object)  # UpdateResult

    def __init__(self, current: str = __version__, url: str = LATEST_URL, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.current, self.url = current, url
        self._manager = QNetworkAccessManager(self)
        self._manager.setRedirectPolicy(QNetworkRequest.ManualRedirectPolicy)  # we want the redirect, not the page
        self._manager.finished.connect(self._on_reply)

    def check(self) -> None:
        if self.url.startswith("https") and not QSslSocket.supportsSsl():
            self._done(UpdateResult("error", url=RELEASES_URL, detail="this system has no TLS support for Qt"))
            return
        request = QNetworkRequest(QUrl(self.url))
        request.setHeader(QNetworkRequest.UserAgentHeader, f"t003-label-gui/{self.current}")
        request.setTransferTimeout(TIMEOUT_MS)
        self._manager.head(request)

    def _on_reply(self, reply: QNetworkReply) -> None:
        target = reply.attribute(QNetworkRequest.RedirectionTargetAttribute)
        status = reply.attribute(QNetworkRequest.HttpStatusCodeAttribute)
        error, message = reply.error(), reply.errorString()
        reply.deleteLater()
        if target is not None:
            self._done(evaluate(self.current, tag_from_url(reply.url().resolved(target).toString())))
        elif status == 404:
            self._done(UpdateResult("unknown", url=RELEASES_URL, detail="no releases have been published yet"))
        elif error != QNetworkReply.NoError:
            self._done(UpdateResult("error", url=RELEASES_URL, detail=message.rstrip(".").lower() or "network error"))
        else:
            self._done(UpdateResult("unknown", url=RELEASES_URL, detail="unexpected answer from GitHub"))

    def _done(self, result: UpdateResult) -> None:
        self.finished.emit(result)
