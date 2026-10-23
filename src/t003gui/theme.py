"""The optional Y2K look: iMac-G3 candy plastic, gel buttons, LED checkboxes, chrome bezels.

Pure Qt stylesheet plus one custom banner widget, so switching back to the platform style is just clearing it.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import QWidget

ASSETS = Path(__file__).with_name("assets")

NAVY = "#0b2a63"
EDGE = "#3b7fc4"
SKY = "#1ea0f0"


def _gel(top: str, mid: str, low: str, bottom: str) -> str:
    """The signature 1999 gel button: a bright top half, a hard seam at the middle and a glowing lower half."""
    return (
        "qlineargradient(x1:0, y1:0, x2:0, y2:1, "
        f"stop:0 {top}, stop:0.48 {mid}, stop:0.5 {low}, stop:1 {bottom})"
    )


GEL = _gel("#ffffff", "#d7edff", "#a9d6fb", "#e2f4ff")
GEL_HOT = _gel("#ffffff", "#e6f4ff", "#bfe3ff", "#f0fbff")
GEL_DOWN = _gel("#8cc4f0", "#a9d6fb", "#d7edff", "#ffffff")
GEL_OFF = _gel("#f4f4f6", "#e6e8ec", "#d4d8de", "#eceef2")
GEL_ORANGE = _gel("#fff2c6", "#ffd27a", "#ff9d1e", "#ffc65c")
GEL_ORANGE_DOWN = _gel("#ff9d1e", "#ffb347", "#ffd27a", "#fff2c6")

LED_OFF = "qradialgradient(cx:0.35, cy:0.3, radius:0.9, fx:0.35, fy:0.3, stop:0 #ffffff, stop:1 #bcd3ea)"
LED_ON = (
    "qradialgradient(cx:0.35, cy:0.3, radius:0.9, fx:0.35, fy:0.3, "
    "stop:0 #eaffd0, stop:0.45 #52e04a, stop:1 #14852a)"
)


def stylesheet() -> str:
    arrows = ASSETS.as_posix()
    return f"""
* {{ font-family: "Verdana", "DejaVu Sans"; font-size: 10pt; color: {NAVY}; }}
QMainWindow {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #f4fcff, stop:0.6 #d4edff, stop:1 #aad8f7);
}}
QWidget#root {{ background: transparent; }}
QLabel {{ background: transparent; }}

QTabWidget::pane {{
    border: 2px solid {EDGE}; border-radius: 12px; top: -2px;
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ffffff, stop:1 #e3f3ff);
}}
QTabBar::tab {{
    padding: 5px 16px; margin-right: 3px; font-weight: bold;
    border: 2px solid {EDGE}; border-bottom: none; border-top-left-radius: 12px; border-top-right-radius: 12px;
    background: {GEL};
}}
QTabBar::tab:!selected {{ margin-top: 3px; color: #3a6aa8; background: {GEL_OFF}; }}
QTabBar::tab:hover:!selected {{ background: {GEL_HOT}; }}
QTabBar::tab:selected {{ background: {_gel("#ffffff", "#ffffff", "#f4faff", "#e3f3ff")}; }}

QPushButton {{
    padding: 5px 14px; font-weight: bold; border: 2px solid {EDGE}; border-radius: 13px; background: {GEL};
}}
QPushButton:hover {{ background: {GEL_HOT}; border-color: {SKY}; }}
QPushButton:pressed {{ background: {GEL_DOWN}; }}
QPushButton:disabled {{ color: #8da2bb; border-color: #aebfd3; background: {GEL_OFF}; }}
QPushButton:default {{
    min-height: 30px; font-size: 13pt; color: #5a2a00; border: 2px solid #c26a00; border-radius: 16px;
    background: {GEL_ORANGE};
}}
QPushButton:default:hover {{ border-color: #ff8a00; }}
QPushButton:default:pressed {{ background: {GEL_ORANGE_DOWN}; }}
QPushButton:default:disabled {{ color: #9a8a70; border-color: #c9b48d; background: {GEL_OFF}; }}

QLineEdit, QPlainTextEdit, QSpinBox, QComboBox {{
    background: #ffffff; border: 2px solid {EDGE}; border-radius: 9px; padding: 3px 7px;
    selection-background-color: {SKY}; selection-color: #ffffff;
}}
QLineEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QComboBox:focus {{ border-color: #ff8a00; }}
QLineEdit:disabled, QSpinBox:disabled {{ background: #eef2f7; color: #8da2bb; border-color: #aebfd3; }}

QComboBox {{ padding-right: 30px; combobox-popup: 0; }}
QComboBox::drop-down {{
    subcontrol-origin: padding; subcontrol-position: top right; width: 26px;
    border-left: 2px solid {EDGE}; border-top-right-radius: 7px; border-bottom-right-radius: 7px; background: {GEL};
}}
QComboBox::down-arrow {{ image: url({arrows}/arrow-down.png); width: 12px; height: 8px; }}
QSpinBox {{ padding-right: 26px; }}
QSpinBox QLineEdit {{ border: none; background: transparent; padding: 0; }}
QSpinBox::up-button, QSpinBox::down-button {{
    subcontrol-origin: padding; width: 22px; border-left: 2px solid {EDGE}; background: {GEL};
}}
QSpinBox::up-button {{ subcontrol-position: top right; border-top-right-radius: 7px; border-bottom: 1px solid {EDGE}; }}
QSpinBox::down-button {{ subcontrol-position: bottom right; border-bottom-right-radius: 7px; }}
QSpinBox::up-button:pressed, QSpinBox::down-button:pressed {{ background: {GEL_DOWN}; }}
QSpinBox::up-arrow {{ image: url({arrows}/arrow-up.png); width: 12px; height: 8px; }}
QSpinBox::down-arrow {{ image: url({arrows}/arrow-down.png); width: 12px; height: 8px; }}

QCheckBox {{ spacing: 8px; background: transparent; }}
QCheckBox::indicator {{
    width: 16px; height: 16px; border-radius: 10px; border: 2px solid {EDGE}; background: {LED_OFF};
}}
QCheckBox::indicator:hover {{ border-color: {SKY}; }}
QCheckBox::indicator:checked {{ border-color: #14852a; background: {LED_ON}; }}
QCheckBox::indicator:disabled {{ border-color: #aebfd3; background: #e4e9f0; }}

QAbstractItemView {{
    background: #ffffff; border: 2px solid {EDGE}; selection-background-color: {SKY}; selection-color: #ffffff;
    outline: 0; color: {NAVY};
}}
QAbstractItemView::item {{ color: {NAVY}; padding: 3px 6px; min-height: 20px; }}
QAbstractItemView::item:selected {{ background: {SKY}; color: #ffffff; }}
QComboBox QAbstractItemView {{ background: #ffffff; color: {NAVY}; }}
QScrollBar:vertical {{ width: 16px; margin: 0; background: #e4f3ff; border-left: 1px solid #9cc7ee; }}
QScrollBar::handle:vertical {{
    min-height: 28px; margin: 1px; border: 2px solid {EDGE}; border-radius: 7px;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ffffff, stop:0.5 #a9d6fb, stop:1 #d9f0ff);
}}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

QFrame#bezel {{
    border: 3px solid #6b7c95; border-radius: 18px;
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ffffff, stop:0.45 #dfe7f2, stop:0.55 #b9c6d8, stop:1 #8d9db3);
}}
QLabel#screen {{ border: 3px solid #3a4a63; border-radius: 6px; background: #ffffff; }}
QLabel#status {{ color: #14602a; font-weight: bold; }}

QMenuBar {{ background: {GEL}; border-bottom: 2px solid {EDGE}; }}
QMenuBar::item {{ padding: 4px 12px; background: transparent; border-radius: 8px; }}
QMenuBar::item:selected {{ background: {GEL_DOWN}; }}
QMenu {{ background: #ffffff; border: 2px solid {EDGE}; border-radius: 8px; padding: 4px; }}
QMenu::item {{ padding: 5px 22px; border-radius: 6px; }}
QMenu::item:selected {{ background: {SKY}; color: #ffffff; }}
QToolTip {{ background: #fff6a8; color: {NAVY}; border: 2px solid #c9a400; padding: 3px; }}
QMessageBox, QInputDialog {{ background: #eaf7ff; }}
"""


class Banner(QWidget):
    """Chrome-and-aqua title plate: the app icon, a gloss highlight and WordArt-ish lettering."""

    TITLE = "T003 LABEL STUDIO"

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(54)
        self._icon = QPixmap(str(ASSETS / "icon-mark.png"))

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHints(QPainter.Antialiasing | QPainter.TextAntialiasing | QPainter.SmoothPixmapTransform)
        r = QRectF(self.rect()).adjusted(2, 2, -2, -2)
        plate = QPainterPath()
        plate.addRoundedRect(r, 22, 22)
        body = QLinearGradient(r.topLeft(), r.bottomLeft())
        body.setColorAt(0.0, QColor("#7fe3ff"))
        body.setColorAt(0.5, QColor("#1ea0f0"))
        body.setColorAt(1.0, QColor("#0b57d0"))
        p.fillPath(plate, body)
        gloss = QPainterPath()
        gloss.addRoundedRect(QRectF(r.left() + 4, r.top() + 3, r.width() - 8, r.height() * 0.46), 18, 18)
        shine = QLinearGradient(r.topLeft(), QPointF(r.left(), r.top() + r.height() * 0.5))
        shine.setColorAt(0.0, QColor(255, 255, 255, 230))
        shine.setColorAt(1.0, QColor(255, 255, 255, 40))
        p.fillPath(gloss, shine)
        p.setPen(QPen(QColor("#0b3a8c"), 2))
        p.drawPath(plate)

        p.drawPixmap(int(r.left() + 8), int(r.top() + 3), 46, 46, self._icon)

        font = QFont("Orbitron", 15)
        font.setWeight(QFont.Black)
        font.setLetterSpacing(QFont.AbsoluteSpacing, 1.5)
        p.setFont(font)
        text_rect = QRectF(r.left() + 56, r.top(), r.width() - 64, r.height())
        p.setPen(QColor("#062a6b"))  # hard drop shadow, the classic WordArt move
        p.drawText(text_rect.translated(2, 2), Qt.AlignVCenter | Qt.AlignLeft, self.TITLE)
        p.setPen(QColor("#ffffff"))
        p.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft, self.TITLE)
