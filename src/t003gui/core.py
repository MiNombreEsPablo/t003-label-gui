"""Render labels and send them to the ORGBRO T003 thermal printer (TSPL over raw USB).

No Qt in here, so it can be tested and reused from a CLI.

Geometry: 58 mm paper, 384 printable dots wide (203 dpi). The label pitch is 240 dots
(sticker + 2 mm gap) but the sticker itself is only ~224 dots tall, so content stays in SH.
"""
from __future__ import annotations

import functools
import math
import subprocess
import time
from dataclasses import dataclass

import qrcode
import usb.core
import usb.util
from PIL import Image, ImageDraw, ImageFont, ImageOps

VID, PID = 0x0483, 0x5743
EP_OUT, EP_IN = 0x01, 0x82
W, H = 384, 240  # printable dots; H is the label pitch
SH = 224  # sticker height in dots
MARGIN = 8
DEFAULT_FONT = "DejaVu Sans"
FALLBACK_FONT_PATHS = ("/usr/share/fonts/TTF/DejaVuSans-Bold.ttf", "DejaVuSans-Bold.ttf")
ALIGNMENTS = ("left", "center", "right")

STATUS_FLAGS = {0x01: "head open", 0x02: "paper jam", 0x04: "out of paper", 0x08: "out of ribbon", 0x80: "error"}


class PrinterError(Exception):
    pass


@dataclass
class LabelSpec:
    text: str = ""
    qr: str = ""
    image_path: str = ""
    threshold: int | None = None  # images: hard cutoff instead of dithering
    border: bool = False
    copies: int = 1
    density: int = 7
    font: str = DEFAULT_FONT  # family name, resolved through fontconfig
    bold: bool = True
    align: str = "center"  # left | center | right: lines within the block and the block within the text area


@functools.cache
def font_path(family: str, bold: bool) -> str:
    """Font file for a family name via fontconfig (it falls back to a default for unknown names)."""
    try:
        out = subprocess.run(
            ["fc-match", "-f", "%{file}", f"{family}:{'bold' if bold else 'regular'}"],
            capture_output=True, text=True, timeout=5, check=True,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        out = ""
    return out or FALLBACK_FONT_PATHS[0]


def _font(path: str, size: int) -> ImageFont.FreeTypeFont:
    for candidate in (path, *FALLBACK_FONT_PATHS):
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            continue
    raise PrinterError(f"cannot load font {path!r}")


def _ink_box(text: str, font: ImageFont.FreeTypeFont, align: str):
    """Real pixel bounds (l, t, r, b) of the rendered text relative to its draw origin.

    textbbox includes glyph side-bearings, so aligning by it leaves a visible gap; render and measure instead.
    """
    spacing = font.size // 5
    probe = ImageDraw.Draw(Image.new("L", (1, 1)))
    l, t, r, b = (math.ceil(v) for v in probe.multiline_textbbox((0, 0), text, font=font, spacing=spacing, align=align))
    ox, oy = 4 - min(l, 0), 4 - min(t, 0)
    canvas = Image.new("L", (r + ox + 4, b + oy + 4), 0)
    ImageDraw.Draw(canvas).multiline_text((ox, oy), text, font=font, fill=255, spacing=spacing, align=align)
    il, it, ir, ib = canvas.getbbox() or (ox, oy, ox + 1, oy + 1)
    return il - ox, it - oy, ir - ox, ib - oy


def _fit_text(text: str, path: str, align: str, box_w: int, box_h: int):
    """Largest font whose ink fits the box; returns (font, ink_box)."""
    for size in range(120, 8, -2):
        font = _font(path, size)
        ink = _ink_box(text, font, align)
        if ink[2] - ink[0] <= box_w and ink[3] - ink[1] <= box_h:
            return font, ink
    font = _font(path, 8)
    return font, _ink_box(text, font, align)


def _qr_image(data: str, side: int) -> Image.Image:
    qr = qrcode.QRCode(border=0, box_size=1, error_correction=qrcode.constants.ERROR_CORRECT_M)
    qr.add_data(data)
    qr.make(fit=True)
    matrix = qr.get_matrix()
    scale = max(1, side // len(matrix))
    img = Image.new("L", (len(matrix) * scale,) * 2, 255)
    draw = ImageDraw.Draw(img)
    for y, row in enumerate(matrix):
        for x, filled in enumerate(row):
            if filled:
                draw.rectangle([x * scale, y * scale, (x + 1) * scale - 1, (y + 1) * scale - 1], fill=0)
    return img


def render(spec: LabelSpec) -> Image.Image:
    """Grayscale W x H canvas; everything is drawn inside the top SH rows."""
    img = Image.new("L", (W, H), 255)
    draw = ImageDraw.Draw(img)

    if spec.image_path:
        src = ImageOps.contain(Image.open(spec.image_path).convert("L"), (W, SH))
        if spec.threshold is not None:
            src = src.point(lambda v: 255 if v >= spec.threshold else 0)
        img.paste(src, ((W - src.width) // 2, (SH - src.height) // 2))
        return img

    text_w = W - 2 * MARGIN
    if spec.qr:
        qimg = _qr_image(spec.qr, SH - 2 * MARGIN)
        y = (SH - qimg.height) // 2
        if spec.text:
            img.paste(qimg, (W - MARGIN - qimg.width, y))
            text_w = W - 3 * MARGIN - qimg.width
        else:
            img.paste(qimg, ((W - qimg.width) // 2, y))
    if spec.text:
        text = spec.text.replace("\\n", "\n")
        align = spec.align if spec.align in ALIGNMENTS else "center"
        font, (l, t, r, b) = _fit_text(text, font_path(spec.font, spec.bold), align, text_w, SH - 2 * MARGIN)
        slack = text_w - (r - l)
        x = MARGIN - l + {"left": 0, "center": slack // 2, "right": slack}[align]
        y = (SH - (b - t)) // 2 - t
        draw.multiline_text((x, y), text, font=font, fill=0, spacing=font.size // 5, align=align)
    if spec.border:
        draw.rectangle([1, 1, W - 2, SH - 2], outline=0, width=3)
    return img


def to_bitmap(img: Image.Image) -> Image.Image:
    """The exact 1-bit image the printer will burn (also used for the GUI preview)."""
    return img.convert("1", dither=Image.Dither.FLOYDSTEINBERG)


def tspl(spec: LabelSpec) -> bytes:
    data = to_bitmap(render(spec)).tobytes()  # 1 = white, 0 = black, same as TSPL BITMAP mode 0
    head = (
        f"SIZE 72 mm,30 mm\r\nGAP 2 mm,0 mm\r\nDIRECTION 1,0\r\nDENSITY {spec.density}\r\nCLS\r\n"
        f"BITMAP 0,0,{W // 8},{H},0,"
    ).encode()
    return head + data + f"\r\nPRINT {spec.copies},1\r\n".encode()


def send(payload: bytes) -> list[str]:
    """Write a TSPL payload; returns printer problems reported afterwards (empty if fine)."""
    dev = usb.core.find(idVendor=VID, idProduct=PID)
    if dev is None:
        raise PrinterError("T003 not found on USB (is it on and plugged in?)")
    try:
        if dev.is_kernel_driver_active(0):
            dev.detach_kernel_driver(0)
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


def print_label(spec: LabelSpec) -> list[str]:
    return send(tspl(spec))
