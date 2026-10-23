"""Qt GUI: edit a label, see the exact 1-bit preview, print it."""
from __future__ import annotations

import sys
import tempfile
import time

from pathlib import Path

from PySide6.QtCore import QEvent, QObject, QSettings, Qt
from PySide6.QtGui import (
    QAction,
    QColor,
    QFont,
    QFontDatabase,
    QIcon,
    QImage,
    QKeySequence,
    QPainter,
    QPixmap,
    QStandardItem,
    QStandardItemModel,
)
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QCompleter,
    QFileDialog,
    QFrame,
    QGroupBox,
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

from . import core, theme
from . import fonts as bundled_fonts
from .presets import PresetStore

PREVIEW_SCALE = 2
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp"}
NO_PRESET = "— presets —"


LABELS = {
    "3d": "3D WordArt", "grid": "Graph paper", "dots": "Polka dots", "bevel": "Win95 bevel",
    "hexgrid": "Hex grid", "matrix": "Matrix rain", "circuit": "Circuit board", "chamfer": "Cyber panel",
    "brackets": "HUD brackets", "ticks": "Ruler ticks", "neon": "Neon glow",
}


def _register_bundled_fonts() -> None:
    """Make Qt aware of the shipped fonts so the picker can preview them even when they aren't installed."""
    for font in bundled_fonts.BUNDLED:
        for filename in font.files.values():
            QFontDatabase.addApplicationFont(str(bundled_fonts.FONT_DIR / filename))


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


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("T003 Label Studio")
        self.setAcceptDrops(True)
        QApplication.instance().installEventFilter(self)
        _register_bundled_fonts()
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
        self.image.setPlaceholderText("Image file")
        self.image.setToolTip("An image overrides the text and QR code")
        browse = QPushButton("Browse…")
        browse.clicked.connect(self.pick_image)
        image_row = QHBoxLayout()
        image_row.addWidget(self.image)
        image_row.addWidget(browse)
        paste = QPushButton("Paste")
        paste.setToolTip("Paste an image from the clipboard (Ctrl+V)")
        paste.clicked.connect(self.paste_image)
        image_row.addWidget(paste)
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

        text_tab = QFormLayout()
        text_tab.addRow("Font", self.font_box)
        text_tab.addRow("Style", style_row)
        text_tab.addRow("", self.all_fonts)
        text_tab.addRow("Size", self.size_spin)
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

        for spin in (self.threshold, self.size_spin, self.copies, self.density):
            spin.lineEdit().setTextMargins(6, 0, 0, 0)  # QSS padding doesn't reach the inner editor
        for form in (content, text_tab, retro, output):
            form.setHorizontalSpacing(14)
            form.setVerticalSpacing(8)
            form.setContentsMargins(12, 12, 12, 12)
            for row in range(form.rowCount()):  # one label column, so fields line up across tabs and the panel below
                label = form.itemAt(row, QFormLayout.LabelRole)
                if label and label.widget():
                    label.widget().setMinimumWidth(66)
        preset_form.setHorizontalSpacing(14)
        output.setContentsMargins(12, 18, 12, 12)  # room for the caption sitting on the frame's top edge
        output_panel = QGroupBox("Output")
        output_panel.setLayout(output)

        self.print_button = QPushButton("Print")
        self.print_button.setDefault(True)
        self.print_button.clicked.connect(self.print_now)
        self.status = QLabel("")
        self.status.setObjectName("status")
        self.status.setWordWrap(True)

        self.banner = theme.Banner()
        controls = QVBoxLayout()
        controls.setSpacing(10)
        controls.addWidget(self.banner)
        controls.addLayout(preset_form)
        controls.addWidget(tabs)
        controls.addWidget(output_panel)
        controls.addWidget(self.print_button)
        controls.addWidget(self.status)
        controls.addStretch()

        self.preview = QLabel()
        self.preview.setObjectName("screen")
        self.preview.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        bezel = QFrame()  # a chrome monitor bezel under the Y2K theme, invisible otherwise
        bezel.setObjectName("bezel")
        bezel_layout = QVBoxLayout(bezel)
        bezel_layout.setContentsMargins(14, 14, 14, 14)
        bezel_layout.addWidget(self.preview, 0, Qt.AlignTop)

        root = QHBoxLayout()
        root.addLayout(controls, 1)
        root.addWidget(bezel, 0, Qt.AlignTop)
        container = QWidget()
        container.setObjectName("root")
        container.setLayout(root)
        self.setCentralWidget(container)

        self.y2k_action = QAction("Y2K theme", self, checkable=True)
        self.y2k_action.toggled.connect(self.apply_theme)
        self.menuBar().addMenu("&View").addAction(self.y2k_action)
        self.y2k_action.setChecked(QSettings().value("y2k", True, type=bool))
        self.apply_theme(self.y2k_action.isChecked())

        for signal in (
            self.text.textChanged,
            self.qr.textChanged,
            self.image.textChanged,
            self.hard_threshold.toggled,
            self.threshold.valueChanged,
            self.font_box.currentIndexChanged,
            self.font_box.lineEdit().editingFinished,
            self.bold.toggled,
            self.italic.toggled,
            self.size_spin.valueChanged,
            self.align.currentIndexChanged,
            self.valign.currentIndexChanged,
            self.effect.currentIndexChanged,
            self.border_box.currentIndexChanged,
            self.background.currentIndexChanged,
            self.bars.toggled,
        ):
            signal.connect(self.refresh_preview)
        self.populate_fonts(False)
        self.font_box.setCurrentText(core.DEFAULT_FONT)
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
            font=self.font_box.currentText().strip() or core.DEFAULT_FONT,
            bold=self.bold.isChecked(),
            italic=self.italic.isChecked(),
            size=self.size_spin.value(),
            align=self.align.currentData(),
            valign=self.valign.currentData(),
            effect=self.effect.currentData(),
            border=border_style is not None,
            border_style=border_style or "solid",
            background=self.background.currentData(),
            bars=self.bars.isChecked(),
        )

    def apply_theme(self, y2k: bool) -> None:
        self.setStyleSheet(theme.stylesheet() if y2k else "")  # on the window, not the app: the system file dialog must stay unstyled
        self.banner.setVisible(y2k)
        QSettings().setValue("y2k", y2k)

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

    def set_spec(self, spec: core.LabelSpec) -> None:
        self.text.setPlainText(spec.text)
        self.qr.setText(spec.qr)
        self.image.setText(spec.image_path)
        self.hard_threshold.setChecked(spec.threshold is not None)
        if spec.threshold is not None:
            self.threshold.setValue(spec.threshold)
        self.copies.setValue(spec.copies)
        self.density.setValue(spec.density)
        self.font_box.setCurrentText(spec.font)
        self.bold.setChecked(spec.bold)
        self.italic.setChecked(spec.italic)
        self.size_spin.setValue(spec.size)
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

    def _image_from_mime(self, mime) -> str | None:
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

    def dragEnterEvent(self, event) -> None:
        mime = event.mimeData()
        if self._dropped_image(event) or mime.hasImage():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        path = self._image_from_mime(event.mimeData())
        if path:
            self.image.setText(path)
            event.acceptProposedAction()

    def paste_image(self) -> bool:
        path = self._image_from_mime(QApplication.clipboard().mimeData())
        if path:
            self.image.setText(path)
        return bool(path)

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        # Ctrl+V pastes a clipboard image, but only when there is no text to paste into a field.
        if event.type() == QEvent.KeyPress and event.matches(QKeySequence.Paste) and self.isActiveWindow():
            mime = QApplication.clipboard().mimeData()
            if mime and not mime.hasText() and (mime.hasImage() or mime.hasUrls()) and self.paste_image():
                return True
        return super().eventFilter(obj, event)

    def pick_image(self) -> None:
        # No parent: a dialog parented to this window would inherit the Y2K stylesheet
        path, _ = QFileDialog.getOpenFileName(None, "Choose image", "", "Images (*.png *.jpg *.jpeg *.bmp *.gif *.webp)")
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
    if "--selftest" in sys.argv:
        from .selftest import run

        sys.exit(run())
    app = QApplication(sys.argv)
    app.setApplicationName("T003 Label Studio")
    app.setOrganizationName("t003-label-gui")
    app.setDesktopFileName("t003-label-gui")  # lets Wayland/KDE match the window to the launcher and its icon
    app.setWindowIcon(QIcon(str(theme.ASSETS / "icon-256.png")))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
