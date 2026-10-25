"""The desktop shell's side of the web UI: the engine and the printer, as methods the page calls from JavaScript.

The web UI is written once and talks to two seams: an engine (label in, pixels out) and a printer (label in, printed).
In a browser those are Pyodide and Web Bluetooth; in the desktop shell (pywebview) they are this class, which calls the
same `api` functions and the same USB/Bluetooth transports natively. Everything crosses as JSON text or base64 so
any bridge (pywebview, a local socket, a test) can carry it.

No Qt and no pywebview in here, so it is tested without either.
"""
from __future__ import annotations

import base64
import binascii
import os
import tempfile

from . import api, bluetooth, composition, core
from .render import PrinterError
from .settings import Settings


class Bridge:
    def __init__(self, settings: Settings | None = None, dialogs=None) -> None:
        """`dialogs` is the shell's native file dialogs (the shell has them, this module doesn't know the toolkit):
        an object with save(suggested_name, kind) -> path or None, where `kind` words the file type ("PNG image")."""
        self._settings = settings or Settings()
        self._dialogs = dialogs

    def options(self) -> str:
        """See `api.options`: the allowed choices, geometry, fonts and Bluetooth constants, as JSON text."""
        return api.options()

    def preview(self, spec_json: str) -> dict:
        """The label as printed (`api.preview_pixels`, W x H gray bytes, base64-encoded) with the hints worth showing
        (`api.hints`): {"pixels": "...", "hints": [...]}."""
        pixels = base64.b64encode(api.preview_pixels(spec_json)).decode("ascii")
        return {"pixels": pixels, "hints": api.hints(spec_json)}

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

    def upload_image(self, data_base64: str, name: str = "") -> dict:
        """A picture chosen, pasted or dropped on the page: {"path": ..., "error": None} with the path to put in the
        label (`api.adopt_image`), or {"path": None, "error": "a sentence for the user"}."""
        fd, scratch = tempfile.mkstemp(prefix="t003-upload-")
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(base64.b64decode(data_base64, validate=True))
            return {"path": api.adopt_image(scratch, name), "error": None}
        except (ValueError, binascii.Error, OSError) as e:  # ValueError: not a picture, too big
            return {"path": None, "error": str(e)}
        finally:
            os.unlink(scratch)

    def export_png(self, spec_json: str, scale: int = 1) -> dict:
        """The label as a PNG (`api.export_png`), base64-encoded, with a name for it: {"data", "name", "error"}."""
        try:
            return {"data": base64.b64encode(api.export_png(spec_json, scale)).decode("ascii"),
                    "name": api.file_stem(spec_json) + ".png", "error": None}
        except (PrinterError, OSError, ValueError) as e:  # a missing picture, a QR code too big to encode
            return {"data": None, "name": None, "error": str(e)}

    def save_file(self, data_base64: str, name: str, kind: str = "File") -> dict:
        """Ask where to put a file the page made, and write it: {"saved": file name, "cancelled": bool, "error"}.
        The file type is the suffix of `name`; `kind` words it for the dialog ("PNG image", "T003 label")."""
        if self._dialogs is None:
            return {"saved": None, "cancelled": False, "error": "This window can't save files."}
        try:
            path = self._dialogs.save(name, kind)
            if not path:
                return {"saved": None, "cancelled": True, "error": None}
            with open(path, "wb") as f:
                f.write(base64.b64decode(data_base64, validate=True))
            return {"saved": os.path.basename(path), "cancelled": False, "error": None}
        except (OSError, ValueError, binascii.Error) as e:
            return {"saved": None, "cancelled": False, "error": str(e)}

    def composition_dumps(self, spec_json: str) -> dict:
        """The label as the text of a `.t003label` file, base64: {"data", "name", "error"}."""
        try:
            text = api.composition_dumps(spec_json)
            return {"data": base64.b64encode(text.encode("utf-8")).decode("ascii"),
                    "name": api.file_stem(spec_json) + composition.SUFFIX, "error": None}
        except (OSError, ValueError) as e:
            return {"data": None, "name": None, "error": str(e)}

    def composition_loads(self, text: str) -> dict:
        """What a `.t003label` file holds: {"spec": JSON text, "error": None}, or {"spec": None, "error": "why"}."""
        try:
            return {"spec": api.composition_loads(text), "error": None}
        except (OSError, ValueError) as e:
            return {"spec": None, "error": str(e)}

    def known_printers(self) -> list[dict]:
        """T003s the system's Bluetooth knows, for a picker: [{"address": ..., "name": ...}]."""
        return [{"address": address, "name": name} for address, name in bluetooth.known_printers()]

    def get_setting(self, key: str, default=None):
        return self._settings.get(key, default)

    def set_setting(self, key: str, value) -> dict:
        """Remember a value; failing to write is data for the page ({"error": ...}), not an exception."""
        try:
            self._settings.set(key, value)
        except OSError as e:
            return {"error": str(e)}
        return {"error": None}
