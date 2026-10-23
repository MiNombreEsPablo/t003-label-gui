"""Render the README screenshots by driving the real window off-screen.

    .venv/bin/python packaging/make_screenshots.py

Outputs go to docs/screenshots/ and are committed, so this only runs when the look changes. It uses throwaway
settings and presets, so it never touches (or depends on) your own.
"""
import math
import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["XDG_CONFIG_HOME"] = tempfile.mkdtemp(prefix="t003-shots-config-")

from PIL import Image
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication, QTabWidget

QSettings.setDefaultFormat(QSettings.IniFormat)
QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, tempfile.mkdtemp(prefix="t003-shots-settings-"))

from t003gui import theme  # noqa: E402
from t003gui.app import MainWindow  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "docs" / "screenshots"
SIZE = (1240, 700)


def sample_picture(path: Path) -> None:
    """A shaded sphere on a gradient: smooth tones, so the dither choices are visible."""
    w, h = 384, 224
    pixels = []
    for y in range(h):
        for x in range(w):
            dx, dy = (x - 192) / 90, (y - 112) / 90
            r2 = dx * dx + dy * dy
            if r2 < 1:
                light = max(0.0, -0.5 * dx - 0.6 * dy + 0.62 * math.sqrt(1 - r2))
                pixels.append(int(30 + 215 * light))
            else:
                pixels.append(60 + int(110 * x / w))
    img = Image.new("L", (w, h))
    img.putdata(pixels)
    img.save(path)


def shoot(app: QApplication, window: MainWindow, name: str, tab: int) -> None:
    window.findChild(QTabWidget).setCurrentIndex(tab)
    for _ in range(3):
        app.processEvents()
    window.grab().save(str(OUT / name))
    print("wrote", name)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    app = QApplication(sys.argv)
    app.setApplicationName("T003 Label Studio")
    app.setOrganizationName("t003-label-gui")
    window = MainWindow()
    window.resize(*SIZE)
    window.show()

    window.content.text.setPlainText("NEON\nNIGHTS")
    window.text_panel.font_box.setCurrentText("Orbitron")
    window.text_panel.effect.setCurrentIndex(window.text_panel.effect.findData("neon"))
    window.decoration.border_box.setCurrentIndex(window.decoration.border_box.findData("brackets"))
    for t in theme.THEMES.values():
        window.apply_theme(t.key)
        shoot(app, window, f"theme-{t.key}.png", tab=1)

    picture = Path(tempfile.mkdtemp(prefix="t003-shots-")) / "orb.png"
    sample_picture(picture)
    window.apply_theme("y2k-blue")
    window.set_spec(type(window.spec())(
        text="Glossy\nOrb", font="Righteous", image_path=str(picture), image_layout="left", image_size=45,
        dither="bayer4", contrast=20,
    ))
    shoot(app, window, "image-layout.png", tab=2)
    window.close()


if __name__ == "__main__":
    main()
