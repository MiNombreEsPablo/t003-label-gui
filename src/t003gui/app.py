"""Qt GUI: edit a label, see the exact 1-bit preview, print it."""
from __future__ import annotations

import re
import sys
from pathlib import Path

from PIL import ImageOps
from PySide6.QtCore import QEvent, QObject, QRect, QSettings, Qt, QUrl
from PySide6.QtGui import (
    QAction,
    QActionGroup,
    QDesktopServices,
    QColor,
    QFontDatabase,
    QIcon,
    QImage,
    QKeySequence,
    QPainter,
    QPixmap,
)
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QFormLayout,
    QHBoxLayout,
    QFileDialog,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from . import __version__, about, composition, core, panels, theme, updates
from . import fonts as bundled_fonts
from .presets import PresetStore

PREVIEW_SCALE = 2
NO_PRESET = "— presets —"


def _register_bundled_fonts() -> None:
    """Make Qt aware of the shipped fonts so the picker can preview them even when they aren't installed."""
    for font in bundled_fonts.BUNDLED:
        for filename in font.files.values():
            QFontDatabase.addApplicationFont(str(bundled_fonts.FONT_DIR / filename))


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

        preset_form.setHorizontalSpacing(14)

        self.content = panels.ContentPanel()
        self.text_panel = panels.TextPanel()
        self.image_panel = panels.ImagePanel()
        self.decoration = panels.DecorationPanel()
        self.output = panels.OutputPanel()
        self.panels = (self.content, self.text_panel, self.image_panel, self.decoration, self.output)
        self.content.image.textChanged.connect(lambda text: self.image_panel.set_active(bool(text.strip())))

        tabs = QTabWidget()
        for panel in (self.content, self.text_panel, self.image_panel, self.decoration):
            tabs.addTab(panel, panel.title)

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
        controls.addWidget(self.output)
        controls.addWidget(self.print_button)
        controls.addWidget(self.status)
        controls.addStretch()

        self.preview = QLabel()
        self.preview.setObjectName("screen")
        self.preview.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        self.preview.setToolTip(
            f"{core.W} × {core.SH} dots (about 48 × 28 mm), exactly what prints.\n"
            f"The strip below is the gap between stickers; nothing there is printed."
        )
        bezel = QFrame()  # a chrome monitor bezel under the Y2K themes, invisible otherwise
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

        file_menu = self.menuBar().addMenu("&File")
        for text, slot, shortcut in (
            ("&Open composition…", self.open_composition, QKeySequence.Open),
            ("&Save composition…", self.save_composition, QKeySequence.Save),
            ("&Export image…", self.export_image, QKeySequence("Ctrl+E")),
        ):
            action = QAction(text, self)
            action.setShortcut(shortcut)
            action.triggered.connect(slot)
            file_menu.addAction(action)
        file_menu.addSeparator()
        self.print_action = QAction("&Print label", self)
        self.print_action.setShortcut(QKeySequence.Print)
        self.print_action.triggered.connect(self.print_now)
        file_menu.addAction(self.print_action)
        file_menu.addSeparator()
        quit_action = QAction("&Quit", self)
        quit_action.setShortcut(QKeySequence.Quit)
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        edit_menu = self.menuBar().addMenu("&Edit")
        paste_action = QAction("&Paste image", self)
        paste_action.setShortcut(QKeySequence.Paste)  # in a text field Ctrl+V pastes text; see eventFilter for the image case
        paste_action.triggered.connect(self.paste_image_from_clipboard)
        self.clear_image_action = QAction("&Clear image", self)
        self.clear_image_action.triggered.connect(lambda: self.content.set_image(""))
        self.clear_image_action.setEnabled(False)
        self.content.image.textChanged.connect(lambda text: self.clear_image_action.setEnabled(bool(text.strip())))
        copy_action = QAction("Copy label as &image", self)
        copy_action.setShortcut(QKeySequence("Ctrl+Shift+C"))  # plain Ctrl+C belongs to the text fields
        copy_action.triggered.connect(self.copy_label_image)
        for action in (paste_action, self.clear_image_action):
            edit_menu.addAction(action)
        edit_menu.addSeparator()
        edit_menu.addAction(copy_action)

        theme_menu = self.menuBar().addMenu("&View").addMenu("&Theme")
        self.theme_actions: dict[str, QAction] = {}
        group = QActionGroup(self)
        for key, label in [(theme.SYSTEM, "System")] + [(t.key, t.title) for t in theme.THEMES.values()]:
            action = QAction(label, self, checkable=True)
            action.triggered.connect(lambda _checked=False, key=key: self.apply_theme(key))
            group.addAction(action)
            theme_menu.addAction(action)
            self.theme_actions[key] = action
        self.apply_theme(self._saved_theme())

        help_menu = self.menuBar().addMenu("&Help")
        help_menu.addAction(f"Version {__version__}").setEnabled(False)
        help_menu.addSeparator()
        help_menu.addAction("&About T003 Label Studio…", self.show_about)
        help_menu.addAction("Check for &updates…", self.check_for_updates)
        help_menu.addAction("&Report an issue…", lambda: self._open_url(about.ISSUES_URL))
        help_menu.addSeparator()
        help_menu.addAction("Open &presets folder", lambda: self._open_path(self.presets.path.parent))

        for panel in (self.content, self.text_panel, self.image_panel, self.decoration):
            panel.changed.connect(self.refresh_preview)
        self.reload_presets()
        self.refresh_preview()

    def spec(self) -> core.LabelSpec:
        fields: dict = {}
        for panel in self.panels:
            fields.update(panel.read())
        return core.LabelSpec(**fields)

    def set_spec(self, spec: core.LabelSpec) -> None:
        for panel in self.panels:
            panel.write(spec)

    @staticmethod
    def _saved_theme() -> str:
        settings = QSettings()
        key = settings.value("theme")
        if key is None and settings.contains("y2k"):  # setting from before themes were selectable
            key = theme.DEFAULT_THEME if settings.value("y2k", True, type=bool) else theme.SYSTEM
        return key if key in theme.THEMES or key == theme.SYSTEM else theme.DEFAULT_THEME

    def apply_theme(self, key: str) -> None:
        chosen = theme.THEMES.get(key)
        key = self.theme_key = chosen.key if chosen else theme.SYSTEM
        self.active_theme = chosen
        # On the window, not the app: the system file dialog must stay unstyled
        self.setStyleSheet(theme.stylesheet(chosen) if chosen else "")
        self.banner.setVisible(chosen is not None)
        if chosen:
            self.banner.set_style(chosen.banner)
        self.theme_actions[key].setChecked(True)
        QSettings().setValue("theme", key)
        self._align_label_columns()  # fonts differ per theme, so the shared label width is measured again
        self.refresh_preview()  # the preview takes the theme's tint

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
    def _dropped_composition(mime) -> str | None:
        for url in mime.urls():
            if url.isLocalFile() and url.toLocalFile().lower().endswith(composition.SUFFIX):
                return url.toLocalFile()
        return None

    def dragEnterEvent(self, event) -> None:
        if panels.has_image(event.mimeData()) or self._dropped_composition(event.mimeData()):
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        dropped = self._dropped_composition(event.mimeData())
        if dropped:
            self._open_composition_file(dropped)
            event.acceptProposedAction()
            return
        path = panels.image_from_mime(event.mimeData())
        if path:
            self.content.set_image(path)
            event.acceptProposedAction()

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        # Ctrl+V pastes a clipboard image, but only when there is no text to paste into a field.
        if event.type() == QEvent.KeyPress and event.matches(QKeySequence.Paste) and self.isActiveWindow():
            mime = QApplication.clipboard().mimeData()
            if mime and not mime.hasText() and (mime.hasImage() or mime.hasUrls()) and self.content.paste_image():
                return True
        return super().eventFilter(obj, event)

    def _align_label_columns(self) -> None:
        """One label column width across every panel, so the fields line up between tabs and the Output box."""
        labels = []
        for panel in self.panels:
            form = panel.layout()
            for row in range(form.rowCount()):
                item = form.itemAt(row, QFormLayout.LabelRole)
                if item and item.widget():
                    labels.append(item.widget())
        for label in labels:
            label.setMinimumWidth(0)
            label.ensurePolished()
        width = max(label.sizeHint().width() for label in labels)
        for label in labels:
            label.setMinimumWidth(width)

    @staticmethod
    def _open_url(url: str) -> None:
        QDesktopServices.openUrl(QUrl(url))

    @staticmethod
    def _open_path(folder) -> None:
        folder.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))

    @staticmethod
    def _plain_buttons(box: QMessageBox) -> None:
        """Message-box buttons are not the primary action: the big orange default style clips their text."""
        for button in box.buttons():
            button.setAutoDefault(False)
            button.setDefault(False)

    def check_for_updates(self) -> None:
        box = QMessageBox(self)
        box.setWindowTitle("Check for updates")
        box.setTextFormat(Qt.RichText)
        box.setText(f"<p>You have version <b>{__version__}</b>.</p><p>Checking GitHub…</p>")
        box.addButton(QMessageBox.Close)
        self._plain_buttons(box)
        box.setModal(True)
        box.setAttribute(Qt.WA_DeleteOnClose)  # takes the checker (its child) with it
        checker = updates.UpdateChecker(parent=box)  # owned by the dialog, gone with it

        def show(result: updates.UpdateResult) -> None:
            box.setText(updates.describe(__version__, result))
            if result.kind != "current" and result.url:
                label = "Download…" if result.kind == "newer" else "Open releases page"
                button = box.addButton(label, QMessageBox.ActionRole)
                button.clicked.connect(lambda: self._open_url(result.url))
                self._plain_buttons(box)

        checker.finished.connect(show)
        box.open()  # non-blocking: the window stays responsive while the request runs
        checker.check()

    def show_about(self) -> None:
        box = QMessageBox(self)
        box.setWindowTitle("About T003 Label Studio")
        box.setIconPixmap(QPixmap(str(theme.ASSETS / "icon-256.png")).scaled(
            96, 96, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        box.setTextFormat(Qt.RichText)
        box.setTextInteractionFlags(Qt.TextBrowserInteraction)  # clickable repo link
        active = theme.THEMES.get(self.theme_key)
        box.setText(about.about_html(core.printer_presence(), len(bundled_fonts.BUNDLED),
                                     link_color=active.link if active else None))
        licences = box.addButton("Font licences", QMessageBox.ActionRole)
        box.addButton(QMessageBox.Close)
        self._plain_buttons(box)
        box.exec()
        if box.clickedButton() is licences:
            self._open_path(bundled_fonts.FONT_DIR / "LICENSES")

    # --- files: compositions and exported images (system dialogs: unparented, so the theme doesn't reach them)

    def _start_dir(self) -> str:
        return QSettings().value("lastDir", "", type=str)

    def _remember_dir(self, path: str) -> None:
        QSettings().setValue("lastDir", str(Path(path).parent))

    def _suggested_name(self, suffix: str) -> str:
        first_line = (self.content.text.toPlainText().strip().splitlines() or [""])[0]
        stem = re.sub(r"[^\w -]+", "", first_line).strip()[:40] or "label"
        return str(Path(self._start_dir()) / (stem + suffix))

    def save_composition(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            None, "Save composition", self._suggested_name(composition.SUFFIX),
            f"T003 label (*{composition.SUFFIX})")
        if not path:
            return
        if not path.lower().endswith(composition.SUFFIX):
            path += composition.SUFFIX
        try:
            composition.save(path, self.spec())
        except OSError as e:
            QMessageBox.warning(self, "Save composition", f"Couldn't save the file: {e}")
            return
        self._remember_dir(path)
        self.status.setText(f"Saved {Path(path).name}.")

    def open_composition(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            None, "Open composition", self._start_dir(), f"T003 label (*{composition.SUFFIX})")
        if path:
            self._open_composition_file(path)

    def _open_composition_file(self, path: str) -> None:
        try:
            spec = composition.load(path)
        except (OSError, ValueError) as e:
            QMessageBox.warning(self, "Open composition", f"Couldn't open {Path(path).name}: {e}")
            return
        self._remember_dir(path)
        self.preset_box.setCurrentIndex(0)
        self.delete_preset_button.setEnabled(False)
        self.set_spec(spec)
        self.status.setText(f"Opened {Path(path).name}.")

    EXPORT_FORMATS = {
        f"PNG image, printed size ({core.W}×{core.SH}) (*.png)": 1,
        f"PNG image, enlarged 4× ({core.W * 4}×{core.SH * 4}) (*.png)": 4,
    }

    def export_image(self) -> None:
        spec = self.spec()
        if not (spec.text or spec.qr or spec.image_path):
            self.status.setText("Nothing to export.")
            return
        path, chosen = QFileDialog.getSaveFileName(
            None, "Export image", self._suggested_name(".png"), ";;".join(self.EXPORT_FORMATS))
        if not path:
            return
        if not path.lower().endswith(".png"):
            path += ".png"
        try:
            core.export_png(spec, path, self.EXPORT_FORMATS.get(chosen, 1))
        except Exception as e:  # bad image path etc., as in the preview
            QMessageBox.warning(self, "Export image", f"Couldn't export the image: {e}")
            return
        self._remember_dir(path)
        self.status.setText(f"Exported {Path(path).name}.")

    def refresh_preview(self) -> None:
        spec = self.spec()
        try:
            bitmap = core.to_bitmap(core.render(spec)).convert("L")
        except Exception as e:  # bad image path etc. — show it instead of crashing
            self.status.setText(f"Preview error: {e}")
            return
        self.status.setText(self._layout_hint(spec))
        tint = self.active_theme.preview_tint if self.active_theme else None
        if tint:  # cosmetic: the theme colours the preview; the printed label stays black on white
            rgb = ImageOps.colorize(bitmap, black=tint[0], white=tint[1])
            qimg = QImage(rgb.tobytes(), core.W, core.H, core.W * 3, QImage.Format_RGB888).copy()
        else:
            qimg = QImage(bitmap.tobytes(), core.W, core.H, core.W, QImage.Format_Grayscale8).copy()
        pix = QPixmap.fromImage(qimg).scaled(
            core.W * PREVIEW_SCALE, core.H * PREVIEW_SCALE, Qt.KeepAspectRatio, Qt.FastTransformation
        )
        # Shade the gap below the sticker so it's obvious nothing there gets printed.
        painter = QPainter(pix)
        gap = QRect(0, core.SH * PREVIEW_SCALE, pix.width(), pix.height() - core.SH * PREVIEW_SCALE)
        painter.fillRect(gap, QColor(0, 0, 0, 40))
        painter.setPen(QColor(120, 120, 120))
        painter.drawRect(0, 0, pix.width() - 1, core.SH * PREVIEW_SCALE - 1)
        font = painter.font()
        font.setPointSize(8)
        painter.setFont(font)
        painter.drawText(gap, Qt.AlignCenter, "gap between stickers, not printed")  # preview only: exports and prints never see it
        painter.end()
        self.preview.setPixmap(pix)

    @staticmethod
    def _layout_hint(spec: core.LabelSpec) -> str:
        """The text and QR code are silently dropped by the default "Image only" layout: say so, and where to change it."""
        if spec.image_path and spec.image_layout == "only" and (spec.text or spec.qr):
            what = "text and QR code aren't" if spec.text and spec.qr else ("text isn't" if spec.text else "QR code isn't")
            return f"The {what} printed: the layout is “Image only”. Choose another layout on the Image tab."
        return ""

    def paste_image_from_clipboard(self) -> None:
        if self.content.paste_image():
            self.status.setText("Pasted the image from the clipboard.")
        else:
            self.status.setText("There is no image on the clipboard.")

    def copy_label_image(self) -> None:
        spec = self.spec()
        if not (spec.text or spec.qr or spec.image_path):
            self.status.setText("Nothing to copy.")
            return
        try:
            bitmap = core.label_bitmap(spec).convert("L")
        except Exception as e:  # bad image path etc., as in the preview
            self.status.setText(f"Couldn't copy the label: {e}")
            return
        QApplication.clipboard().setImage(QImage(bitmap.tobytes(), core.W, core.SH, core.W, QImage.Format_Grayscale8).copy())
        self.status.setText("Copied the label to the clipboard.")

    def print_now(self) -> None:
        spec = self.spec()
        if not (spec.text or spec.qr or spec.image_path):
            self.status.setText("Nothing to print.")
            return
        self.print_button.setEnabled(False)
        self.print_action.setEnabled(False)
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            problems = core.print_label(spec)
        except Exception as e:  # PrinterError, or a bad image path / oversized QR raised while rendering
            QMessageBox.critical(self, "Print failed", str(e))
            self.status.setText(str(e))
        else:
            self.status.setText("Printer: " + ", ".join(problems) if problems else "Sent.")
        finally:
            QApplication.restoreOverrideCursor()
            self.print_button.setEnabled(True)
            self.print_action.setEnabled(True)


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
