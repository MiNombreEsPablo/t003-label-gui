import pytest
from PySide6.QtWidgets import QApplication, QTabWidget

from t003gui import core, fonts
from t003gui.app import MainWindow


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def window(app):
    w = MainWindow()
    w.show()
    app.processEvents()
    yield w
    w.close()
    app.setStyleSheet("")


def test_spec_round_trips_every_control(window):
    spec = core.LabelSpec(
        text="電脳\nCITY", qr="x", font="DotGothic16", bold=False, italic=True, size=40, align="right",
        valign="bottom", effect="neon", border=True, border_style="chamfer", background="circuit", bars=True,
        copies=3, density=9, threshold=120,
    )
    window.set_spec(spec)
    assert window.spec() == spec
    window.set_spec(core.LabelSpec(text="x"))
    plain = window.spec()
    assert not plain.border and plain.effect == "none" and plain.background == "none" and plain.font == "DejaVu Sans"


def test_choice_boxes_match_the_core_lists(window):
    values = lambda box: [box.itemData(i) for i in range(box.count())]
    assert values(window.effect) == list(core.EFFECTS)
    assert values(window.background) == list(core.BACKGROUNDS)
    assert values(window.border_box) == [None, *core.BORDER_STYLES]


def test_font_picker_is_curated_by_default_and_keeps_your_font(window):
    model = window.font_box.model()
    rows = [model.item(i).text() for i in range(model.rowCount())]
    assert all(f.family in rows for f in fonts.BUNDLED)
    assert not model.item(0).isEnabled()  # category header
    window.set_spec(core.LabelSpec(text="x", font="Some Installed Font"))
    window.all_fonts.setChecked(True)
    assert window.font_box.currentText() == "Some Installed Font"
    window.all_fonts.setChecked(False)
    assert window.font_box.currentText() == "Some Installed Font"


def test_theme_choice_applies_and_clears_the_stylesheet(window, app):
    for key in ("y2k-blue", "y2k-pink", "gunmetal"):
        window.apply_theme(key)
        assert "qlineargradient" in window.styleSheet() and app.styleSheet() == ""
        assert window.banner.isVisibleTo(window) and window.theme_actions[key].isChecked()
    window.apply_theme("system")
    assert window.styleSheet() == "" and not window.banner.isVisibleTo(window)
    assert window.theme_actions["system"].isChecked()


def test_every_theme_stylesheet_references_assets_that_exist(window):
    import re

    from t003gui import theme

    for t in theme.THEMES.values():
        for path in re.findall(r"url\(([^)]+)\)", theme.stylesheet(t)):
            assert path.startswith(theme.ASSETS.as_posix()) and theme.Path(path).exists(), path


def test_old_y2k_setting_is_migrated(window):
    from PySide6.QtCore import QSettings

    settings = QSettings()
    settings.remove("theme")
    settings.setValue("y2k", False)
    assert window._saved_theme() == "system"
    settings.setValue("y2k", True)
    assert window._saved_theme() == "y2k-blue"
    settings.remove("y2k")
    settings.remove("theme")
    assert window._saved_theme() == "y2k-blue"
    settings.setValue("theme", "no-such-theme")
    assert window._saved_theme() == "y2k-blue"


def test_dropping_only_accepts_images(window):
    from PySide6.QtCore import QMimeData, QPointF, Qt, QUrl
    from PySide6.QtGui import QDropEvent

    keep = []  # QDropEvent does not own its QMimeData; letting it be collected leaves a dangling pointer

    def drop(path):
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(path)])
        keep.append(mime)
        return QDropEvent(QPointF(5, 5), Qt.CopyAction, mime, Qt.LeftButton, Qt.NoModifier)

    assert window._dropped_image(drop("/etc/hostname")) is None
    assert window._dropped_image(drop("/tmp/x.PNG")) == "/tmp/x.PNG"


def test_pasting_a_clipboard_image_sets_the_image_path(window, app):
    from pathlib import Path

    from PySide6.QtGui import QColor, QImage

    img = QImage(20, 10, QImage.Format_RGB32)
    img.fill(QColor("black"))
    app.clipboard().setImage(img)
    assert window.paste_image()
    assert Path(window.image.text()).exists()
    app.clipboard().clear()
    assert not window.paste_image()


def test_tabs_exist(window):
    tabs = window.findChild(QTabWidget)
    assert [tabs.tabText(i) for i in range(tabs.count())] == ["Content", "Text", "Retro"]


def test_widget_attributes_do_not_shadow_qt_methods(window):
    from PySide6.QtWidgets import QMainWindow

    shadowed = [n for n in vars(window) if callable(getattr(QMainWindow, n, None)) and not callable(vars(window)[n])]
    assert shadowed == [], f"attributes hide Qt methods: {shadowed}"
    assert window.size().width() > 0  # the one that actually bit us
