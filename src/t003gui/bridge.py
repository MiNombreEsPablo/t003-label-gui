"""The desktop shell's side of the web UI: the engine and the printer, as methods the page calls from JavaScript.

The web UI is written once and talks to two seams: an engine (label in, pixels out) and a printer (label in, printed).
In a browser those are Pyodide and Web Bluetooth; in the desktop shell (pywebview) they are this class, which calls the
same `api` functions and the same USB/Bluetooth transports natively. Everything crosses as JSON text or base64 so
any bridge (pywebview, a local socket, a test) can carry it.

No Qt and no pywebview in here, so it is tested without either.
"""
from __future__ import annotations

import base64

from . import api, bluetooth, core
from .render import PrinterError


class Bridge:
    def options(self) -> str:
        """See `api.options`: the allowed choices, geometry, fonts and Bluetooth constants, as JSON text."""
        return api.options()

    def preview(self, spec_json: str) -> str:
        """The label as printed (`api.preview_pixels`, W x H gray bytes), base64-encoded."""
        return base64.b64encode(api.preview_pixels(spec_json)).decode("ascii")

    def print_label(self, spec_json: str, bluetooth_target: str | None = None) -> dict:
        """Print over USB, or over Bluetooth when `bluetooth_target` is an address ("" or "auto" = the first T003 the
        system knows). Returns {"problems": [...], "error": None}, or {"problems": [], "error": "why it failed"}:
        a failure is data for the page to show, never an exception across the bridge."""
        try:
            spec = api.label_from_json(spec_json)
            if bluetooth_target is None:
                problems = core.print_label(spec)
            else:
                problems = core.print_label(spec, bluetooth=bluetooth_target)
        except (PrinterError, OSError, ValueError) as e:  # ValueError: bad JSON, or a QR code too big to encode
            return {"problems": [], "error": str(e)}
        return {"problems": problems, "error": None}

    def known_printers(self) -> list[dict]:
        """T003s the system's Bluetooth knows, for a picker: [{"address": ..., "name": ...}]."""
        return [{"address": address, "name": name} for address, name in bluetooth.known_printers()]
