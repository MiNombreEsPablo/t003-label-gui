"""Optional looks for the window: a `Theme` is a bag of colours/shapes that one stylesheet template fills in.

Pure Qt stylesheet plus one custom banner widget, so choosing "System" is just clearing the stylesheet. The built-ins are
`Y2K_BLUE` (iMac-G3 candy plastic, gel buttons, LED checkboxes, chrome bezels), its `Y2K_PINK` variant and `GUNMETAL` (gunmetal bevels, black LCD fields,
lime text).
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import QWidget

ASSETS = Path(__file__).with_name("assets")


def _vgrad(*stops: str) -> str:
    n = len(stops) - 1
    return "qlineargradient(x1:0, y1:0, x2:0, y2:1, " + ", ".join(f"stop:{i / n:g} {c}" for i, c in enumerate(stops)) + ")"


def _gel(top: str, mid: str, low: str, bottom: str) -> str:
    """The signature 1999 gel button: a bright top half, a hard seam at the middle and a glowing lower half."""
    return (
        "qlineargradient(x1:0, y1:0, x2:0, y2:1, "
        f"stop:0 {top}, stop:0.48 {mid}, stop:0.5 {low}, stop:1 {bottom})"
    )


@dataclass(frozen=True)
class BannerStyle:
    stops: tuple[str, str, str]  # plate gradient, top to bottom
    outline: str
    radius: int
    gloss: bool  # candy highlight over the top half
    bevel: str | None  # 1px highlight just inside the plate (flat/metal looks)
    font: str
    size: int
    weight: int
    spacing: float
    color: str
    shadow: str | None  # hard drop shadow behind the title


@dataclass(frozen=True)
class Theme:
    key: str
    title: str
    font: str
    text: str
    link: str  # hyperlinks in rich-text labels
    edge: str  # outlines and separators
    bevel_hi: str  # raised controls: top/left edge ...
    bevel_lo: str  # ... bottom/right edge (same as hi for flat looks)
    inset_hi: str  # sunken fields: top/left edge ...
    inset_lo: str  # ... bottom/right edge
    window_bg: str
    panel_bg: str  # tab pane and group boxes
    btn: str
    btn_hot: str
    btn_down: str
    btn_off: str
    btn_hover_border: str  # declarations, may be empty
    dis_text: str
    dis_border: str  # border-color value
    default_bg: str  # the Print button
    default_bg_down: str
    default_text: str
    default_border: str  # declarations
    default_hover: str  # declarations
    default_dis_text: str
    default_dis_border: str
    input_bg: str
    input_text: str
    input_dis_bg: str
    focus_border: str  # declarations
    select_bg: str
    select_text: str
    tab_unselected_text: str
    tab_selected_bg: str  # equal to the top of panel_bg so tab and pane read as one piece
    led_on: str
    led_off: str
    led_on_border: str
    led_dis: str
    led_size: int
    led_radius: int
    scroll_bg: str
    scroll_line: str
    scroll_handle: str
    bezel_bg: str
    bezel_border: str
    screen_border: str
    status: str
    tooltip_bg: str
    tooltip_text: str
    tooltip_border: str
    menu_bg: str
    dialog_bg: str
    r_ctl: int  # inputs
    r_btn: int
    r_default: int
    r_pane: int
    r_tab: int
    r_title: int
    r_bezel: int
    r_menu: int
    r_item: int
    arrow: str  # asset suffix: arrow-down{suffix}.png
    banner: BannerStyle
    slider_fill: str = ""  # the filled part of a slider (default: the selection colour)
    slider_handle: str = ""  # a slider's handle (default: the button look)
    tab_accent: str = ""  # colour of the selected/hovered tab's top edge (an XP-style cue), or none
    font_pt: int = 10  # pixel fonts are only crisp at their design size
    preview_tint: tuple[str, str] | None = None  # (ink, paper): colour the label preview (cosmetic; prints stay black on white)

    @property
    def screen_bg(self) -> str:
        return self.preview_tint[1] if self.preview_tint else "#ffffff"

    def raised(self, width: int = 2) -> str:
        return f"border: {width}px solid {self.bevel_lo}; border-color: {self.bevel_hi} {self.bevel_lo} {self.bevel_lo} {self.bevel_hi};"

    def inset(self, width: int = 2) -> str:
        return f"border: {width}px solid {self.inset_lo}; border-color: {self.inset_hi} {self.inset_lo} {self.inset_lo} {self.inset_hi};"


_BLUE_PANEL = "qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ffffff, stop:1 #e3f3ff)"
Y2K_BLUE = Theme(
    key="y2k-blue", title="Y2K Blue", font='"Verdana", "DejaVu Sans"', text="#0b2a63", link="#1a5fb4", edge="#3b7fc4",
    bevel_hi="#3b7fc4", bevel_lo="#3b7fc4", inset_hi="#3b7fc4", inset_lo="#3b7fc4",
    window_bg="qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #f4fcff, stop:0.6 #d4edff, stop:1 #aad8f7)",
    panel_bg=_BLUE_PANEL,
    btn=_gel("#ffffff", "#d7edff", "#a9d6fb", "#e2f4ff"),
    btn_hot=_gel("#ffffff", "#e6f4ff", "#bfe3ff", "#f0fbff"),
    btn_down=_gel("#8cc4f0", "#a9d6fb", "#d7edff", "#ffffff"),
    btn_off=_gel("#f4f4f6", "#e6e8ec", "#d4d8de", "#eceef2"),
    btn_hover_border="border-color: #1ea0f0;",
    dis_text="#8da2bb", dis_border="#aebfd3",
    default_bg=_gel("#fff2c6", "#ffd27a", "#ff9d1e", "#ffc65c"),
    default_bg_down=_gel("#ff9d1e", "#ffb347", "#ffd27a", "#fff2c6"),
    default_text="#5a2a00", default_border="border: 2px solid #c26a00;", default_hover="border-color: #ff8a00;",
    default_dis_text="#6f7c8c", default_dis_border="#c9b48d",
    input_bg="#ffffff", input_text="#0b2a63", input_dis_bg="#eef2f7",
    focus_border="border-color: #ff8a00;", select_bg="#1ea0f0", select_text="#ffffff",
    tab_unselected_text="#3a6aa8", tab_selected_bg="#ffffff",
    led_on="qradialgradient(cx:0.35, cy:0.3, radius:0.9, fx:0.35, fy:0.3, stop:0 #eaffd0, stop:0.45 #52e04a, stop:1 #14852a)",
    led_off="qradialgradient(cx:0.35, cy:0.3, radius:0.9, fx:0.35, fy:0.3, stop:0 #ffffff, stop:1 #bcd3ea)",
    led_on_border="#14852a", led_dis="#e4e9f0", led_size=16, led_radius=4,
    scroll_bg="#e4f3ff", scroll_line="#9cc7ee",
    scroll_handle="qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ffffff, stop:0.5 #a9d6fb, stop:1 #d9f0ff)",
    bezel_bg="qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ffffff, stop:0.45 #dfe7f2, stop:0.55 #b9c6d8, stop:1 #8d9db3)",
    bezel_border="3px solid #6b7c95", screen_border="3px solid #3a4a63", status="#14602a",
    tooltip_bg="#fff6a8", tooltip_text="#0b2a63", tooltip_border="#c9a400",
    menu_bg="#ffffff", dialog_bg="#eaf7ff",
    r_ctl=9, r_btn=13, r_default=16, r_pane=12, r_tab=12, r_title=10, r_bezel=18, r_menu=8, r_item=6,
    arrow="", tab_accent="#ffa31a",
    banner=BannerStyle(
        stops=("#7fe3ff", "#1ea0f0", "#0b57d0"), outline="#0b3a8c", radius=22, gloss=True, bevel=None,
        font="Orbitron", size=15, weight=QFont.Black, spacing=1.5, color="#ffffff", shadow="#062a6b",
    ),
)

# Bubblegum variant of the same candy plastic: only colours differ. Plum replaces navy, and the Print button goes grape
# purple because the blue theme's orange would fight the pink.
Y2K_PINK = replace(
    Y2K_BLUE, key="y2k-pink", title="Y2K Pink", text="#5a0f3d", link="#b0156f", edge="#c2468f",
    bevel_hi="#c2468f", bevel_lo="#c2468f", inset_hi="#c2468f", inset_lo="#c2468f",
    window_bg="qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #fff5fb, stop:0.6 #ffdcef, stop:1 #ffb6df)",
    panel_bg="qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ffffff, stop:1 #ffeaf5)",
    btn=_gel("#ffffff", "#ffe3f2", "#ffb3dc", "#ffecf7"),
    btn_hot=_gel("#ffffff", "#ffeef8", "#ffc7e6", "#fff4fb"),
    btn_down=_gel("#ff9ed3", "#ffb3dc", "#ffe3f2", "#ffffff"),
    btn_off=_gel("#f7f4f6", "#ece8eb", "#dcd5da", "#f1edf0"),
    btn_hover_border="border-color: #ff4fa8;",
    dis_text="#b58aa3", dis_border="#e3c2d5",
    default_bg=_gel("#f1e1ff", "#cfa6ff", "#8f45f2", "#bd92ff"),
    default_bg_down=_gel("#8f45f2", "#a869ff", "#cfa6ff", "#f1e1ff"),
    default_text="#2e0a5e", default_border="border: 2px solid #6a24c9;", default_hover="border-color: #a56bff;",
    default_dis_text="#7c6a78", default_dis_border="#cdb5c6",
    input_text="#5a0f3d", input_dis_bg="#fbf0f6",
    focus_border="border-color: #12b5b0;", select_bg="#ff4fa8",
    tab_unselected_text="#a8467f",
    led_off="qradialgradient(cx:0.35, cy:0.3, radius:0.9, fx:0.35, fy:0.3, stop:0 #ffffff, stop:1 #f0c4dc)",
    led_dis="#f3e3ec",
    scroll_bg="#ffeaf5", scroll_line="#f0a6cf",
    scroll_handle="qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ffffff, stop:0.5 #ffb3dc, stop:1 #ffe3f2)",
    bezel_bg="qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #fff3fa, stop:0.45 #ffc9e6, stop:0.55 #ff9fd2, stop:1 #d4579f)",
    bezel_border="3px solid #b03a80", screen_border="3px solid #6b1f4d", status="#1b6a3a",
    tooltip_text="#5a0f3d", menu_bg="#ffffff", dialog_bg="#fff0f8", arrow="-plum", tab_accent="#8f45f2",
    banner=BannerStyle(
        stops=("#ffb3de", "#ff4fa8", "#c2187a"), outline="#8a1259", radius=22, gloss=True, bevel=None,
        font="Orbitron", size=15, weight=QFont.Black, spacing=1.5, color="#ffffff", shadow="#6d0e48",
    ),
)

_GM_PANEL = _vgrad("#3a3d4e", "#2c2e3c")
GUNMETAL = Theme(
    key="gunmetal", title="Gunmetal", font='"Arial", "Liberation Sans", "DejaVu Sans"', text="#c8d0e0", link="#00e000", edge="#0d0e14",
    bevel_hi="#9ba0b8", bevel_lo="#14151d", inset_hi="#0d0e14", inset_lo="#7c819a",
    window_bg=_vgrad("#3d4052", "#262835"),
    panel_bg=_GM_PANEL,
    btn=_vgrad("#8d92aa", "#565a70"),
    btn_hot=_vgrad("#a0a5bd", "#626780"),
    btn_down=_vgrad("#3f4356", "#5a5e74"),
    btn_off=_vgrad("#3e4152", "#313444"),
    btn_hover_border="",
    dis_text="#6b7088", dis_border="#4a4e62 #14151d #14151d #4a4e62",
    default_bg=_vgrad("#8d92aa", "#565a70"),
    default_bg_down=_vgrad("#3f4356", "#5a5e74"),
    default_text="#7dff7d",
    default_border="border: 2px solid #14151d; border-color: #b9bed4 #14151d #14151d #b9bed4;",
    default_hover="border-color: #d8ffd8 #0a3a0a #0a3a0a #d8ffd8;",
    default_dis_text="#6b7088", default_dis_border="#4a4e62 #14151d #14151d #4a4e62",
    input_bg="#000000", input_text="#00e000", input_dis_bg="#101218",
    focus_border="border-color: #00a000 #00e000 #00e000 #00a000;", select_bg="#0000c6", select_text="#ffffff",
    tab_unselected_text="#8e94ac", tab_selected_bg="#3a3d4e",
    led_on="qradialgradient(cx:0.4, cy:0.35, radius:0.8, fx:0.4, fy:0.35, stop:0 #d8ffd8, stop:0.5 #2cf02c, stop:1 #0a7a0a)",
    led_off="qradialgradient(cx:0.4, cy:0.35, radius:0.8, fx:0.4, fy:0.35, stop:0 #2f3a2f, stop:1 #101810)",
    led_on_border="#06400a", led_dis="#22252f", led_size=14, led_radius=3,
    scroll_bg="#14151d", scroll_line="#0d0e14",
    scroll_handle=_vgrad("#8d92aa", "#565a70"),
    bezel_bg=_vgrad("#2a2c39", "#1b1c26"),
    bezel_border="3px solid #0d0e14", screen_border="3px solid #000000", status="#5bff5b",
    tooltip_bg="#000000", tooltip_text="#00e000", tooltip_border="#7c819a",
    menu_bg="#2c2e3c", dialog_bg="#2f3242",
    r_ctl=2, r_btn=2, r_default=2, r_pane=3, r_tab=3, r_title=2, r_bezel=4, r_menu=0, r_item=0,
    arrow="-lcd", slider_fill="#00a800",
    banner=BannerStyle(
        stops=("#7a7f96", "#4c5068", "#2f3243"), outline="#0d0e14", radius=3, gloss=False, bevel="#aab0c8",
        font="VT323", size=26, weight=QFont.Normal, spacing=2.0, color="#00e000", shadow="#003800",
    ),
)

# A 90s handheld's four shades of olive green, nothing else: flat blocky controls, a pixel font, an inverted Print button.
_D, _M, _L, _P = "#0f380f", "#306230", "#8bac0f", "#9bbc0f"  # darkest, dark, light, lightest (paper)
HANDHELD = Theme(
    key="handheld", title="Handheld", font='"Pixelify Sans", "DejaVu Sans Mono"', text=_D, link=_D, edge=_D,
    bevel_hi=_P, bevel_lo=_D, inset_hi=_M, inset_lo=_P,
    window_bg=_P, panel_bg=_L,
    btn=_L, btn_hot=_P, btn_down="#7a990c", btn_off=_L, btn_hover_border="",
    dis_text="#5c7f10", dis_border="#6b8a12",
    default_bg=_D, default_bg_down=_M, default_text=_P,
    default_border=f"border: 2px solid {_D}; border-color: {_M} {_D} {_D} {_M};",
    default_hover=f"border-color: {_L} {_M} {_M} {_L};",
    default_dis_text="#5c7f10", default_dis_border="#6b8a12",
    input_bg=_P, input_text=_D, input_dis_bg=_L, focus_border=f"border-color: {_D};",
    select_bg=_D, select_text=_P,
    tab_unselected_text=_M, tab_selected_bg=_L,
    led_on=_D, led_off=_P, led_on_border=_D, led_dis=_L, led_size=14, led_radius=0,
    scroll_bg=_L, scroll_line=_M, scroll_handle=_P,
    bezel_bg=_M, bezel_border=f"3px solid {_D}", screen_border=f"3px solid {_D}", status=_D,
    tooltip_bg=_P, tooltip_text=_D, tooltip_border=_D,
    menu_bg=_P, dialog_bg=_L,
    r_ctl=0, r_btn=0, r_default=0, r_pane=0, r_tab=0, r_title=0, r_bezel=10, r_menu=0, r_item=0,
    arrow="-dmg",
    banner=BannerStyle(
        stops=(_M, _D, _D), outline=_D, radius=3, gloss=False, bevel=_L,
        font="Pixelify Sans", size=20, weight=QFont.Bold, spacing=1.0, color=_P, shadow=None,
    ),
    font_pt=11, slider_fill=_M, slider_handle=_D,
    preview_tint=(_D, _P),
)

THEMES: dict[str, Theme] = {t.key: t for t in (Y2K_BLUE, Y2K_PINK, GUNMETAL, HANDHELD)}
DEFAULT_THEME = Y2K_BLUE.key
SYSTEM = "system"  # no stylesheet: whatever the desktop provides


def stylesheet(t: Theme = Y2K_BLUE) -> str:
    arrows = ASSETS.as_posix()
    down, up = f"{arrows}/arrow-down{t.arrow}.png", f"{arrows}/arrow-up{t.arrow}.png"
    return f"""
* {{ font-family: {t.font}; font-size: {t.font_pt}pt; color: {t.text}; }}
QMainWindow {{ background: {t.window_bg}; }}
QWidget#root {{ background: transparent; }}
QLabel {{ background: transparent; }}

QTabWidget::pane {{
    {t.raised()} border-radius: {t.r_pane}px; border-top-left-radius: 0; top: -2px; background: {t.panel_bg};
}}
QGroupBox {{ margin-top: 11px; {t.raised()} border-radius: {t.r_pane}px; background: {t.panel_bg}; }}
QGroupBox::title {{
    subcontrol-origin: margin; subcontrol-position: top left; left: 14px; padding: 1px 12px;
    {t.raised()} border-radius: {t.r_title}px; background: {t.btn}; font-weight: bold;
}}
QTabBar::tab {{
    padding: 5px 16px; margin-right: 3px; font-weight: bold; {t.raised()} border-bottom: none;
    border-top-left-radius: {t.r_tab}px; border-top-right-radius: {t.r_tab}px; background: {t.btn};
}}
QTabBar::tab:!selected {{ margin-top: 3px; color: {t.tab_unselected_text}; background: {t.btn_off}; }}
QTabBar::tab:hover:!selected {{ background: {t.btn_hot}; }}
QTabBar::tab:selected {{ background: {t.tab_selected_bg}; }}  /* same as the top of the pane, so tab and pane read as one piece */

QPushButton {{ padding: 5px 14px; font-weight: bold; {t.raised()} border-radius: {t.r_btn}px; background: {t.btn}; }}
QPushButton:hover {{ background: {t.btn_hot}; {t.btn_hover_border} }}
QPushButton:pressed {{ background: {t.btn_down}; }}
QPushButton:disabled {{ color: {t.dis_text}; border-color: {t.dis_border}; background: {t.btn_off}; }}
QPushButton:default {{
    min-height: 30px; font-size: 13pt; color: {t.default_text}; {t.default_border} border-radius: {t.r_default}px;
    background: {t.default_bg};
}}
QPushButton:default:hover {{ {t.default_hover} }}
QPushButton:default:pressed {{ background: {t.default_bg_down}; }}
QPushButton:default:disabled {{ color: {t.default_dis_text}; border-color: {t.default_dis_border}; background: {t.btn_off}; }}

QLineEdit, QPlainTextEdit, QSpinBox, QComboBox {{
    background: {t.input_bg}; color: {t.input_text}; {t.inset()} border-radius: {t.r_ctl}px; padding: 3px 7px;
    selection-background-color: {t.select_bg}; selection-color: {t.select_text};
}}
QLineEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QComboBox:focus {{ {t.focus_border} }}
QLineEdit:disabled, QSpinBox:disabled, QComboBox:disabled {{ background: {t.input_dis_bg}; color: {t.dis_text}; border-color: {t.dis_border}; }}

QComboBox {{ padding-right: 30px; combobox-popup: 0; }}
QComboBox::drop-down {{
    subcontrol-origin: padding; subcontrol-position: top right; width: 26px;
    border-left: 2px solid {t.edge}; border-top-right-radius: {max(t.r_ctl - 2, 0)}px; border-bottom-right-radius: {max(t.r_ctl - 2, 0)}px;
    background: {t.btn};
}}
QComboBox::down-arrow {{ image: url({down}); width: 12px; height: 8px; }}
QSpinBox {{ padding-right: 26px; }}
QSpinBox QLineEdit {{ border: none; background: transparent; padding: 0; }}
QSpinBox::up-button, QSpinBox::down-button {{
    subcontrol-origin: padding; width: 22px; border-left: 2px solid {t.edge}; background: {t.btn};
}}
QSpinBox::up-button {{ subcontrol-position: top right; border-top-right-radius: {max(t.r_ctl - 2, 0)}px; border-bottom: 1px solid {t.edge}; }}
QSpinBox::down-button {{ subcontrol-position: bottom right; border-bottom-right-radius: {max(t.r_ctl - 2, 0)}px; }}
QSpinBox::up-button:pressed, QSpinBox::down-button:pressed {{ background: {t.btn_down}; }}
QSpinBox::up-arrow {{ image: url({up}); width: 12px; height: 8px; }}
QSpinBox::down-arrow {{ image: url({down}); width: 12px; height: 8px; }}

QSlider::groove:horizontal {{
    height: 6px; margin: 0 8px; background: {t.input_bg}; {t.inset()} border-radius: {min(t.r_ctl, 5)}px;
}}
QSlider::sub-page:horizontal {{ margin: 0 8px; background: {t.slider_fill or t.select_bg}; border-radius: {min(t.r_ctl, 5)}px; }}
QSlider::handle:horizontal {{
    width: 14px; height: 14px; margin: -7px -8px; background: {t.slider_handle or t.btn}; {t.raised()} border-radius: {min(t.r_btn, 9)}px;
}}
QSlider::handle:horizontal:hover {{ background: {t.slider_handle or t.btn_hot}; }}
QSlider::handle:horizontal:pressed {{ background: {t.slider_handle or t.btn_down}; }}
QSlider::groove:horizontal:disabled {{ background: {t.input_dis_bg}; border-color: {t.dis_border}; }}
QSlider::sub-page:horizontal:disabled {{ background: {t.dis_border}; }}
QSlider::handle:horizontal:disabled {{ background: {t.btn_off}; border-color: {t.dis_border}; }}

QCheckBox {{ spacing: 8px; background: transparent; }}
QCheckBox::indicator {{
    width: {t.led_size}px; height: {t.led_size}px; border-radius: {t.led_radius}px; {t.inset()} background: {t.led_off};
}}
QCheckBox::indicator:hover {{ border-color: {t.select_bg}; }}
QCheckBox::indicator:checked {{ border-color: {t.led_on_border}; background: {t.led_on}; }}
QCheckBox::indicator:disabled {{ border-color: {t.dis_border}; background: {t.led_dis}; }}

QAbstractItemView {{
    background: {t.input_bg}; {t.inset()} selection-background-color: {t.select_bg}; selection-color: {t.select_text};
    outline: 0; color: {t.input_text};
}}
QAbstractItemView::item {{ color: {t.input_text}; padding: 3px 6px; min-height: 20px; }}
QAbstractItemView::item:selected {{ background: {t.select_bg}; color: {t.select_text}; }}
QComboBox QAbstractItemView {{ background: {t.input_bg}; color: {t.input_text}; }}
QScrollBar:vertical {{ width: 16px; margin: 0; background: {t.scroll_bg}; border-left: 1px solid {t.scroll_line}; }}
QScrollBar::handle:vertical {{
    min-height: 28px; margin: 1px; {t.raised()} border-radius: {max(t.r_ctl - 2, 0)}px; background: {t.scroll_handle};
}}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

QFrame#bezel {{ border: {t.bezel_border}; border-radius: {t.r_bezel}px; background: {t.bezel_bg}; }}
QLabel#screen {{ border: {t.screen_border}; border-radius: 6px; background: {t.screen_bg}; }}
QLabel#status {{ color: {t.status}; font-weight: bold; }}

QMenuBar {{ background: {t.btn}; border-bottom: 2px solid {t.edge}; }}
QMenuBar::item {{ padding: 4px 12px; background: transparent; border-radius: {t.r_menu}px; }}
QMenuBar::item:selected {{ background: {t.btn_down}; }}
QMenu {{ background: {t.menu_bg}; border: 2px solid {t.edge}; border-radius: {t.r_menu}px; padding: 4px; }}
QMenu::item {{ padding: 5px 22px; border-radius: {t.r_item}px; }}
QMenu::item:selected {{ background: {t.select_bg}; color: {t.select_text}; }}
QToolTip {{ background: {t.tooltip_bg}; color: {t.tooltip_text}; border: 2px solid {t.tooltip_border}; padding: 3px; }}
QMessageBox, QInputDialog {{ background: {t.dialog_bg}; }}
""" + (
        f"QTabBar::tab:selected, QTabBar::tab:hover:!selected {{ border-top-color: {t.tab_accent}; }}\n"
        if t.tab_accent else ""
    )


class Banner(QWidget):
    """Title plate: the app icon mark and the app name, styled by the active theme's `BannerStyle`."""

    TITLE = "T003 LABEL STUDIO"

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(54)
        self._icon = QPixmap(str(ASSETS / "icon-mark.png"))
        self._style = Y2K_BLUE.banner

    def set_style(self, style: BannerStyle) -> None:
        self._style = style
        self.update()

    def paintEvent(self, event) -> None:
        s = self._style
        p = QPainter(self)
        p.setRenderHints(QPainter.Antialiasing | QPainter.TextAntialiasing | QPainter.SmoothPixmapTransform)
        r = QRectF(self.rect()).adjusted(2, 2, -2, -2)
        plate = QPainterPath()
        plate.addRoundedRect(r, s.radius, s.radius)
        body = QLinearGradient(r.topLeft(), r.bottomLeft())
        for at, color in zip((0.0, 0.5, 1.0), s.stops):
            body.setColorAt(at, QColor(color))
        p.fillPath(plate, body)
        if s.gloss:
            gloss = QPainterPath()
            gloss.addRoundedRect(QRectF(r.left() + 4, r.top() + 3, r.width() - 8, r.height() * 0.46), 18, 18)
            shine = QLinearGradient(r.topLeft(), QPointF(r.left(), r.top() + r.height() * 0.5))
            shine.setColorAt(0.0, QColor(255, 255, 255, 230))
            shine.setColorAt(1.0, QColor(255, 255, 255, 40))
            p.fillPath(gloss, shine)
        p.setPen(QPen(QColor(s.outline), 2))
        p.drawPath(plate)
        if s.bevel:
            p.setPen(QPen(QColor(s.bevel), 1))
            p.drawLine(QPointF(r.left() + s.radius, r.top() + 2), QPointF(r.right() - s.radius, r.top() + 2))

        p.drawPixmap(int(r.left() + 8), int(r.top() + 3), 46, 46, self._icon)

        font = QFont(s.font, s.size)
        font.setWeight(s.weight)
        font.setLetterSpacing(QFont.AbsoluteSpacing, s.spacing)
        p.setFont(font)
        text_rect = QRectF(r.left() + 56, r.top(), r.width() - 64, r.height())
        if s.shadow:  # hard drop shadow, the classic WordArt move
            p.setPen(QColor(s.shadow))
            p.drawText(text_rect.translated(2, 2), Qt.AlignVCenter | Qt.AlignLeft, self.TITLE)
        p.setPen(QColor(s.color))
        p.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft, self.TITLE)
