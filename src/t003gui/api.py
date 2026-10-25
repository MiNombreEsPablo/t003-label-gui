"""The label engine behind one small, client-neutral surface: a label as JSON in, pixels or TSPL out.

Every client drives the engine through this: the web build calls it from JavaScript (Pyodide), and a future
desktop shell could do the same. It needs no Qt and no USB, only what `render` and `protocol` need, and it takes and
returns plain data (strings, bytes, JSON), so the caller never touches Pillow or `LabelSpec` objects.

A picture is referenced by path (`image_path`); the caller makes the file exist wherever the engine runs (the web
build writes the upload into Pyodide's virtual file system).
"""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import PurePath

from . import bluetooth, doodle, fonts, form, imaging, render, spec, stickers
from .protocol import STATUS_QUERY, status_problems, tspl  # noqa: F401


def label_from_json(raw: str | bytes | dict) -> spec.LabelSpec:
    """A `LabelSpec` from JSON text or an already-parsed dict. Unknown keys are ignored and a wrongly typed value falls
    back to its default (see `LabelSpec.from_dict`); text that is not a JSON object raises ValueError."""
    if isinstance(raw, (str, bytes)):
        raw = json.loads(raw)
    if not isinstance(raw, dict):
        raise ValueError("a label is a JSON object")
    return spec.LabelSpec.from_dict(raw)


def preview_pixels(raw: str | bytes | dict) -> bytes:
    """The exact label the printer will burn, W x H bytes, row by row: 0 = black, 255 = white. The bottom rows below
    `SH` are the gap between stickers and are always white."""
    return render.to_bitmap(render.render(label_from_json(raw))).convert("L").tobytes()


def tspl_bytes(raw: str | bytes | dict) -> bytes:
    """The complete TSPL payload for a label, ready to send over any transport."""
    return tspl(label_from_json(raw))


def _rows(sticker: str):
    mask = stickers.mask(sticker, 1)
    return [[mask.getpixel((x, y)) for x in range(mask.width)] for y in range(mask.height)]


def adopt_image(path: str, name: str = "") -> str:
    """Take a picture a client wrote to `path` (an upload, a paste) and return the path to put in the label's
    `image_path`. Raises ValueError with a sentence for the user when it isn't a picture we can use."""
    return imaging.adopt(path, name)


def hints(raw: str | bytes | dict) -> list[str]:
    """Things worth telling the user about this label (for example that "Image only" drops the text), as plain
    sentences; empty when there is nothing to say."""
    hint = spec.layout_hint(label_from_json(raw))
    return [hint] if hint else []


def fonts_needed(raw: str | bytes | dict) -> list[str]:
    """Names of the font files (in the bundled `fonts/` folder) that rendering this label can open, so a client that
    loads fonts on demand knows what to fetch first: the chosen font, the Japanese fallback, the last resort and any font a background draws with."""
    label = label_from_json(raw)
    wanted = [render.font_path(label.font, label.bold, label.italic)[0], fonts.FALLBACK_JA.pick(label.bold, False)[0],
              *render.FALLBACK_FONT_PATHS]
    if label.background in render.BACKGROUND_FONTS:  # a pattern made of text, such as the matrix rain
        wanted.append(render.font_path(render.BACKGROUND_FONTS[label.background], False)[0])
    names: list[str] = []
    for path in wanted:
        if PurePath(path).parent == PurePath(fonts.FONT_DIR) and PurePath(path).name not in names:
            names.append(PurePath(path).name)
    return names


def options() -> str:
    """JSON describing what a label can be: the allowed choices, the geometry and the bundled fonts. A client builds
    its controls from this instead of repeating the lists."""
    return json.dumps({
        "geometry": {"width": spec.W, "height": spec.H, "sticker_height": spec.SH, "margin": spec.MARGIN},
        "effects": spec.EFFECTS,
        "backgrounds": spec.BACKGROUNDS,
        "border_styles": spec.BORDER_STYLES,
        "image_layouts": spec.IMAGE_LAYOUTS,
        "dithers": spec.DITHERS,
        "alignments": spec.ALIGNMENTS,
        "valignments": spec.VALIGNMENTS,
        "default_font": spec.DEFAULT_FONT,
        "fonts": [
            {"family": f.family, "category": f.category, "japanese": f.ja, "files": f.files} for f in fonts.BUNDLED
        ],
        "bluetooth": {"name_prefix": bluetooth.NAME_PREFIX, "ble": bluetooth.BLE, "status_query": list(STATUS_QUERY)},
        "form": form.describe(),
        "stickers": {  # each as 24 rows of "0"/"1" (1 = ink), for a client to draw and enlarge by whole numbers
            name: {"label": label, "rows": ["".join("1" if p else "0" for p in row) for row in _rows(name)]}
            for name, (label, _) in stickers.STICKERS.items()
        },
        "doodle": doodle.describe(),
        "defaults": asdict(spec.LabelSpec()),
        "content_fields": list(spec.CONTENT_FIELDS),  # a label with none of these set has nothing to print
    })
