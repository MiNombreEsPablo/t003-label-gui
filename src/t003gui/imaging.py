"""Turn a picture file into the grayscale (or already 1-bit) image that gets pasted on the label. Qt-free.

Order: load (transparency over white, EXIF rotation) -> fit -> tone (gamma, brightness, contrast) -> dither.
The default dither, Floyd-Steinberg, is left to `to_bitmap` (which dithers the whole label); the other modes produce
pure black/white here, which `to_bitmap` then passes through untouched.
"""
from __future__ import annotations

import functools

from PIL import Image, ImageChops, ImageEnhance, ImageOps

from .spec import SH, W, LabelSpec


def load_gray(path: str) -> Image.Image:
    """Open an image as 8-bit gray: upright per its EXIF orientation, transparent areas white (not black)."""
    img = ImageOps.exif_transpose(Image.open(path))
    if img.mode in ("RGBA", "LA", "PA") or (img.mode == "P" and "transparency" in img.info):
        rgba = img.convert("RGBA")
        flat = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
        img = Image.alpha_composite(flat, rgba)
    return img.convert("L")


def tone(img: Image.Image, gamma: float = 1.0, brightness: int = 0, contrast: int = 0) -> Image.Image:
    """gamma > 1 lightens the mid-tones; brightness and contrast are -100..100 (0 = unchanged)."""
    if gamma != 1.0:
        inverse = 1.0 / max(gamma, 0.01)
        img = img.point([round(255 * (v / 255) ** inverse) for v in range(256)])
    if brightness:
        img = ImageEnhance.Brightness(img).enhance(max(0.0, 1 + brightness / 100))
    if contrast:
        img = ImageEnhance.Contrast(img).enhance(max(0.0, 1 + contrast / 100))
    return img


def _bayer_matrix(n: int) -> list[list[int]]:
    m = [[0]]
    while len(m) < n:
        size = len(m)
        big = [[0] * (2 * size) for _ in range(2 * size)]
        for y in range(size):
            for x in range(size):
                v = 4 * m[y][x]
                big[y][x], big[y][x + size], big[y + size][x], big[y + size][x + size] = v, v + 2, v + 3, v + 1
        m = big
    return m


@functools.lru_cache(maxsize=8)
def _threshold_map(n: int, width: int, height: int) -> Image.Image:
    """An n x n Bayer matrix tiled over a width x height image, as per-pixel thresholds 0..254."""
    m = _bayer_matrix(n)
    cells = n * n
    levels = [[min(254, int((v + 0.5) * 255 / cells)) for v in row] for row in m]
    img = Image.new("L", (width, height))
    img.putdata([levels[y % n][x % n] for y in range(height) for x in range(width)])
    return img


def ordered_dither(img: Image.Image, n: int) -> Image.Image:
    """Ordered (Bayer) dithering: the regular crosshatch pattern of 90s handheld cameras and early games."""
    above = ImageChops.subtract(img, _threshold_map(n, *img.size))  # > 0 where the pixel beats its threshold
    return above.point(lambda v: 255 if v > 0 else 0)


def _dither(img: Image.Image, spec: LabelSpec, *, final: bool) -> Image.Image:
    """Gray to dots per the spec. Floyd-Steinberg is left to `to_bitmap` unless the picture will be enlarged first."""
    if spec.threshold is not None:
        return img.point(lambda v: 255 if v >= spec.threshold else 0)
    if spec.dither == "bayer4":
        return ordered_dither(img, 4)
    if spec.dither == "bayer8":
        return ordered_dither(img, 8)
    return img if final else img.convert("1", dither=Image.Dither.FLOYDSTEINBERG).convert("L")


def process(spec: LabelSpec, box: tuple[int, int] = (W, SH), cover: bool = False) -> Image.Image:
    """The picture for `spec`, fitted inside `box` (default: the whole sticker); `cover` fills the box and crops.

    With `pixelate` the tone and dither happen at the low resolution and the dots are then enlarged, so the pattern
    itself turns chunky (the look of 90s handheld cameras) instead of staying one dot wide inside each block.
    """
    gray = load_gray(spec.image_path)
    img = ImageOps.fit(gray, box) if cover else ImageOps.contain(gray, box)
    if spec.mirror:
        img = ImageOps.mirror(img)
    if spec.flip:
        img = ImageOps.flip(img)
    block = max(1, spec.pixelate)
    size = img.size
    if block > 1:
        img = img.resize((-(-size[0] // block), -(-size[1] // block)), Image.Resampling.BOX)
    img = tone(img, spec.gamma, spec.brightness, spec.contrast)
    if spec.invert:
        img = ImageOps.invert(img)
    img = _dither(img, spec, final=block == 1)
    if block > 1:
        img = img.resize((img.width * block, img.height * block), Image.Resampling.NEAREST).crop((0, 0, *size))
    return img
