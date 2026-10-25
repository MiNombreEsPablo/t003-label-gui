"""Send a label to the ORGBRO T003 thermal printer: over raw USB here, or over Bluetooth (bluetooth.py).

No Qt in here, so it can be tested and reused from a CLI. Rendering lives in render.py and the label
description in spec.py; both are re-exported so `core` stays the one import for callers.
"""
from __future__ import annotations

import ctypes
import time

import usb.core
import usb.util
from PIL import Image

from . import bluetooth as bt
from .protocol import STATUS_FLAGS, STATUS_QUERY, chunks, status_problems, tspl  # noqa: F401
from .render import PrinterError, font_path, list_font_families, render, to_bitmap  # noqa: F401
from .spec import (  # noqa: F401
    ALIGNMENTS,
    BACKGROUNDS,
    BORDER_STYLES,
    DEFAULT_FONT,
    DITHERS,
    EFFECTS,
    H,
    IMAGE_LAYOUTS,
    IMAGE_SUFFIXES,
    MARGIN,
    SH,
    VALIGNMENTS,
    W,
    LabelSpec,
)

VID, PID = 0x0483, 0x5743
EP_OUT, EP_IN = 0x01, 0x82


def _backend():
    """libusb from the libusb-package wheel (the only way Windows/macOS get one); None = pyusb's own search."""
    try:
        import libusb_package
        from usb.backend import libusb1

        return libusb1.get_backend(find_library=libusb_package.find_library)
    except Exception:  # missing wheel or load failure: fall back to a system libusb
        return None


def backend_problem() -> str:
    """Why `_backend()` found nothing, for diagnostics (the self-test and bug reports)."""
    try:
        import libusb_package
    except ImportError as e:
        return f"libusb-package is not installed ({e})"
    try:
        from usb.backend import libusb1

        found = libusb_package.find_library("usb-1.0")
        if libusb1.get_backend(find_library=libusb_package.find_library) is None:
            try:
                ctypes.CDLL(found)
            except OSError as e:  # the dynamic loader's own explanation, e.g. a missing system library
                return f"libusb-package found {found!r} but it will not load: {e}"
            return f"libusb-package found {found!r}, which loads, but pyusb rejected it (pyusb {usb.__version__})"
        return ""
    except Exception as e:
        return f"{type(e).__name__}: {e}"


def send(payload: bytes) -> list[str]:
    """Write a TSPL payload; returns printer problems reported afterwards (empty if fine)."""
    dev = usb.core.find(idVendor=VID, idProduct=PID, backend=_backend())
    if dev is None:
        raise PrinterError("T003 not found on USB (is it on and plugged in?)")
    try:
        try:
            if dev.is_kernel_driver_active(0):
                dev.detach_kernel_driver(0)
        except (NotImplementedError, usb.core.USBError):  # Windows/macOS backends have no kernel-driver calls
            pass
        usb.util.claim_interface(dev, 0)
        for part in chunks(payload, 4096):
            dev.write(EP_OUT, part, timeout=5000)
        time.sleep(0.5)
        dev.write(EP_OUT, STATUS_QUERY, timeout=1000)
        time.sleep(0.3)
        try:
            status = bytes(dev.read(EP_IN, 64, timeout=700))[0]
        except usb.core.USBTimeoutError:
            return []
    except usb.core.USBError as e:
        raise PrinterError(f"USB error: {e}") from e
    finally:
        usb.util.dispose_resources(dev)
    return status_problems(status)


def label_bitmap(spec: LabelSpec, scale: int = 1) -> Image.Image:
    """The exact 1-bit image that prints: just the sticker (no gap rows), optionally enlarged.

    Enlarging is nearest-neighbour so every printed dot stays a crisp square.
    """
    bitmap = to_bitmap(render(spec)).crop((0, 0, W, SH))
    if scale > 1:
        bitmap = bitmap.resize((W * scale, SH * scale), Image.Resampling.NEAREST)
    return bitmap


def export_png(spec: LabelSpec, path, scale: int = 1) -> None:
    """Save the label as a PNG (see `label_bitmap`)."""
    label_bitmap(spec, scale).save(path, format="PNG")


def printer_presence() -> str:
    """Whether the printer is on the USB bus, as a short phrase (never raises); used by About and --selftest."""
    backend = _backend()
    if backend is None:
        return "no libusb backend"
    try:
        return "found" if usb.core.find(idVendor=VID, idProduct=PID, backend=backend) else "not connected"
    except Exception as e:  # e.g. no USB subsystem in a container
        return f"USB unavailable ({type(e).__name__})"


def print_label(spec: LabelSpec, bluetooth: str | None = None) -> list[str]:
    """Print over USB, or over Bluetooth when `bluetooth` is given: the printer's address, or "" / "auto" for the first
    known T003 (see `bluetooth.resolve`). Returns the problems the printer reports afterwards."""
    payload = tspl(spec)
    if bluetooth is None:
        return send(payload)
    return bt.send(payload, bt.resolve(bluetooth))
