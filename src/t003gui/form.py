"""The label's simple controls, described as data, so every client builds them from one description.

A client (the web UI today) renders `describe()` instead of repeating the lists of fonts, effects, backgrounds, ranges
and labels. Adding a choice in `spec.py` therefore shows up everywhere; adding a new `LabelSpec` field fails
tests/test_form.py until it is described here (or listed in `PENDING`, the controls still to be built by hand).

Not described here, because each needs its own widget: the picture and its tone controls, the doodle, the printer.
No Qt in here.
"""
from __future__ import annotations

from dataclasses import dataclass

from . import fonts, spec

LABELS = {  # how a choice is worded when `value.capitalize()` isn't enough
    "3d": "3D WordArt", "grid": "Graph paper", "dots": "Polka dots", "bevel": "Win95 bevel",
    "hexgrid": "Hex grid", "matrix": "Matrix rain", "circuit": "Circuit board", "chamfer": "Cyber panel",
    "brackets": "HUD brackets", "ticks": "Ruler ticks", "neon": "Neon glow",
}

TABS = (("content", "Content"), ("text", "Text"), ("decoration", "Decoration"))
OUTPUT = "output"  # not a tab: shown next to the Print button, whatever tab is open

# LabelSpec fields without a control in the schema yet. Each phase of docs/web-port.md moves some of them out.
PENDING = frozenset({
    "image_path", "image_layout", "image_size", "threshold", "dither", "brightness", "contrast", "gamma", "pixelate",
    "mirror", "flip", "invert",  # the Image tab (phase 2)
    "doodle",  # the Doodle tab (phase 3)
})


@dataclass(frozen=True)
class Field:
    name: str  # the LabelSpec field it sets
    kind: str  # "text" | "textarea" | "choice" | "toggle" | "number"
    label: str
    tab: str  # a tab id from TABS, or OUTPUT
    row: str = ""  # fields with the same row title sit side by side under it (Bold and Italic: "Style")
    choices: tuple = ()  # choice: ((value, label, group), ...); group is "" when there are none
    none_label: str = ""  # choice: a leading item meaning "off", which turns `toggle` off
    toggle: str = ""  # the bool LabelSpec field that is on whenever a real choice is picked (border / border_style)
    minimum: int = 0
    maximum: int = 0
    zero_label: str = ""  # number: what 0 means, shown when the box is empty ("Auto (fit)")
    tip: str = ""

    def describe(self) -> dict:
        return {
            "name": self.name, "kind": self.kind, "label": self.label, "tab": self.tab, "row": self.row,
            "choices": [list(c) for c in self.choices], "none_label": self.none_label, "toggle": self.toggle,
            "minimum": self.minimum, "maximum": self.maximum, "zero_label": self.zero_label, "tip": self.tip,
        }


def _choices(values) -> tuple:
    return tuple((v, LABELS.get(v, v.capitalize()), "") for v in values)


def _font_choices() -> tuple:
    return tuple((family, family, category) for category, families in fonts.categories() for family in families)


FIELDS = (
    Field("text", "textarea", "Text", "content"),
    Field("qr", "text", "QR", "content", tip="Anything a phone can scan: a link, a Wi-Fi code, some words"),
    Field("font", "choice", "Font", "text", choices=_font_choices()),
    Field("bold", "toggle", "Bold", "text", row="Style"),
    Field("italic", "toggle", "Italic", "text", row="Style"),
    Field("size", "number", "Size", "text", minimum=0, maximum=120, zero_label="Auto (fit)",
          tip="Largest text size in dots; Auto picks the biggest that fits"),
    Field("align", "choice", "Align", "text", choices=_choices(spec.ALIGNMENTS)),
    Field("valign", "choice", "Vertical", "text", choices=_choices(spec.VALIGNMENTS)),
    Field("effect", "choice", "Effect", "text", choices=_choices(spec.EFFECTS)),
    Field("border_style", "choice", "Border", "decoration", choices=_choices(spec.BORDER_STYLES), none_label="None",
          toggle="border"),
    Field("background", "choice", "Background", "decoration", choices=_choices(spec.BACKGROUNDS)),
    Field("bars", "toggle", "Under-construction bars", "decoration"),
    Field("copies", "number", "Copies", OUTPUT, minimum=1, maximum=99),
    Field("density", "number", "Darkness", OUTPUT, minimum=0, maximum=15),
)


def covered() -> set[str]:
    """The LabelSpec fields the schema sets (a toggle's bool counts as set by its choice)."""
    return {f.name for f in FIELDS} | {f.toggle for f in FIELDS if f.toggle}


def describe() -> dict:
    return {"tabs": [{"id": i, "label": label} for i, label in TABS], "fields": [f.describe() for f in FIELDS]}
