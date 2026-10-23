"""The editing controls, one self-contained widget per group.

Each panel owns its widgets and maps them to/from its slice of `LabelSpec` (`read` / `write`), emitting `changed` when
anything the preview depends on is edited. `MainWindow` only decides where the panels go, so a layout can arrange them
as tabs, side modules, or anything else without touching the controls.
"""
from __future__ import annotations

import tempfile
import time
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QImage, QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QCompleter,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QWidget,
)

from . import core
from . import fonts as bundled_fonts
from .spec import IMAGE_SUFFIXES
from .widgets import SliderSpin, TenthsSpinBox, log_mapping

LABELS = {
    "3d": "3D WordArt", "grid": "Graph paper", "dots": "Polka dots", "bevel": "Win95 bevel",
    "hexgrid": "Hex grid", "matrix": "Matrix rain", "circuit": "Circuit board", "chamfer": "Cyber panel",
    "brackets": "HUD brackets", "ticks": "Ruler ticks", "neon": "Neon glow",
    "floyd": "Floyd–Steinberg (smooth)", "bayer4": "Ordered 4×4 (crosshatch)", "bayer8": "Ordered 8×8 (finer)",
    "threshold": "Hard cutoff (flat art)",
    "only": "Image only", "left": "Left of text", "right": "Right of text",
    "top": "Above text", "bottom": "Below text", "behind": "Behind text",
}


def has_image(mime) -> bool:
    """Whether `mime` carries an image file or raw image data (cheap: nothing is saved)."""
    if mime is None:
        return False
    return mime.hasImage() or any(
        u.isLocalFile() and Path(u.toLocalFile()).suffix.lower() in IMAGE_SUFFIXES for u in mime.urls()
    )


def image_from_mime(mime) -> str | None:
    """Path of an image in `mime`: a dropped file, else raw pixels saved to a temp PNG."""
    if mime is None:
        return None
    for url in mime.urls():
        if url.isLocalFile() and Path(url.toLocalFile()).suffix.lower() in IMAGE_SUFFIXES:
            return url.toLocalFile()
    if mime.hasImage():
        image = QImage(mime.imageData())
        if not image.isNull():
            folder = Path(tempfile.gettempdir()) / "t003-label-gui"
            folder.mkdir(exist_ok=True)
            path = folder / f"pasted-{time.time_ns()}.png"
            if image.save(str(path)):
                return str(path)
    return None


def _font_box() -> QComboBox:
    """Editable, so any installed family can be typed even when the list shows only the curated set."""
    box = QComboBox()
    box.setEditable(True)
    box.setInsertPolicy(QComboBox.NoInsert)
    box.setMaxVisibleItems(24)
    return box


def _choice_box(values, default=None, none_label=None) -> QComboBox:
    """Combo whose item data is the spec value; none_label adds a leading item with data None."""
    box = QComboBox()
    if none_label:
        box.addItem(none_label, None)
    for v in values:
        box.addItem(LABELS.get(v, v.capitalize()), v)
    if default:
        box.setCurrentIndex(box.findData(default))
    return box


def _tidy(form: QFormLayout, top: int = 12) -> None:
    """Shared spacing and one label column, so fields line up across panels."""
    form.setHorizontalSpacing(14)
    form.setVerticalSpacing(8)
    form.setContentsMargins(12, top, 12, 12)
    for row in range(form.rowCount()):
        label = form.itemAt(row, QFormLayout.LabelRole)
        if label and label.widget():
            label.widget().setMinimumWidth(66)
    for spin in form.parentWidget().findChildren(QSpinBox):
        spin.lineEdit().setTextMargins(6, 0, 0, 0)  # QSS padding doesn't reach the inner editor


class ContentPanel(QWidget):
    title = "Content"
    changed = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.text = QPlainTextEdit()
        self.text.setPlaceholderText("Label text (Enter for a new line)")
        self.text.setFixedHeight(90)
        self.qr = QLineEdit()
        self.qr.setPlaceholderText("QR code content (optional)")
        self.image = QLineEdit()
        self.image.setPlaceholderText("Image file")
        self.image.setToolTip("With the default layout the picture replaces the text and QR code;\n"
                              "choose another layout on the Image tab to print them together.")
        self.image.setAccessibleName("Image file")
        self.image.setClearButtonEnabled(True)  # the x that removes the picture again
        browse = QPushButton("Browse…")
        browse.clicked.connect(self.pick_image)
        paste = QPushButton("Paste")
        paste.setToolTip("Paste an image from the clipboard (Ctrl+V)")
        paste.clicked.connect(self.paste_image)
        image_row = QHBoxLayout()
        image_row.addWidget(self.image)
        image_row.addWidget(browse)
        image_row.addWidget(paste)

        form = QFormLayout(self)
        form.addRow("Text", self.text)
        form.addRow("QR", self.qr)
        form.addRow("Image", image_row)
        _tidy(form)

        for signal in (self.text.textChanged, self.qr.textChanged, self.image.textChanged):
            signal.connect(self.changed)

    def read(self) -> dict:
        return {
            "text": self.text.toPlainText().strip(),
            "qr": self.qr.text().strip(),
            "image_path": self.image.text().strip(),
        }

    def write(self, spec: core.LabelSpec) -> None:
        self.text.setPlainText(spec.text)
        self.qr.setText(spec.qr)
        self.image.setText(spec.image_path)

    def set_image(self, path: str) -> None:
        self.image.setText(path)

    def paste_image(self) -> bool:
        path = image_from_mime(QApplication.clipboard().mimeData())
        if path:
            self.set_image(path)
        return bool(path)

    def pick_image(self) -> None:
        # No parent: a dialog parented to a styled window would inherit its stylesheet
        path, _ = QFileDialog.getOpenFileName(None, "Choose image", "", "Images (*.png *.jpg *.jpeg *.bmp *.gif *.webp)")
        if path:
            self.set_image(path)


class TextPanel(QWidget):
    title = "Text"
    changed = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.font_box = _font_box()
        self.all_fonts = QCheckBox("Show all installed fonts")
        self.all_fonts.setToolTip("Off: the curated set that ships with the app. On: every installed family.")
        self.all_fonts.toggled.connect(self.populate_fonts)
        self.all_fonts.setVisible(bool(core.list_font_families()))  # needs fontconfig (Linux)
        self.bold = QCheckBox("Bold")
        self.bold.setChecked(True)
        self.italic = QCheckBox("Italic")
        style_row = QHBoxLayout()
        style_row.addWidget(self.bold)
        style_row.addSpacing(12)
        style_row.addWidget(self.italic)
        style_row.addStretch(1)
        self.size_spin = QSpinBox()
        self.size_spin.setRange(0, 120)
        self.size_spin.setSpecialValueText("Auto (fit)")
        self.size_spin.setToolTip("Largest text size in dots; Auto picks the biggest that fits")
        self.align = _choice_box(core.ALIGNMENTS, default="center")
        self.valign = _choice_box(core.VALIGNMENTS, default="middle")
        self.effect = _choice_box(core.EFFECTS)

        form = QFormLayout(self)
        form.addRow("Font", self.font_box)
        form.addRow("Style", style_row)
        form.addRow("", self.all_fonts)
        form.addRow("Size", self.size_spin)
        form.addRow("Align", self.align)
        form.addRow("Vertical", self.valign)
        form.addRow("Effect", self.effect)
        _tidy(form)

        self.populate_fonts(False)
        self.font_box.setCurrentText(core.DEFAULT_FONT)
        for signal in (self.font_box.currentIndexChanged, self.font_box.lineEdit().editingFinished, self.bold.toggled,
                       self.italic.toggled, self.size_spin.valueChanged, self.align.currentIndexChanged,
                       self.valign.currentIndexChanged, self.effect.currentIndexChanged):
            signal.connect(self.changed)

    def read(self) -> dict:
        return {
            "font": self.font_box.currentText().strip() or core.DEFAULT_FONT,
            "bold": self.bold.isChecked(),
            "italic": self.italic.isChecked(),
            "size": self.size_spin.value(),
            "align": self.align.currentData(),
            "valign": self.valign.currentData(),
            "effect": self.effect.currentData(),
        }

    def write(self, spec: core.LabelSpec) -> None:
        self.font_box.setCurrentText(spec.font)
        self.bold.setChecked(spec.bold)
        self.italic.setChecked(spec.italic)
        self.size_spin.setValue(spec.size)
        for box, value in ((self.align, spec.align), (self.valign, spec.valign), (self.effect, spec.effect)):
            box.setCurrentIndex(max(0, box.findData(value)))

    def populate_fonts(self, show_all: bool = False) -> None:
        """Curated, grouped list by default; every installed family on request. The current font is kept."""
        current = self.font_box.currentText() or core.DEFAULT_FONT
        model = QStandardItemModel(self.font_box)

        def add(family: str, tip: str = "") -> None:
            item = QStandardItem(family)
            item.setFont(QFont(family))
            item.setToolTip(tip)
            model.appendRow(item)

        if show_all:
            for family in core.list_font_families():
                add(family)
        else:
            own_japanese = {f.family for f in bundled_fonts.BUNDLED if f.ja}
            for category, names in bundled_fonts.categories():
                header = QStandardItem(f"— {category} —")
                header.setEnabled(False)
                model.appendRow(header)
                for name in names:
                    add(name, "Has its own Japanese glyphs" if name in own_japanese
                        else f"Japanese text borrows {bundled_fonts.FALLBACK_JA.family}")
        self.font_box.blockSignals(True)
        self.font_box.setModel(model)
        completer = QCompleter(model, self.font_box)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setFilterMode(Qt.MatchContains)
        self.font_box.setCompleter(completer)
        self.font_box.setCurrentText(current)
        self.font_box.blockSignals(False)


class ImagePanel(QWidget):
    """How a picture becomes dots: dither, tone and looks. Only matters when an image is chosen."""

    title = "Image"
    changed = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.hint = QLabel("Choose an image first (Content tab).")
        self.image_layout = _choice_box(core.IMAGE_LAYOUTS)
        self.image_layout.setToolTip("How the picture shares the label with the text and QR code.\n"
                                     "'Image only' prints just the picture and ignores the text.")
        self.image_layout.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)  # don't widen the window
        self.image_layout.setMinimumContentsLength(10)
        self.image_layout.setAccessibleName("Layout")
        self.image_size = QSpinBox()
        self.image_size.setRange(20, 80)
        self.image_size.setValue(40)
        self.image_size.setSuffix(" %")
        self.image_size.setToolTip("The picture's share of the label")
        self.image_size.setAccessibleName("Picture size")
        layout_row = QHBoxLayout()
        layout_row.addWidget(self.image_layout, 1)
        layout_row.addWidget(self.image_size)
        self.dither = _choice_box(core.DITHERS + ("threshold",))
        self.dither.setToolTip("Floyd–Steinberg is smooth and best for photos; ordered dithering gives the regular\n"
                               "crosshatch of 90s handheld cameras; a hard cutoff suits flat-colour art.")
        self.cutoff = SliderSpin(0, 255, default=160)
        self.cutoff.setValue(160)
        self.cutoff.setToolTip("Pixels lighter than this print white, darker print black")
        self.brightness = SliderSpin(-100, 100, default=0)
        self.contrast = SliderSpin(-100, 100, default=0)
        for tone in (self.brightness, self.contrast):
            tone.setToolTip("Drag, type a number, or double-click the slider to reset it")
        self.gamma = SliderSpin(3, 30, default=10, spin=TenthsSpinBox(), mapping=log_mapping(3, 30, neutral=10))  # tenths
        self.gamma.setValue(10)
        self.gamma.setToolTip("Above 1.0 lightens the mid-tones, below 1.0 darkens them. Double-click to reset.")
        self.pixelate = SliderSpin(0, 32, default=0)
        self.pixelate.setSpecialValueText("Off")
        self.pixelate.setSuffix(" dots")
        self.pixelate.setToolTip("Chunky blocks, dithered at the low resolution: 3 gives the look of a 90s handheld camera")
        for control, name in ((self.cutoff, "Cutoff"), (self.brightness, "Brightness"), (self.contrast, "Contrast"),
                              (self.gamma, "Gamma"), (self.pixelate, "Pixelate")):
            control.set_name(name)  # the row labels aren't attached to the slider or the box
        self.mirror = QCheckBox("Mirror")
        self.flip = QCheckBox("Flip")
        self.invert = QCheckBox("Invert")
        self.reset = QPushButton("Reset")
        self.reset.setToolTip("Put every image setting back to its default")
        self.reset.clicked.connect(self.reset_all)
        looks_row = QHBoxLayout()
        looks_row.setSpacing(16)
        for box in (self.mirror, self.flip, self.invert):
            looks_row.addWidget(box)
        looks_row.addStretch(1)
        looks_row.addWidget(self.reset)

        form = self._form = QFormLayout(self)
        form.addRow(self.hint)
        form.addRow("Layout", layout_row)
        form.addRow("Dither", self.dither)
        form.addRow("Cutoff", self.cutoff)
        form.addRow("Brightness", self.brightness)
        form.addRow("Contrast", self.contrast)
        form.addRow("Gamma", self.gamma)
        form.addRow("Pixelate", self.pixelate)
        form.addRow("Options", looks_row)
        _tidy(form)

        self._active = False
        self.dither.currentIndexChanged.connect(self._sync_cutoff)
        self.image_layout.currentIndexChanged.connect(self._sync_layout)
        self._sync_cutoff()
        for signal in (self.image_layout.currentIndexChanged, self.image_size.valueChanged,
                       self.dither.currentIndexChanged, self.cutoff.valueChanged, self.brightness.valueChanged,
                       self.contrast.valueChanged, self.gamma.valueChanged, self.pixelate.valueChanged,
                       self.mirror.toggled, self.flip.toggled, self.invert.toggled):
            signal.connect(self.changed)
        self.set_active(False)

    def _sync_cutoff(self) -> None:
        hard = self.dither.currentData() == "threshold"
        self._form.setRowVisible(self.cutoff, hard)  # only shown when it applies, to keep the tab short
        self.cutoff.setEnabled(hard)

    def _sync_layout(self) -> None:
        """Only the side and band layouts have a size."""
        self.image_size.setEnabled(self._active and self.image_layout.currentData() in ("left", "right", "top", "bottom"))

    def set_active(self, active: bool) -> None:
        """Dim the controls (and say why) while no image is chosen."""
        self._active = active
        self.hint.setVisible(not active)
        for widget in (self.image_layout, self.dither, self.brightness, self.contrast, self.gamma, self.pixelate,
                       self.mirror, self.flip, self.invert, self.reset):
            widget.setEnabled(active)
        self.cutoff.setEnabled(active and self.dither.currentData() == "threshold")
        self._sync_layout()

    def reset_all(self) -> None:
        self.image_layout.setCurrentIndex(self.image_layout.findData("only"))
        self.image_size.setValue(40)
        self.dither.setCurrentIndex(self.dither.findData("floyd"))
        self.cutoff.setValue(160)
        self.brightness.setValue(0)
        self.contrast.setValue(0)
        self.gamma.setValue(10)
        self.pixelate.setValue(0)
        for box in (self.mirror, self.flip, self.invert):
            box.setChecked(False)

    def read(self) -> dict:
        mode = self.dither.currentData()
        hard = mode == "threshold"
        return {
            "image_layout": self.image_layout.currentData(),
            "image_size": self.image_size.value(),
            "dither": "floyd" if hard else mode,
            "threshold": self.cutoff.value() if hard else None,
            "brightness": self.brightness.value(),
            "contrast": self.contrast.value(),
            "gamma": self.gamma.value() / 10,
            "pixelate": self.pixelate.value(),
            "mirror": self.mirror.isChecked(),
            "flip": self.flip.isChecked(),
            "invert": self.invert.isChecked(),
        }

    def write(self, spec: core.LabelSpec) -> None:
        mode = "threshold" if spec.threshold is not None else spec.dither
        self.image_layout.setCurrentIndex(max(0, self.image_layout.findData(spec.image_layout)))
        self.image_size.setValue(min(80, max(20, spec.image_size)))
        self.dither.setCurrentIndex(max(0, self.dither.findData(mode)))
        if spec.threshold is not None:
            self.cutoff.setValue(spec.threshold)
        self.brightness.setValue(spec.brightness)
        self.contrast.setValue(spec.contrast)
        self.gamma.setValue(round(spec.gamma * 10))
        self.pixelate.setValue(spec.pixelate)
        self.mirror.setChecked(spec.mirror)
        self.flip.setChecked(spec.flip)
        self.invert.setChecked(spec.invert)


class DecorationPanel(QWidget):
    """Border, background pattern and hazard bars. Named for what it holds, not for a style: text effects are just
    as retro and live under Text, and stickers or stamps would belong here."""

    title = "Decoration"
    changed = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.border_box = _choice_box(core.BORDER_STYLES, none_label="None")
        self.background = _choice_box(core.BACKGROUNDS)
        self.bars = QCheckBox("Under-construction bars")

        form = QFormLayout(self)
        form.addRow("Border", self.border_box)
        form.addRow("Background", self.background)
        form.addRow("", self.bars)
        _tidy(form)

        for signal in (self.border_box.currentIndexChanged, self.background.currentIndexChanged, self.bars.toggled):
            signal.connect(self.changed)

    def read(self) -> dict:
        border_style = self.border_box.currentData()
        return {
            "border": border_style is not None,
            "border_style": border_style or "solid",
            "background": self.background.currentData(),
            "bars": self.bars.isChecked(),
        }

    def write(self, spec: core.LabelSpec) -> None:
        self.background.setCurrentIndex(max(0, self.background.findData(spec.background)))
        self.border_box.setCurrentIndex(max(0, self.border_box.findData(spec.border_style)) if spec.border else 0)
        self.bars.setChecked(spec.bars)


class OutputPanel(QGroupBox):
    """Print settings; they don't change the preview, so there is no `changed` signal."""

    def __init__(self) -> None:
        super().__init__("Output")
        self.copies = QSpinBox()
        self.copies.setRange(1, 99)
        self.density = QSpinBox()
        self.density.setRange(0, 15)
        self.density.setValue(7)

        form = QFormLayout(self)
        form.addRow("Copies", self.copies)
        form.addRow("Darkness", self.density)
        _tidy(form, top=18)  # room for the caption sitting on the frame's top edge

    def read(self) -> dict:
        return {"copies": self.copies.value(), "density": self.density.value()}

    def write(self, spec: core.LabelSpec) -> None:
        self.copies.setValue(spec.copies)
        self.density.setValue(spec.density)
