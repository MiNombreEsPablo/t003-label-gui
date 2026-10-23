"""Draw a LabelSpec onto a 384x240 grayscale canvas. Everything stays inside the top SH rows."""
from __future__ import annotations

import functools
import math
import random
import subprocess

import qrcode
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageOps

from .spec import ALIGNMENTS, BACKGROUNDS, BORDER_STYLES, EFFECTS, H, MARGIN, SH, VALIGNMENTS, W, LabelSpec

FALLBACK_FONT_PATHS = ("/usr/share/fonts/TTF/DejaVuSans-Bold.ttf", "DejaVuSans-Bold.ttf")
ITALIC_SHEAR = 0.25
BAR_H = 14
MAX_FONT_SIZE = 120
# Space a border takes from the edge of the frame; text keeps this much distance plus a gap.
BORDER_INSET = {
    "solid": 3, "double": 9, "dotted": 6, "checker": 8, "bevel": 9, "marquee": 15,
    "chamfer": 10, "brackets": 7, "ticks": 9,
}


class PrinterError(Exception):
    pass


# --- fonts -------------------------------------------------------------------------------------------------------


@functools.cache
def font_path(family: str, bold: bool, italic: bool = False) -> tuple[str, bool]:
    """(file, has_native_slant) for a family via fontconfig, which falls back for unknown names."""
    style = ("bold" if bold else "regular") + (":italic" if italic else "")
    try:
        out = subprocess.run(
            ["fc-match", "-f", "%{file}|%{slant}", f"{family}:{style}"],
            capture_output=True, text=True, timeout=5, check=True,
        ).stdout.strip()
        path, _, slant = out.partition("|")
        return (path, slant.isdigit() and int(slant) > 0) if path else (FALLBACK_FONT_PATHS[0], False)
    except (OSError, subprocess.SubprocessError):
        return FALLBACK_FONT_PATHS[0], False


def _font(path: str, size: int) -> ImageFont.FreeTypeFont:
    for candidate in (path, *FALLBACK_FONT_PATHS):
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            continue
    raise PrinterError(f"cannot load font {path!r}")


# --- text --------------------------------------------------------------------------------------------------------


def _checker(w: int, h: int) -> Image.Image:
    even = bytes([255, 0] * (w // 2 + 1))[:w]
    odd = bytes([0, 255] * (w // 2 + 1))[:w]
    return Image.frombytes("L", (w, h), b"".join(even if y % 2 == 0 else odd for y in range(h)))


def _dots(w: int, h: int) -> Image.Image:
    """25% coverage: every other pixel on every other row (a light dither, used for glow)."""
    even = bytes([255, 0] * (w // 2 + 1))[:w]
    blank = bytes(w)
    return Image.frombytes("L", (w, h), b"".join(even if y % 2 == 0 else blank for y in range(h)))


def _layout(probe: ImageDraw.ImageDraw, text: str, font, align: str, spacing: int):
    """Place each line ourselves: [(line, x, y)] and the block's (l, t, r, b).

    Pillow's multiline_text widens the line pitch by 2*stroke_width, so a stroked pass (outline, glow, halo)
    drifts further from the unstroked pass on every line. A fixed pitch keeps all passes registered.
    """
    lines = text.split("\n")
    pitch = probe.textbbox((0, 0), "A", font=font)[3] + spacing
    widths = [probe.textlength(line, font=font) for line in lines]
    block = max(widths)
    placed = [
        (line, {"left": 0, "center": (block - lw) / 2, "right": block - lw}[align], i * pitch)
        for i, (line, lw) in enumerate(zip(lines, widths))
    ]
    boxes = [probe.textbbox((x, y), line, font=font) for line, x, y in placed if line.strip()]
    if not boxes:
        return placed, (0, 0, 1, 1)
    return placed, tuple(math.ceil(v) for v in (
        min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes)))


def _text_layer(text, font, align, effect, halo, shear):
    """Render text with its effect. Returns (value, alpha) cropped to the painted area:
    paste `value` through `alpha` to draw it (value holds the black/white pixels, alpha where they apply)."""
    spacing = font.size // 5
    probe = ImageDraw.Draw(Image.new("L", (1, 1)))
    lines, (l, t, r, b) = _layout(probe, text, font, align, spacing)
    pad = 12
    ox, oy = pad - min(l, 0), pad - min(t, 0)
    w, h = r + ox + pad, b + oy + pad
    value, alpha = Image.new("L", (w, h), 255), Image.new("L", (w, h), 0)
    draws = (ImageDraw.Draw(value), ImageDraw.Draw(alpha))

    def draw_lines(draw, off, fill, stroke):
        for line, x, y in lines:
            draw.text(
                (ox + off[0] + x, oy + off[1] + y), line, font=font, fill=fill,
                stroke_width=stroke, stroke_fill=fill,
            )

    def put(off, fill, stroke=0):
        for draw, f in zip(draws, (fill, 255)):
            draw_lines(draw, off, f, stroke)

    def glyph(off=(0, 0), stroke=0):
        """Mask of the plain (optionally thickened) text."""
        m = Image.new("L", (w, h), 0)
        draw_lines(ImageDraw.Draw(m), off, 255, stroke)
        return m

    def paint(mask, fill):
        value.paste(fill, mask=mask)
        alpha.paste(255, mask=mask)

    if effect == "outline":
        put((0, 0), 0, 3)
        put((0, 0), 255)
    elif effect == "3d":
        for i in range(6, 0, -1):
            put((i, i), 0, 1)
        put((0, 0), 0, 2)
        put((0, 0), 255)
    elif effect == "shadow":
        if halo:
            put((4, 4), 255, 2)
            put((0, 0), 255, 2)
        shadow = glyph((4, 4))
        value.paste(255, mask=shadow)  # opaque white under the dither so the background doesn't show through
        value.paste(0, mask=ImageChops.multiply(shadow, _checker(w, h)))
        alpha.paste(255, mask=shadow)
        put((0, 0), 0)
    elif effect == "glitch":
        unit = max(0.15, font.size / 60)  # displacements scale with the text so small labels stay legible
        base = glyph()
        sliced = base.copy()
        pitch = probe.textbbox((0, 0), "A", font=font)[3] + spacing
        for i, (_, _, ly) in enumerate(lines):  # displaced horizontal slices on every line, like a bad VHS frame
            for frac, dx in ((0.22, 8), (0.58, -10)):
                y0 = min(h - 1, oy + ly + int(frac * pitch))
                y1 = min(h, y0 + max(2, font.size // 10))
                shift = round((dx if i % 2 == 0 else -dx) * unit)
                band = base.crop((0, y0, w, y1))
                sliced.paste(0, (0, y0, w, y1))
                sliced.paste(band, (shift, y0))
        # the fringe copy and scanline gaps only read at larger sizes; small text keeps just the slice shifts
        ghost = Image.new("L", (w, h), 0)
        if font.size >= 24:
            ghost = ImageChops.multiply(glyph((-max(1, round(6 * unit)), 0)), _checker(w, h))  # dithered fringe copy
        union = ImageChops.lighter(ImageChops.lighter(sliced, ghost), base)
        if halo:
            paint(union.filter(ImageFilter.MaxFilter(7)), 255)
        paint(union, 255)
        value.paste(0, mask=ghost)
        value.paste(0, mask=sliced)
        if font.size >= 30:
            for y in range(oy, h, max(5, round(6 * unit))):  # thin white scanline gaps through the text
                value.paste(255, (0, y, w, y + 1), mask=sliced.crop((0, y, w, y + 1)))
    elif effect == "neon":
        glow = glyph(stroke=7)
        paint(glow, 255)
        value.paste(0, mask=ImageChops.multiply(glow, _dots(w, h)))  # dithered halo
        put((0, 0), 0, 3)
        put((0, 0), 255, 1)  # white tube gap between the outer line and the core
        put((0, 0), 0)
    elif effect == "scanlines":
        if halo:
            put((0, 0), 255, 3)
        put((0, 0), 0)
        period = max(4, font.size // 9)
        gaps = Image.new("L", (w, h), 0)
        gd = ImageDraw.Draw(gaps)
        for y in range(oy, h, period):
            gd.rectangle([0, y, w, y + max(1, period // 3) - 1], fill=255)
        value.paste(255, mask=ImageChops.multiply(gaps, glyph()))
    else:
        if halo:
            put((0, 0), 255, 3)
        put((0, 0), 0)

    if shear:
        w2 = w + math.ceil(shear * h)
        coeffs = (1, shear, -shear * h, 0, 1, 0)
        value = value.transform((w2, h), Image.AFFINE, coeffs, fillcolor=255)
        alpha = alpha.transform((w2, h), Image.AFFINE, coeffs, fillcolor=0)
    box = alpha.getbbox() or (0, 0, 1, 1)
    return value.crop(box), alpha.crop(box)


def _fit_text_layer(text, path, shear, align, effect, halo, box_w, box_h, max_size):
    """Largest font size (binary search) whose rendered layer fits the box."""
    sizes = list(range(8, max_size + 1, 2)) or [8]
    if sizes[-1] != max_size and max_size > 8:
        sizes.append(max_size)

    def build(size):
        return _text_layer(text, _font(path, size), align, effect, halo, shear)

    best, lo, hi = None, 0, len(sizes) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        layer = build(sizes[mid])
        if layer[0].width <= box_w and layer[0].height <= box_h:
            best, lo = layer, mid + 1
        else:
            hi = mid - 1
    return best or build(sizes[0])


# --- decoration --------------------------------------------------------------------------------------------------

_BAYER = ((0, 8, 2, 10), (12, 4, 14, 6), (3, 11, 1, 9), (15, 7, 13, 5))


@functools.cache
def _background(name: str) -> Image.Image:  # cached: some are slow and all are deterministic
    img = Image.new("L", (W, SH), 255)
    d = ImageDraw.Draw(img)
    if name == "checker":
        for y in range(0, SH, 8):
            for x in range(0, W, 8):
                if (x // 8 + y // 8) % 2 == 0:
                    d.rectangle([x, y, x + 7, y + 7], fill=0)
    elif name == "dots":
        for row, y in enumerate(range(3, SH, 8)):
            for x in range(3 + 4 * (row % 2), W, 8):
                d.rectangle([x, y, x + 1, y + 1], fill=0)
    elif name == "stripes":
        for k in range(-SH, W, 12):
            d.line([(k, SH), (k + SH, 0)], fill=0, width=3)
    elif name == "gradient":
        px = img.load()
        for y in range(SH):
            level = y / (SH - 1)  # white at the top fading to black at the bottom
            for x in range(W):
                if level > (_BAYER[y % 4][x % 4] + 0.5) / 16:
                    px[x, y] = 0
    elif name == "stars":
        for row, y in enumerate(range(10, SH, 28)):
            for x in range(10 + 14 * (row % 2), W, 28):
                d.line([(x - 4, y), (x + 4, y)], fill=0, width=1)
                d.line([(x, y - 4), (x, y + 4)], fill=0, width=1)
                d.line([(x - 3, y - 3), (x + 3, y + 3)], fill=0, width=1)
                d.line([(x - 3, y + 3), (x + 3, y - 3)], fill=0, width=1)
    elif name == "grid":
        for x in range(0, W, 16):
            d.line([(x, 0), (x, SH)], fill=0, width=1)
        for y in range(0, SH, 16):
            d.line([(0, y), (W, y)], fill=0, width=1)
    elif name == "scanlines":
        for y in range(0, SH, 4):
            d.line([(0, y), (W, y)], fill=0, width=1)
    elif name == "circuit":
        _circuit(d)
    elif name == "hexgrid":
        r = 12
        for col in range(-1, int(W / (1.5 * r)) + 2):
            for row in range(-1, int(SH / (math.sqrt(3) * r)) + 2):
                cx = col * 1.5 * r
                cy = row * math.sqrt(3) * r + (math.sqrt(3) / 2 * r if col % 2 else 0)
                pts = [(cx + r * math.cos(math.radians(a)), cy + r * math.sin(math.radians(a))) for a in range(0, 360, 60)]
                d.line(pts + [pts[0]], fill=0, width=1)
    elif name == "synthwave":
        _synthwave(img)
    elif name == "matrix":
        _matrix(d)
    elif name == "halftone":
        for row, y in enumerate(range(4, SH, 8)):
            radius = 0.5 + 3.4 * y / SH  # dots swell towards the bottom
            for x in range(4 + 4 * (row % 2), W, 8):
                d.ellipse([x - radius, y - radius, x + radius, y + radius], fill=0)
    return img


def _circuit(d: ImageDraw.ImageDraw) -> None:
    """PCB traces: random walks along 45-degree directions ending in via rings (seeded, so stable)."""
    rng = random.Random(7)
    dirs = ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1), (1, -1), (-1, 1))
    for _ in range(26):
        x, y = rng.randrange(0, W, 8), rng.randrange(0, SH, 8)
        d.ellipse([x - 3, y - 3, x + 3, y + 3], outline=0, width=2)
        for _ in range(rng.randint(2, 4)):
            dx, dy = rng.choice(dirs)
            n = rng.randrange(2, 6) * 8
            nx, ny = x + dx * n, y + dy * n
            d.line([(x, y), (nx, ny)], fill=0, width=2)
            x, y = nx, ny
        d.ellipse([x - 3, y - 3, x + 3, y + 3], outline=0, fill=255, width=2)


def _synthwave(img: Image.Image) -> None:
    """Striped dithered sun on the horizon over a perspective grid."""
    d = ImageDraw.Draw(img)
    horizon, cx, radius = int(SH * 0.55), W // 2, 62
    px = img.load()
    for y in range(horizon - radius, horizon):
        level = 0.3 + 0.55 * (y - (horizon - radius)) / radius  # denser towards the horizon
        half = math.sqrt(max(0, radius**2 - (y - horizon) ** 2))
        for x in range(int(cx - half), int(cx + half) + 1):
            if 0 <= x < W and level > (_BAYER[y % 4][x % 4] + 0.5) / 16:
                px[x, y] = 0
    for offset, thickness in ((6, 4), (16, 3), (27, 2), (40, 2), (55, 1)):  # slats get thicker near the horizon
        d.rectangle([0, horizon - offset, W, horizon - offset + thickness - 1], fill=255)
    d.rectangle([0, horizon, W, SH], fill=255)
    d.line([(0, horizon), (W, horizon)], fill=0, width=2)
    for i in range(-14, 15):
        d.line([(cx, horizon), (cx + i * 44, SH)], fill=0, width=1)
    for k in range(1, 8):
        y = horizon + int((k / 7) ** 2 * (SH - horizon))
        d.line([(0, y), (W, y)], fill=0, width=1)


def _matrix(d: ImageDraw.ImageDraw) -> None:
    """Falling columns of 0/1, dense at the head and thinning to a tail (seeded)."""
    rng = random.Random(11)
    font = _font(font_path("DejaVu Sans Mono", False)[0], 10)
    for x in range(2, W, 11):
        length, start = rng.randrange(4, 20), rng.randrange(-8, 14)
        for i in range(length):
            if rng.random() < (i + 1) / length:
                d.text((x, (start + i) * 11), rng.choice("01"), font=font, fill=0)


def sorted_box(xa: int, ya: int, xb: int, yb: int) -> list[int]:
    return [min(xa, xb), min(ya, yb), max(xa, xb), max(ya, yb)]


def _border(d: ImageDraw.ImageDraw, style: str, x0: int, y0: int, x1: int, y1: int) -> None:
    if style == "double":
        d.rectangle([x0, y0, x1, y1], outline=0, width=2)
        d.rectangle([x0 + 5, y0 + 5, x1 - 5, y1 - 5], outline=0, width=2)
    elif style == "dotted":
        for x in range(x0 + 1, x1 - 2, 8):
            d.rectangle([x, y0 + 1, x + 3, y0 + 4], fill=0)
            d.rectangle([x, y1 - 4, x + 3, y1 - 1], fill=0)
        for y in range(y0 + 1, y1 - 2, 8):
            d.rectangle([x0 + 1, y, x0 + 4, y + 3], fill=0)
            d.rectangle([x1 - 4, y, x1 - 1, y + 3], fill=0)
    elif style == "checker":
        cell = 6
        for i, x in enumerate(range(x0, x1 + 1, cell)):
            if i % 2 == 0:
                for y in (y0, y1 - cell + 1):
                    d.rectangle([x, y, min(x + cell - 1, x1), y + cell - 1], fill=0)
        for i, y in enumerate(range(y0, y1 + 1, cell)):
            if i % 2 == 0:
                for x in (x0, x1 - cell + 1):
                    d.rectangle([x, y, x + cell - 1, min(y + cell - 1, y1)], fill=0)
    elif style == "bevel":
        d.rectangle([x0, y0, x1, y1], outline=0, width=1)
        d.rectangle([x0 + 1, y1 - 3, x1 - 1, y1 - 1], fill=0)  # dark bottom and right edges read as a raised panel
        d.rectangle([x1 - 3, y0 + 1, x1 - 1, y1 - 1], fill=0)
        d.rectangle([x0 + 4, y0 + 4, x1 - 6, y1 - 6], outline=0, width=1)
    elif style == "marquee":
        r = 4
        bulbs = [(x, y0 + 7) for x in range(x0 + 7, x1 - 6, 14)]
        bulbs += [(x1 - 7, y) for y in range(y0 + 7 + 14, y1 - 6, 14)]
        bulbs += [(x, y1 - 7) for x in range(x1 - 7, x0 + 6, -14)]
        bulbs += [(x0 + 7, y) for y in range(y1 - 7 - 14, y0 + 7, -14)]
        for i, (cx, cy) in enumerate(bulbs):
            d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=0, fill=0 if i % 2 == 0 else 255, width=1)
    elif style == "chamfer":
        c = 10  # cut corners plus little tabs, like a game-UI panel
        # the 3-wide line is centred on its path, so keep the path 1 dot inside the frame
        ax0, ay0, ax1, ay1 = x0 + 1, y0 + 1, x1 - 1, y1 - 1
        pts = [(ax0 + c, ay0), (ax1 - c, ay0), (ax1, ay0 + c), (ax1, ay1 - c), (ax1 - c, ay1), (ax0 + c, ay1), (ax0, ay1 - c), (ax0, ay0 + c)]
        d.line(pts + [pts[0]], fill=0, width=3, joint="curve")
        d.rectangle([x0 + c + 10, y0, x0 + c + 44, y0 + 6], fill=0)
        d.rectangle([x1 - c - 44, y1 - 6, x1 - c - 10, y1], fill=0)
    elif style == "brackets":
        arm, t = 28, 4  # HUD corner brackets around a hairline frame
        d.rectangle([x0 + 6, y0 + 6, x1 - 6, y1 - 6], outline=0, width=1)
        for cx, sx in ((x0, 1), (x1, -1)):
            for cy, sy in ((y0, 1), (y1, -1)):
                d.rectangle(sorted_box(cx, cy, cx + sx * arm, cy + sy * t), fill=0)
                d.rectangle(sorted_box(cx, cy, cx + sx * t, cy + sy * arm), fill=0)
    elif style == "ticks":
        d.rectangle([x0 + 6, y0 + 6, x1 - 6, y1 - 6], outline=0, width=1)  # ruler scale around a hairline frame
        for i, x in enumerate(range(x0 + 6, x1 - 5, 8)):
            n = 6 if i % 5 == 0 else 3
            d.line([(x, y0 + 6), (x, y0 + 6 - n)], fill=0)
            d.line([(x, y1 - 6), (x, y1 - 6 + n)], fill=0)
        for i, y in enumerate(range(y0 + 6, y1 - 5, 8)):
            n = 6 if i % 5 == 0 else 3
            d.line([(x0 + 6, y), (x0 + 6 - n, y)], fill=0)
            d.line([(x1 - 6, y), (x1 - 6 + n, y)], fill=0)
    else:  # solid
        d.rectangle([x0, y0, x1, y1], outline=0, width=3)


def _hazard_bar(img: Image.Image, y0: int) -> None:
    band = Image.new("L", (W, BAR_H), 255)
    bd = ImageDraw.Draw(band)
    for x in range(-BAR_H, W + BAR_H, 20):
        bd.polygon([(x, BAR_H), (x + 10, BAR_H), (x + 10 + BAR_H, 0), (x + BAR_H, 0)], fill=0)
    bd.rectangle([0, 0, W - 1, BAR_H - 1], outline=0, width=1)
    img.paste(band, (0, y0))


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


# --- render ------------------------------------------------------------------------------------------------------


def _pick(value: str, allowed: tuple[str, ...], default: str) -> str:
    return value if value in allowed else default


def render(spec: LabelSpec) -> Image.Image:
    """Grayscale W x H canvas; everything is drawn inside the top SH rows."""
    img = Image.new("L", (W, H), 255)

    if spec.image_path:
        src = ImageOps.contain(Image.open(spec.image_path).convert("L"), (W, SH))
        if spec.threshold is not None:
            src = src.point(lambda v: 255 if v >= spec.threshold else 0)
        img.paste(src, ((W - src.width) // 2, (SH - src.height) // 2))
        return img

    background = _pick(spec.background, BACKGROUNDS, "none")
    if background != "none":
        img.paste(_background(background), (0, 0))
    draw = ImageDraw.Draw(img)

    top, bottom = 0, SH  # frame: what's left after the hazard bars
    if spec.bars:
        _hazard_bar(img, 0)
        _hazard_bar(img, SH - BAR_H)
        top, bottom = BAR_H, SH - BAR_H
    margin = MARGIN
    if spec.border:
        style = _pick(spec.border_style, BORDER_STYLES, "solid")
        _border(draw, style, 0, top, W - 1, bottom - 1)
        margin = max(MARGIN, BORDER_INSET[style] + 4)

    ax0, ax1, ay0, ay1 = margin, W - margin, top + margin, bottom - margin
    text_w = ax1 - ax0
    if spec.qr:
        qimg = _qr_image(spec.qr, ay1 - ay0)
        qx = ax1 - qimg.width if spec.text else ax0 + (text_w - qimg.width) // 2
        qy = ay0 + (ay1 - ay0 - qimg.height) // 2
        draw.rectangle([qx - 4, qy - 4, qx + qimg.width + 3, qy + qimg.height + 3], fill=255)  # quiet zone
        img.paste(qimg, (qx, qy))
        text_w = qx - MARGIN - ax0

    if spec.text and text_w > 0:
        align = _pick(spec.align, ALIGNMENTS, "center")
        valign = _pick(spec.valign, VALIGNMENTS, "middle")
        effect = _pick(spec.effect, EFFECTS, "none")
        path, native_slant = font_path(spec.font, spec.bold, spec.italic)
        shear = ITALIC_SHEAR if spec.italic and not native_slant else 0
        max_size = min(MAX_FONT_SIZE, spec.size) if spec.size > 0 else MAX_FONT_SIZE
        value, alpha = _fit_text_layer(
            spec.text.replace("\\n", "\n"), path, shear, align, effect, background != "none",
            text_w, ay1 - ay0, max_size,
        )
        x = ax0 + {"left": 0, "center": (text_w - value.width) // 2, "right": text_w - value.width}[align]
        y = ay0 + {"top": 0, "middle": (ay1 - ay0 - value.height) // 2, "bottom": ay1 - ay0 - value.height}[valign]
        img.paste(value, (x, y), alpha)
    return img


def to_bitmap(img: Image.Image) -> Image.Image:
    """The exact 1-bit image the printer will burn (also used for the GUI preview)."""
    return img.convert("1", dither=Image.Dither.FLOYDSTEINBERG)
