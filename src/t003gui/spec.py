"""Label description and the geometry constants shared by rendering and printing.

Geometry: 58 mm paper, 384 printable dots wide (203 dpi). The label pitch is 240 dots
(sticker + 2 mm gap) but the sticker itself is only ~224 dots tall, so content stays in SH.
"""
from __future__ import annotations

from dataclasses import dataclass

W, H = 384, 240  # printable dots; H is the label pitch
SH = 224  # sticker height in dots
MARGIN = 8

DEFAULT_FONT = "DejaVu Sans"
ALIGNMENTS = ("left", "center", "right")
VALIGNMENTS = ("top", "middle", "bottom")
EFFECTS = ("none", "shadow", "outline", "3d")
BACKGROUNDS = ("none", "checker", "dots", "stripes", "gradient", "stars", "grid")
BORDER_STYLES = ("solid", "double", "dotted", "checker", "bevel", "marquee")


@dataclass
class LabelSpec:
    text: str = ""
    qr: str = ""
    image_path: str = ""
    threshold: int | None = None  # images: hard cutoff instead of dithering
    copies: int = 1
    density: int = 7
    # text
    font: str = DEFAULT_FONT  # family name, resolved through fontconfig
    bold: bool = True
    italic: bool = False  # synthetic slant when the font has no italic face
    size: int = 0  # 0 = largest that fits, otherwise a cap in dots
    align: str = "center"  # lines within the block and the block within the text area
    valign: str = "middle"
    effect: str = "none"
    # decoration
    border: bool = False
    border_style: str = "solid"
    background: str = "none"
    bars: bool = False  # hazard-stripe "under construction" bars top and bottom
