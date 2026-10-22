"""Render labels and send them to the ORGBRO T003 thermal printer (TSPL over raw USB).

No Qt in here, so it can be tested and reused from a CLI.

Geometry: 58 mm paper, 384 printable dots wide (203 dpi). The label pitch is 240 dots
(sticker + 2 mm gap) but the sticker itself is only ~224 dots tall, so content stays in SH.
"""
from __future__ import annotations

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
FONT_PATHS = ("/usr/share/fonts/TTF/DejaVuSans-Bold.ttf", "DejaVuSans-Bold.ttf")

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


def _font(size: int) -> ImageFont.FreeTypeFont:
    for path in FONT_PATHS:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    raise PrinterError("DejaVu Sans Bold font not found")


def _fit_text(draw: ImageDraw.ImageDraw, text: str, box_w: int, box_h: int):
    for size in range(120, 8, -2):
        font = _font(size)
        bbox = draw.multiline_textbbox((0, 0), text, font=font, spacing=size // 5, align="center")
        if bbox[2] - bbox[0] <= box_w and bbox[3] - bbox[1] <= box_h:
            return font, bbox
    font = _font(8)
    return font, draw.multiline_textbbox((0, 0), text, font=font, align="center")


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
        font, (l, t, r, b) = _fit_text(draw, text, text_w, SH - 2 * MARGIN)
        x = MARGIN + (text_w - (r - l)) // 2 - l
        y = (SH - (b - t)) // 2 - t
        draw.multiline_text((x, y), text, font=font, fill=0, spacing=font.size // 5, align="center")
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
