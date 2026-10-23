"""Rasterise src/t003gui/assets/icon.svg into the PNG/ICO/ICNS files the packages need.

    .venv/bin/python packaging/make_icons.py

Needs PySide6 (QtSvg). Outputs are committed, so this only runs when the SVG changes.
"""
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PIL import Image
from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication, QImage, QPainter
from PySide6.QtSvg import QSvgRenderer

ROOT = Path(__file__).resolve().parent.parent
SVG = ROOT / "src/t003gui/assets/icon.svg"
OUT = ROOT / "packaging/icons"
SIZES = (16, 24, 32, 48, 64, 128, 256, 512)


def render(size: int) -> Image.Image:
    image = QImage(size, size, QImage.Format_ARGB32)
    image.fill(Qt.transparent)
    painter = QPainter(image)
    painter.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
    QSvgRenderer(str(SVG)).render(painter)
    painter.end()
    return Image.frombuffer("RGBA", (size, size), bytes(image.constBits()), "raw", "BGRA", 0, 1)


def arrows() -> None:
    """Small navy chevrons for combo/spin-box buttons in the Y2K theme (anti-aliased via 4x supersampling)."""
    for name, points in (("arrow-down", [(0, 0), (12, 0), (6, 7)]), ("arrow-up", [(0, 7), (12, 7), (6, 0)])):
        big = Image.new("RGBA", (48, 32), (0, 0, 0, 0))
        from PIL import ImageDraw

        ImageDraw.Draw(big).polygon([(x * 4, y * 4 + 2) for x, y in points], fill=(11, 42, 99, 255))
        big.resize((12, 8), Image.LANCZOS).save(ROOT / f"src/t003gui/assets/{name}.png")


def main() -> None:
    QGuiApplication(sys.argv)
    OUT.mkdir(parents=True, exist_ok=True)
    images = {size: render(size) for size in SIZES}
    for size, img in images.items():
        img.save(OUT / f"t003-label-gui-{size}.png")
    images[256].save(ROOT / "src/t003gui/assets/icon-256.png")  # used at runtime (no SVG plugin needed)
    images[256].save(OUT / "t003-label-gui.ico", sizes=[(s, s) for s in (16, 24, 32, 48, 64, 128, 256)])
    images[512].save(OUT / "t003-label-gui.icns")
    arrows()
    print("wrote", len(SIZES), "PNGs, .ico, .icns, arrows")


if __name__ == "__main__":
    main()
