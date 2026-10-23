"""Build the TSPL payload and send it to the ORGBRO T003 thermal printer over raw USB.

No Qt in here, so it can be tested and reused from a CLI. Rendering lives in render.py and the label
description in spec.py; both are re-exported so `core` stays the one import for callers.
"""
from __future__ import annotations

import ctypes
import time

import usb.core
import usb.util
from PIL import Image

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
STATUS_FLAGS = {0x01: "head open", 0x02: "paper jam", 0x04: "out of paper", 0x08: "out of ribbon", 0x80: "error"}


def tspl(spec: LabelSpec) -> bytes:
    data = to_bitmap(render(spec)).tobytes()  # 1 = white, 0 = black, same as TSPL BITMAP mode 0
    head = (
        f"SIZE 72 mm,30 mm\r\nGAP 2 mm,0 mm\r\nDIRECTION 1,0\r\nDENSITY {spec.density}\r\nCLS\r\n"
        f"BITMAP 0,0,{W // 8},{H},0,"
    ).encode()
    return head + data + f"\r\nPRINT {spec.copies},1\r\n".encode()


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
        for i in range(0, len(payload), 4096):
            dev.write(EP_OUT, payload[i : i + 4096], timeout=5000)
        time.sleep(0.5)
        dev.write(EP_OUT, b"\x1b!?", timeout=1000)
        time.sleep(0.3)
        try:
            status = bytes(dev.read(EP_IN, 64, timeout=700))[0]
        except usb.core.USBTimeoutError:
            return []
    except usb.core.USBError as e:
        raise PrinterError(f"USB error: {e}") from e
    finally:
        usb.util.dispose_resources(dev)
    return [msg for bit, msg in STATUS_FLAGS.items() if status & bit]


def export_png(spec: LabelSpec, path, scale: int = 1) -> None:
    """Save the label as the exact 1-bit image that prints: just the sticker (no gap rows), optionally enlarged.

    Enlarging is nearest-neighbour so every printed dot stays a crisp square.
    """
    bitmap = to_bitmap(render(spec)).crop((0, 0, W, SH))
    if scale > 1:
        bitmap = bitmap.resize((W * scale, SH * scale), Image.Resampling.NEAREST)
    bitmap.save(path, format="PNG")


def printer_presence() -> str:
    """Whether the printer is on the USB bus, as a short phrase (never raises); used by About and --selftest."""
    backend = _backend()
    if backend is None:
        return "no libusb backend"
    try:
        return "found" if usb.core.find(idVendor=VID, idProduct=PID, backend=backend) else "not connected"
    except Exception as e:  # e.g. no USB subsystem in a container
        return f"USB unavailable ({type(e).__name__})"


def print_label(spec: LabelSpec) -> list[str]:
    return send(tspl(spec))
