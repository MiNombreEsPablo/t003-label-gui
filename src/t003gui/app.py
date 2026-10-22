"""Qt GUI: edit a label, see the exact 1-bit preview, print it."""
from __future__ import annotations

import sys

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFontComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from . import core
from .presets import PresetStore

PREVIEW_SCALE = 2
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp"}
NO_PRESET = "— presets —"


LABELS = {"3d": "3D WordArt", "grid": "Graph paper", "dots": "Polka dots", "stars": "Stars", "bevel": "Win95 bevel"}


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


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("T003 Label Printer")
        self.setAcceptDrops(True)
        self.presets = PresetStore()

        self.preset_box = QComboBox()
        self.preset_box.activated.connect(self.load_preset)
        save_preset = QPushButton("Save…")
        save_preset.clicked.connect(self.save_preset)
        self.delete_preset_button = QPushButton("Delete")
        self.delete_preset_button.clicked.connect(self.delete_preset)
        preset_row = QHBoxLayout()
        preset_row.addWidget(self.preset_box, 1)
        preset_row.addWidget(save_preset)
        preset_row.addWidget(self.delete_preset_button)
        preset_form = QFormLayout()
        preset_form.addRow("Preset", preset_row)

        # Content tab
        self.text = QPlainTextEdit()
        self.text.setPlaceholderText("Label text (Enter for a new line)")
        self.text.setFixedHeight(90)
        self.qr = QLineEdit()
        self.qr.setPlaceholderText("QR code content (optional)")
        self.image = QLineEdit()
        self.image.setPlaceholderText("Image file (overrides text/QR)")
        browse = QPushButton("Browse…")
        browse.clicked.connect(self.pick_image)
        image_row = QHBoxLayout()
        image_row.addWidget(self.image)
        image_row.addWidget(browse)
        self.hard_threshold = QCheckBox("Hard black/white cutoff (flat-colour art)")
        self.threshold = QSpinBox()
        self.threshold.setRange(0, 255)
        self.threshold.setValue(160)
        self.threshold.setEnabled(False)
        self.hard_threshold.toggled.connect(self.threshold.setEnabled)

        content = QFormLayout()
        content.addRow("Text", self.text)
        content.addRow("QR", self.qr)
        content.addRow("Image", image_row)
        content.addRow("", self.hard_threshold)
        content.addRow("Cutoff", self.threshold)

        # Text tab
        self.font_box = QFontComboBox()
        self.font_box.setFontFilters(QFontComboBox.ScalableFonts)
        self.font_box.setCurrentFont(QFont(core.DEFAULT_FONT))
        self.bold = QCheckBox("Bold")
        self.bold.setChecked(True)
        self.italic = QCheckBox("Italic")
        font_row = QHBoxLayout()
        font_row.addWidget(self.font_box, 1)
        font_row.addWidget(self.bold)
        font_row.addWidget(self.italic)
        self.size = QSpinBox()
        self.size.setRange(0, 120)
        self.size.setSpecialValueText("Auto (fit)")
        self.size.setToolTip("Largest text size in dots; Auto picks the biggest that fits")
        self.align = _choice_box(core.ALIGNMENTS, default="center")
        self.valign = _choice_box(core.VALIGNMENTS, default="middle")
        self.effect = _choice_box(core.EFFECTS)

        text_tab = QFormLayout()
        text_tab.addRow("Font", font_row)
        text_tab.addRow("Size", self.size)
        text_tab.addRow("Align", self.align)
        text_tab.addRow("Vertical", self.valign)
        text_tab.addRow("Effect", self.effect)

        # Retro tab
        self.border_box = _choice_box(core.BORDER_STYLES, none_label="None")
        self.background = _choice_box(core.BACKGROUNDS)
        self.bars = QCheckBox("Under-construction bars")

        retro = QFormLayout()
        retro.addRow("Border", self.border_box)
        retro.addRow("Background", self.background)
        retro.addRow("", self.bars)

        tabs = QTabWidget()
        for title, layout in (("Content", content), ("Text", text_tab), ("Retro", retro)):
            page = QWidget()
            page.setLayout(layout)
            tabs.addTab(page, title)

        self.copies = QSpinBox()
        self.copies.setRange(1, 99)
        self.density = QSpinBox()
        self.density.setRange(0, 15)
        self.density.setValue(7)
        output = QFormLayout()
        output.addRow("Copies", self.copies)
        output.addRow("Darkness", self.density)

        self.print_button = QPushButton("Print")
        self.print_button.setDefault(True)
        self.print_button.clicked.connect(self.print_now)
        self.status = QLabel("")
        self.status.setWordWrap(True)

        controls = QVBoxLayout()
        controls.addLayout(preset_form)
        controls.addWidget(tabs)
        controls.addLayout(output)
        controls.addWidget(self.print_button)
        controls.addWidget(self.status)
        controls.addStretch()

        self.preview = QLabel()
        self.preview.setAlignment(Qt.AlignTop | Qt.AlignHCenter)

        root = QHBoxLayout()
        root.addLayout(controls, 1)
        root.addWidget(self.preview, 0)
        container = QWidget()
        container.setLayout(root)
        self.setCentralWidget(container)

        for signal in (
            self.text.textChanged,
            self.qr.textChanged,
            self.image.textChanged,
            self.hard_threshold.toggled,
            self.threshold.valueChanged,
            self.font_box.currentFontChanged,
            self.bold.toggled,
            self.italic.toggled,
            self.size.valueChanged,
            self.align.currentIndexChanged,
            self.valign.currentIndexChanged,
            self.effect.currentIndexChanged,
            self.border_box.currentIndexChanged,
            self.background.currentIndexChanged,
            self.bars.toggled,
        ):
            signal.connect(self.refresh_preview)
        self.reload_presets()
        self.refresh_preview()

    def spec(self) -> core.LabelSpec:
        border_style = self.border_box.currentData()
        return core.LabelSpec(
            text=self.text.toPlainText().strip(),
            qr=self.qr.text().strip(),
            image_path=self.image.text().strip(),
            threshold=self.threshold.value() if self.hard_threshold.isChecked() else None,
            copies=self.copies.value(),
            density=self.density.value(),
            font=self.font_box.currentFont().family(),
            bold=self.bold.isChecked(),
            italic=self.italic.isChecked(),
            size=self.size.value(),
            align=self.align.currentData(),
            valign=self.valign.currentData(),
            effect=self.effect.currentData(),
            border=border_style is not None,
            border_style=border_style or "solid",
            background=self.background.currentData(),
            bars=self.bars.isChecked(),
        )

    def set_spec(self, spec: core.LabelSpec) -> None:
        self.text.setPlainText(spec.text)
        self.qr.setText(spec.qr)
        self.image.setText(spec.image_path)
        self.hard_threshold.setChecked(spec.threshold is not None)
        if spec.threshold is not None:
            self.threshold.setValue(spec.threshold)
        self.copies.setValue(spec.copies)
        self.density.setValue(spec.density)
        self.font_box.setCurrentFont(QFont(spec.font))
        self.bold.setChecked(spec.bold)
        self.italic.setChecked(spec.italic)
        self.size.setValue(spec.size)
        for box, value in ((self.align, spec.align), (self.valign, spec.valign), (self.effect, spec.effect),
                           (self.background, spec.background)):
            box.setCurrentIndex(max(0, box.findData(value)))
        self.border_box.setCurrentIndex(max(0, self.border_box.findData(spec.border_style)) if spec.border else 0)
        self.bars.setChecked(spec.bars)

    def reload_presets(self, select: str | None = None) -> None:
        self.preset_box.clear()
        self.preset_box.addItem(NO_PRESET)
        self.preset_box.addItems(self.presets.names())
        if select:
            self.preset_box.setCurrentText(select)
        self.delete_preset_button.setEnabled(self.preset_box.currentIndex() > 0)

    def load_preset(self, index: int) -> None:
        self.delete_preset_button.setEnabled(index > 0)
        spec = self.presets.get(self.preset_box.itemText(index)) if index > 0 else None
        if spec:
            self.set_spec(spec)
            self.status.setText("")

    def save_preset(self) -> None:
        current = self.preset_box.currentText()
        name, ok = QInputDialog.getText(
            self, "Save preset", "Preset name:", text="" if current == NO_PRESET else current
        )
        name = name.strip()
        if not ok or not name or name == NO_PRESET:
            return
        self.presets.save(name, self.spec())
        self.reload_presets(select=name)
        self.status.setText(f"Saved preset {name!r}.")

    def delete_preset(self) -> None:
        name = self.preset_box.currentText()
        if self.preset_box.currentIndex() == 0:
            return
        if QMessageBox.question(self, "Delete preset", f"Delete preset {name!r}?") == QMessageBox.Yes:
            self.presets.delete(name)
            self.reload_presets()

    @staticmethod
    def _dropped_image(event) -> str | None:
        for url in event.mimeData().urls():
            if url.isLocalFile() and Path(url.toLocalFile()).suffix.lower() in IMAGE_SUFFIXES:
                return url.toLocalFile()
        return None

    def dragEnterEvent(self, event) -> None:
        if self._dropped_image(event):
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        path = self._dropped_image(event)
        if path:
            self.image.setText(path)
            event.acceptProposedAction()

    def pick_image(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Choose image", "", "Images (*.png *.jpg *.jpeg *.bmp *.gif *.webp)")
        if path:
            self.image.setText(path)

    def refresh_preview(self) -> None:
        spec = self.spec()
        try:
            bitmap = core.to_bitmap(core.render(spec)).convert("L")
        except Exception as e:  # bad image path etc. — show it instead of crashing
            self.status.setText(f"Preview error: {e}")
            return
        self.status.setText("")
        data = bitmap.tobytes()
        qimg = QImage(data, core.W, core.H, core.W, QImage.Format_Grayscale8).copy()
        pix = QPixmap.fromImage(qimg).scaled(
            core.W * PREVIEW_SCALE, core.H * PREVIEW_SCALE, Qt.KeepAspectRatio, Qt.FastTransformation
        )
        # Shade the gap below the sticker so it's obvious nothing there gets printed.
        painter = QPainter(pix)
        painter.fillRect(0, core.SH * PREVIEW_SCALE, pix.width(), pix.height(), QColor(0, 0, 0, 40))
        painter.setPen(QColor(120, 120, 120))
        painter.drawRect(0, 0, pix.width() - 1, core.SH * PREVIEW_SCALE - 1)
        painter.end()
        self.preview.setPixmap(pix)

    def print_now(self) -> None:
        spec = self.spec()
        if not (spec.text or spec.qr or spec.image_path):
            self.status.setText("Nothing to print.")
            return
        self.print_button.setEnabled(False)
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            problems = core.print_label(spec)
        except core.PrinterError as e:
            QMessageBox.critical(self, "Print failed", str(e))
            self.status.setText(str(e))
        else:
            self.status.setText("Printer: " + ", ".join(problems) if problems else "Sent.")
        finally:
            QApplication.restoreOverrideCursor()
            self.print_button.setEnabled(True)


def main() -> None:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
