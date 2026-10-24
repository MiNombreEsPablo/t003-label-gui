"""Small reusable controls."""
from __future__ import annotations

import math
import random
from typing import Callable, NamedTuple, Optional

from PIL import Image, ImageChops, ImageDraw, ImageFilter
from PySide6.QtCore import QPoint, QRect, Qt, QTimer, Signal
from PySide6.QtGui import QBrush, QColor, QImage, QPainter, QPen, QValidator
from PySide6.QtWidgets import QHBoxLayout, QSlider, QSpinBox, QWidget

from . import doodle, stickers
from .spec import SH, W


class TenthsSpinBox(QSpinBox):
    """An integer spin box shown in tenths (gamma 1.0 is stored as 10); still a QSpinBox, so the theme styles it."""

    def textFromValue(self, value: int) -> str:
        return f"{value / 10:.1f}"

    def valueFromText(self, text: str) -> int:
        try:
            return round(float(text) * 10)
        except ValueError:
            return self.value()

    def validate(self, text: str, pos: int):
        try:
            float(text)
        except ValueError:
            return (QValidator.Intermediate if text in ("", ".") else QValidator.Invalid), text, pos
        return QValidator.Acceptable, text, pos


class Mapping(NamedTuple):
    """How a slider's position (0..steps) relates to the value, when it isn't a straight line."""

    steps: int
    to_position: Callable[[int], int]
    from_position: Callable[[int], int]


def log_mapping(minimum: int, maximum: int, neutral: Optional[int] = None, steps: int = 1000) -> Mapping:
    """A logarithmic slider, so a range like 0.3-3.0 isn't squashed at one end.

    With `neutral` the track is two log scales meeting exactly in the middle: `minimum`..`neutral` fills the left half
    and `neutral`..`maximum` the right half. The neutral value then sits at the same spot as the 0 of a symmetric
    slider (brightness, contrast), so every "no change" handle lines up. (A single log scale put gamma 1.0 a few
    pixels right of centre.)
    """
    half = steps // 2
    if neutral is None:
        span = math.log(maximum / minimum)
        return Mapping(
            steps,
            lambda value: round(math.log(max(value, minimum) / minimum) / span * steps),
            lambda position: round(minimum * math.exp(position / steps * span)),
        )
    low, high = math.log(neutral / minimum), math.log(maximum / neutral)

    def to_position(value: int) -> int:
        if value <= neutral:
            return round(math.log(max(value, minimum) / minimum) / low * half)
        return half + round(math.log(value / neutral) / high * half)

    def from_position(position: int) -> int:
        if position <= half:
            return round(minimum * math.exp(position / half * low))
        return round(neutral * math.exp((position - half) / half * high))

    return Mapping(steps, to_position, from_position)


class _Slider(QSlider):
    reset_requested = Signal()

    def mouseDoubleClickEvent(self, event) -> None:
        self.reset_requested.emit()  # double-click puts the control back to neutral


class SliderSpin(QWidget):
    """A slider you can drag with a small value box beside it for exact numbers.

    The spin box is the source of truth (`value()`, `setValue()`, `valueChanged` mirror it), so everything that used
    to read a QSpinBox keeps working. Double-clicking the slider resets it to `default`.
    """

    valueChanged = Signal(int)
    VALUE_BOX_WIDTH = 92

    def __init__(self, minimum: int, maximum: int, default: Optional[int] = None, *, spin: Optional[QSpinBox] = None,
                 mapping: Optional[Mapping] = None) -> None:
        super().__init__()
        self.spin = spin or QSpinBox()
        self.spin.setRange(minimum, maximum)
        self.default = minimum if default is None else default
        self._mapping = mapping
        self._minimum = minimum
        self.slider = _Slider(Qt.Horizontal)
        steps = mapping.steps if mapping else maximum - minimum
        self.slider.setRange(0, steps)
        self.slider.setPageStep(max(1, steps // 10))
        self.slider.setFocusPolicy(Qt.StrongFocus)
        self.spin.setFixedWidth(self.VALUE_BOX_WIDTH)  # one width for every row, so all the sliders are the same length

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        layout.addWidget(self.slider, 1)
        layout.addWidget(self.spin)

        self.slider.valueChanged.connect(self._from_slider)
        self.slider.reset_requested.connect(self.reset)
        self.spin.valueChanged.connect(self._from_spin)
        self._place_slider(self.spin.value())

    def _position(self, value: int) -> int:
        return self._mapping.to_position(value) if self._mapping else value - self._minimum

    def _value_at(self, position: int) -> int:
        return self._mapping.from_position(position) if self._mapping else position + self._minimum

    def _place_slider(self, value: int) -> None:
        was = self.slider.blockSignals(True)
        self.slider.setValue(self._position(value))
        self.slider.blockSignals(was)

    def _from_slider(self, position: int) -> None:  # the user dragged it
        value = self._value_at(position)
        if value != self.spin.value():
            self.spin.setValue(value)  # which emits valueChanged exactly once, through _from_spin

    def _from_spin(self, value: int) -> None:  # typed, stepped, set from code or followed the slider
        self._place_slider(value)
        self.valueChanged.emit(value)

    def value(self) -> int:
        return self.spin.value()

    def setValue(self, value: int) -> None:
        self.spin.setValue(value)

    def reset(self) -> None:
        self.spin.setValue(self.default)

    def setSpecialValueText(self, text: str) -> None:
        self.spin.setSpecialValueText(text)

    def setSuffix(self, text: str) -> None:
        self.spin.setSuffix(text)

    def set_name(self, name: str) -> None:
        """The accessible name a screen reader announces (the row label next to it isn't attached to either part)."""
        self.slider.setAccessibleName(name)
        self.spin.setAccessibleName(f"{name} value")

    def setToolTip(self, text: str) -> None:
        for widget in (self, self.slider, self.spin):
            QWidget.setToolTip(widget, text)


def ink_image(mask: Image.Image) -> QImage:
    """A PIL ink mask (mode "L") as black pixels with that alpha, ready to paint."""
    alpha = QImage(mask.tobytes(), mask.width, mask.height, mask.width, QImage.Format_Alpha8).copy()
    return alpha.convertToFormat(QImage.Format_ARGB32_Premultiplied)


class DoodleCanvas(QWidget):
    """A pad the size of the sticker (one dot per pixel) to draw on with the mouse or a pen.

    Old-school paint tools: round, square and calligraphy brushes, a spray can, line/rectangle/ellipse, a paint bucket,
    stickers as stamps and an eraser. Strokes are hard-edged (the printer is 1-bit) and `ink` picks a dither pattern to
    paint with instead of solid black. The ink is a transparent image; `data()`/`set_data()` convert it to the
    `LabelSpec.doodle` text (see doodle.py). `underlay` is the rest of the label, shown faintly so you can draw around
    the text, and it stops the bucket like ink does; it is never part of the ink. `changed` fires when a stroke ends,
    not on every mouse move, because each emit re-renders the whole preview.
    """

    changed = Signal()
    TOOLS = ("pen", "square", "italic", "spray", "line", "box", "oval", "fill", "stamp", "eraser")
    INKS = {  # 4x4 dither tiles ("#" is ink); Qt's own hatch patterns are too sparse for the bucket to treat as a wall
        "solid": ("####",) * 4, "half": ("#.#.", ".#.#", "#.#.", ".#.#"), "quarter": ("#.#.", "....", "#.#.", "...."),
        "lines": ("####", "....", "####", "...."), "diagonal": ("##..", ".##.", "..##", "#..#"),
    }
    FREEHAND = ("pen", "square", "italic", "spray", "eraser")
    UNDO_LIMIT = 30
    SPRAY_MS = 25

    def __init__(self) -> None:
        super().__init__()
        self.tool = "pen"
        self.brush = 4  # stroke width in dots (not `size`: that is QWidget.size())
        self.ink = "solid"
        self.sticker = next(iter(stickers.STICKERS))
        self.sticker_scale = 2
        self._ink = self._blank()
        self._underlay: QImage | None = None
        self._blocks: Image.Image | None = None  # dark pixels of the underlay: where the bucket stops
        self._undo: list[QImage] = []
        self._start: QPoint | None = None  # where a stroke began
        self._last = QPoint()
        self._now = QPoint()
        self._hover: QPoint | None = None  # the sticker ghost follows the cursor
        self._spray = QTimer(self)
        self._spray.setInterval(self.SPRAY_MS)
        self._spray.timeout.connect(self._spray_tick)
        self.setFixedSize(W, SH)
        self.setMouseTracking(True)
        self.setCursor(Qt.CrossCursor)
        self.setToolTip("Drawn over everything else and printed exactly as you see it")

    @staticmethod
    def _blank() -> QImage:
        img = QImage(W, SH, QImage.Format_ARGB32_Premultiplied)
        img.fill(Qt.transparent)
        return img

    # --- state ---------------------------------------------------------------------------------------------------

    def data(self) -> str:
        return doodle.encode(self._alpha())

    def _alpha(self, image: QImage | None = None) -> Image.Image:
        alpha = (image or self._ink).convertToFormat(QImage.Format_Alpha8)
        return Image.frombuffer("L", (W, SH), bytes(alpha.constBits()), "raw", "L", alpha.bytesPerLine(), 1)

    def set_data(self, text: str) -> None:
        """Show a stored doodle (no `changed`: the caller already has it). Drawing it again starts a fresh undo list."""
        mask = doodle.decode(text)
        self._ink = self._blank() if mask is None else ink_image(mask)
        self._undo.clear()
        self.update()

    def set_underlay(self, label: Image.Image | None) -> None:
        self._underlay = self._blocks = None
        if label is not None:
            gray = label.convert("L").crop((0, 0, W, SH))
            self._underlay = QImage(gray.tobytes(), W, SH, W, QImage.Format_Grayscale8).copy()
            self._blocks = gray.point([255] * 128 + [0] * 128)
        self.update()

    def is_empty(self) -> bool:
        return not self.data()

    def can_undo(self) -> bool:
        return bool(self._undo)

    def undo(self) -> None:
        if self._undo:
            self._ink = self._undo.pop()
            self.update()
            self.changed.emit()

    def clear(self) -> None:
        if not self.is_empty():
            self._remember()
            self._ink = self._blank()
            self.update()
            self.changed.emit()

    def _remember(self) -> None:
        self._undo.append(self._ink.copy())
        del self._undo[:-self.UNDO_LIMIT]

    # --- drawing -------------------------------------------------------------------------------------------------

    def _ink_brush(self, solid: bool = False) -> QBrush:
        """Black paint, or the chosen dither tile (tiles are anchored to the pad, so neighbouring strokes line up)."""
        rows = self.INKS["solid"] if solid or self.tool == "eraser" or self.ink not in self.INKS else self.INKS[self.ink]
        if rows == self.INKS["solid"]:
            return QBrush(QColor("black"))
        tile = QImage(4, 4, QImage.Format_ARGB32)
        tile.fill(Qt.transparent)
        for y, row in enumerate(rows):
            for x, mark in enumerate(row):
                if mark == "#":
                    tile.setPixelColor(x, y, QColor("black"))
        return QBrush(tile)

    def _pen(self, width: int | None = None, solid: bool = False) -> QPen:
        return QPen(self._ink_brush(solid), self.brush if width is None else width, Qt.SolidLine, Qt.RoundCap,
                    Qt.RoundJoin)

    def _begin(self, painter: QPainter) -> None:
        painter.setBrush(Qt.NoBrush)
        erase = self.tool == "eraser"
        painter.setCompositionMode(QPainter.CompositionMode_Clear if erase else QPainter.CompositionMode_SourceOver)

    def _freehand(self, painter: QPainter, a: QPoint, b: QPoint) -> None:
        """One mouse segment of a freehand tool: `a` to `b` (equal for a click)."""
        self._begin(painter)
        if self.tool in ("pen", "eraser"):
            painter.setPen(self._pen(self.brush * 2 if self.tool == "eraser" else None))
            painter.drawPoint(a) if a == b else painter.drawLine(a, b)
            return
        if self.tool == "spray":
            return self._spray_at(painter, b)
        painter.setPen(self._pen(1))
        half = self.brush // 2
        steps = max(abs(b.x() - a.x()), abs(b.y() - a.y()), 1)
        for i in range(steps + 1):  # a dab every dot along the way, so fast strokes stay unbroken
            x = a.x() + (b.x() - a.x()) * i // steps
            y = a.y() + (b.y() - a.y()) * i // steps
            if self.tool == "square":
                painter.fillRect(QRect(x - half, y - half, self.brush, self.brush), self._ink_brush())
            else:  # calligraphy: a slanted nib
                painter.drawLine(x - half, y + half, x + half, y - half)

    def _spray_at(self, painter: QPainter, centre: QPoint) -> None:
        painter.setPen(self._pen(1, solid=True))
        radius = self.brush * 2
        for _ in range(max(3, radius * radius // 10)):
            r = radius * random.random() ** 0.5
            angle = random.random() * 6.2832
            painter.drawPoint(centre.x() + round(r * math.cos(angle)), centre.y() + round(r * math.sin(angle)))

    def _spray_tick(self) -> None:
        if self._start is None:
            return self._spray.stop()
        self._paint_ink(lambda p: self._freehand(p, self._now, self._now))

    def _shape(self, painter: QPainter, a: QPoint, b: QPoint) -> None:
        self._begin(painter)
        painter.setPen(self._pen())
        if self.tool == "line":
            painter.drawPoint(a) if a == b else painter.drawLine(a, b)
        else:
            box = QRect(a, b).normalized()
            painter.drawRect(box) if self.tool == "box" else painter.drawEllipse(box)

    def _stamp_image(self) -> QImage:
        return ink_image(stickers.mask(self.sticker, self.sticker_scale))

    def _stamp(self, painter: QPainter, centre: QPoint) -> None:
        image = self._stamp_image()
        painter.drawImage(centre.x() - image.width() // 2, centre.y() - image.height() // 2, image)

    def _bucket(self, at: QPoint) -> bool:
        """Paint the enclosed area around `at` (stopped by ink and by the label's own dark pixels). False: nothing to do."""
        walls = self._alpha().point([0] * 128 + [255] * 128).filter(ImageFilter.MaxFilter(3))  # patterned lines have gaps
        if self._blocks is not None:
            walls = ImageChops.lighter(walls, self._blocks)
        if walls.getpixel((at.x(), at.y())):
            return False  # clicked on a line
        ImageDraw.floodfill(walls, (at.x(), at.y()), 128)
        region = ink_image(walls.point(_ONLY_128).filter(ImageFilter.MaxFilter(3)))  # grown back to meet the walls
        paint = QImage(W, SH, QImage.Format_ARGB32_Premultiplied)
        paint.fill(Qt.transparent)
        p = QPainter(paint)
        p.fillRect(paint.rect(), self._ink_brush())
        p.setCompositionMode(QPainter.CompositionMode_DestinationIn)
        p.drawImage(0, 0, region)
        p.end()
        self._paint_ink(lambda q: q.drawImage(0, 0, paint))
        return True

    def _paint_ink(self, draw) -> None:
        painter = QPainter(self._ink)
        draw(painter)
        painter.end()
        self.update()

    # --- mouse ---------------------------------------------------------------------------------------------------

    def _inside(self, event) -> QPoint:
        p = event.position().toPoint()
        return QPoint(min(W - 1, max(0, p.x())), min(SH - 1, max(0, p.y())))

    def mousePressEvent(self, event) -> None:
        if event.button() != Qt.LeftButton:
            return
        at = self._inside(event)
        self._remember()
        if self.tool == "fill":
            if self._bucket(at):
                self.changed.emit()
            else:
                self._undo.pop()  # nothing changed, so nothing to undo
            return
        self._start = self._last = self._now = at
        if self.tool in self.FREEHAND:
            self._paint_ink(lambda p: self._freehand(p, at, at))
        if self.tool == "spray":
            self._spray.start()

    def mouseMoveEvent(self, event) -> None:
        self._hover = self._inside(event)
        if self._start is not None:
            self._now = self._hover
            if self.tool in self.FREEHAND and self.tool != "spray":
                a, b = self._last, self._now
                self._paint_ink(lambda p: self._freehand(p, a, b))
            self._last = self._now
        self.update()

    def leaveEvent(self, event) -> None:
        self._hover = None
        self.update()

    def mouseReleaseEvent(self, event) -> None:
        if self._start is None or event.button() != Qt.LeftButton:
            return
        self._spray.stop()
        end = self._inside(event)
        if self.tool == "stamp":
            self._paint_ink(lambda p: self._stamp(p, end))
        elif self.tool not in self.FREEHAND:
            start = self._start
            self._paint_ink(lambda p: self._shape(p, start, end))
        self._start = None
        self.update()
        self.changed.emit()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), Qt.white)
        if self._underlay is not None:
            painter.setOpacity(0.3)
            painter.drawImage(0, 0, self._underlay)
            painter.setOpacity(1)
        painter.drawImage(0, 0, self._ink)
        if self.tool == "stamp" and (self._hover or self._start):  # the sticker, ghosted where it will land
            painter.setOpacity(0.5)
            self._stamp(painter, self._now if self._start is not None else self._hover)
            painter.setOpacity(1)
        elif self._start is not None and self.tool in ("line", "box", "oval"):  # the shape being dragged out
            self._shape(painter, self._start, self._now)
        painter.setPen(QColor(120, 120, 120))
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(0, 0, W - 1, SH - 1)
        painter.end()


_ONLY_128 = [0] * 128 + [255] + [0] * 127  # lookup table: just the flood-filled pixels
