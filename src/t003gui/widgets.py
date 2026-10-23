"""Small reusable controls."""
from __future__ import annotations

import math
from typing import Callable, NamedTuple, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QValidator
from PySide6.QtWidgets import QHBoxLayout, QSlider, QSpinBox, QWidget


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
