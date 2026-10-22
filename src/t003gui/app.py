"""Qt GUI: edit a label, see the exact 1-bit preview, print it."""
from __future__ import annotations

import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from . import core

PREVIEW_SCALE = 2


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("T003 Label Printer")

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
        self.border = QCheckBox("Border")
        self.copies = QSpinBox()
        self.copies.setRange(1, 99)
        self.density = QSpinBox()
        self.density.setRange(0, 15)
        self.density.setValue(7)

        form = QFormLayout()
        form.addRow("Text", self.text)
        form.addRow("QR", self.qr)
        form.addRow("Image", image_row)
        form.addRow("", self.hard_threshold)
        form.addRow("Cutoff", self.threshold)
        form.addRow("", self.border)
        form.addRow("Copies", self.copies)
        form.addRow("Darkness", self.density)

        self.print_button = QPushButton("Print")
        self.print_button.setDefault(True)
        self.print_button.clicked.connect(self.print_now)
        self.status = QLabel("")
        self.status.setWordWrap(True)

        controls = QVBoxLayout()
        controls.addLayout(form)
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
            self.border.toggled,
        ):
            signal.connect(self.refresh_preview)
        self.refresh_preview()

    def spec(self) -> core.LabelSpec:
        return core.LabelSpec(
            text=self.text.toPlainText().strip(),
            qr=self.qr.text().strip(),
            image_path=self.image.text().strip(),
            threshold=self.threshold.value() if self.hard_threshold.isChecked() else None,
            border=self.border.isChecked(),
            copies=self.copies.value(),
            density=self.density.value(),
        )

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
