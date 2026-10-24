"""Freehand doodles: a 1-bit ink mask the size of the sticker, stored in `LabelSpec.doodle` as base64 PNG text. Qt-free.

A string rather than a file, so a doodle travels with presets and `.t003label` files and needs no extra plumbing. White
pixels in the mask are ink (printed black), black ones are untouched label.
"""
from __future__ import annotations

import base64
import binascii
import io
from functools import lru_cache

from PIL import Image, UnidentifiedImageError

from .spec import SH, W

SIZE = (W, SH)


def encode(mask: Image.Image) -> str:
    """Base64 PNG of `mask` (any mode, size W x SH; non-zero is ink), or "" when nothing is drawn."""
    if mask.size != SIZE:
        raise ValueError(f"a doodle is {W}x{SH} dots, not {mask.width}x{mask.height}")
    bits = mask.convert("L").point([0] * 128 + [255] * 128).convert("1")
    if not bits.getbbox():
        return ""
    out = io.BytesIO()
    bits.save(out, "PNG", optimize=True)
    return base64.b64encode(out.getvalue()).decode("ascii")


@lru_cache(maxsize=8)  # the preview renders on every slider step; the mask is shared, so never modify it
def decode(data: str) -> Image.Image | None:
    """The ink mask (mode "L", 0 or 255), or None for an empty or damaged doodle: stored files may be hand-edited."""
    if not data:
        return None
    try:
        img = Image.open(io.BytesIO(base64.b64decode(data, validate=True)))
        if img.size != SIZE:  # checked from the header, before any pixels are decoded
            return None
        return img.convert("L").point([0] * 128 + [255] * 128)
    except (binascii.Error, ValueError, OSError, UnidentifiedImageError, Image.DecompressionBombError):
        return None
