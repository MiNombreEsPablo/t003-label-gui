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
    assert values(window.text_panel.effect) == list(core.EFFECTS)
    assert values(window.retro.background) == list(core.BACKGROUNDS)
    assert values(window.retro.border_box) == [None, *core.BORDER_STYLES]


def test_font_picker_is_curated_by_default_and_keeps_your_font(window):
    model = window.text_panel.font_box.model()
    rows = [model.item(i).text() for i in range(model.rowCount())]
    assert all(f.family in rows for f in fonts.BUNDLED)
    assert not model.item(0).isEnabled()  # category header
    window.set_spec(core.LabelSpec(text="x", font="Some Installed Font"))
    window.text_panel.all_fonts.setChecked(True)
    assert window.text_panel.font_box.currentText() == "Some Installed Font"
    window.text_panel.all_fonts.setChecked(False)
    assert window.text_panel.font_box.currentText() == "Some Installed Font"


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

    from t003gui import panels

    assert not panels.has_image(drop("/etc/hostname").mimeData())
    assert panels.has_image(drop("/tmp/x.PNG").mimeData())
    assert panels.image_from_mime(drop("/tmp/x.PNG").mimeData()) == "/tmp/x.PNG"


def test_each_panel_round_trips_its_own_slice_of_the_spec(window):
    from dataclasses import fields

    spec = core.LabelSpec(text="hi", qr="q", copies=3, density=9, font="Orbitron", bold=False,
                          italic=True, size=40, align="left", valign="top", effect="shadow", border=True,
                          border_style="double", background="grid", bars=True, dither="bayer8", brightness=-10,
                          contrast=25, gamma=1.8, pixelate=3, mirror=True, flip=True, invert=True)
    window.set_spec(spec)
    assert window.spec() == spec
    seen = [set(p.read()) for p in window.panels]
    assert set().union(*seen) == {f.name for f in fields(core.LabelSpec)}
    assert sum(len(s) for s in seen) == len(set().union(*seen))  # no field is owned by two panels


def test_pasting_a_clipboard_image_sets_the_image_path(window, app):
    from pathlib import Path

    from PySide6.QtGui import QColor, QImage

    img = QImage(20, 10, QImage.Format_RGB32)
    img.fill(QColor("black"))
    app.clipboard().setImage(img)
    assert window.content.paste_image()
    assert Path(window.content.image.text()).exists()
    app.clipboard().clear()
    assert not window.content.paste_image()


def test_tabs_exist(window):
    tabs = window.findChild(QTabWidget)
    assert [tabs.tabText(i) for i in range(tabs.count())] == ["Content", "Text", "Image", "Retro"]


def test_widget_attributes_do_not_shadow_qt_methods(window):
    from PySide6.QtWidgets import QMainWindow

    shadowed = [n for n in vars(window) if callable(getattr(QMainWindow, n, None)) and not callable(vars(window)[n])]
    assert shadowed == [], f"attributes hide Qt methods: {shadowed}"
    assert window.size().width() > 0  # the one that actually bit us


def test_help_menu_and_about_text(window):
    from t003gui import __version__, about

    titles = [a.text() for top in window.menuBar().actions() if top.menu() for a in top.menu().actions()]
    assert any("About" in t for t in titles) and any("updates" in t for t in titles)
    assert f"Version {__version__}" in titles
    html = about.about_html("found", 23)
    assert __version__ in html and "found" in html and about.REPO_URL in html
    assert about.RELEASES_URL.startswith(about.REPO_URL) and about.ISSUES_URL.startswith(about.REPO_URL)


def test_file_menu_actions_exist(window):
    titles = [a.text() for top in window.menuBar().actions() if top.menu() for a in top.menu().actions()]
    for wanted in ("Open composition", "Save composition", "Export image"):
        assert any(wanted in t for t in titles), wanted


def test_save_then_open_a_composition(window, monkeypatch, tmp_path):
    from PySide6.QtWidgets import QFileDialog

    path = str(tmp_path / "mine")  # the suffix is added for the user
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *a, **k: (path, ""))
    window.content.text.setPlainText("keep me")
    window.text_panel.effect.setCurrentIndex(window.text_panel.effect.findData("outline"))
    window.save_composition()
    assert (tmp_path / "mine.t003label").exists() and "Saved" in window.status.text()

    window.content.text.setPlainText("changed")
    window.text_panel.effect.setCurrentIndex(0)
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *a, **k: (path + ".t003label", ""))
    window.open_composition()
    assert window.spec().text == "keep me" and window.spec().effect == "outline"


def test_opening_a_bad_composition_warns_and_changes_nothing(window, monkeypatch, tmp_path):
    from PySide6.QtWidgets import QFileDialog, QMessageBox

    bad = tmp_path / "bad.t003label"
    bad.write_text("nope")
    warned = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: warned.append(a[2]))
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *a, **k: (str(bad), ""))
    window.content.text.setPlainText("untouched")
    window.open_composition()
    assert warned and "bad.t003label" in warned[0] and window.spec().text == "untouched"


def test_export_image_uses_the_chosen_scale(window, monkeypatch, tmp_path):
    from PIL import Image
    from PySide6.QtWidgets import QFileDialog

    window.content.text.setPlainText("Hi")
    big = [f for f, scale in window.EXPORT_FORMATS.items() if scale == 4][0]
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *a, **k: (str(tmp_path / "out"), big))
    window.export_image()
    assert Image.open(tmp_path / "out.png").size == (core.W * 4, core.SH * 4)

    window.content.text.setPlainText("")  # nothing to export
    (tmp_path / "none.png").unlink(missing_ok=True)
    window.export_image()
    assert "Nothing to export" in window.status.text()


def test_dropping_a_composition_file_opens_it(window, tmp_path):
    from PySide6.QtCore import QMimeData, QPointF, Qt, QUrl
    from PySide6.QtGui import QDropEvent

    from t003gui import composition

    path = tmp_path / ("dropped" + composition.SUFFIX)
    composition.save(path, core.LabelSpec(text="from a drop"))
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(path))])
    event = QDropEvent(QPointF(5, 5), Qt.CopyAction, mime, Qt.LeftButton, Qt.NoModifier)
    window.dropEvent(event)
    assert window.spec().text == "from a drop" and "Opened" in window.status.text()


def test_image_panel_is_inactive_until_an_image_is_chosen(window, tmp_path):
    panel = window.image_panel
    assert not panel.dither.isEnabled() and not panel.hint.isHidden()
    window.content.set_image(str(tmp_path / "x.png"))
    assert panel.dither.isEnabled() and panel.hint.isHidden()
    window.content.set_image("")
    assert not panel.dither.isEnabled()


def test_image_panel_modes_and_legacy_threshold(window):
    panel = window.image_panel
    for mode in ("floyd", "bayer4", "bayer8"):
        window.set_spec(core.LabelSpec(dither=mode, brightness=-20, contrast=35, gamma=1.6))
        spec = window.spec()
        assert (spec.dither, spec.threshold, spec.brightness, spec.contrast, spec.gamma) == (mode, None, -20, 35, 1.6)
    window.set_spec(core.LabelSpec(threshold=77))  # older presets/files: just a cutoff
    assert panel.dither.currentData() == "threshold" and window.spec().threshold == 77
    window.set_spec(core.LabelSpec(dither="no-such-mode"))
    assert panel.dither.currentData() == "floyd"
    window.set_spec(core.LabelSpec(brightness=5, pixelate=4, mirror=True, flip=True, invert=True, dither="bayer8"))
    panel.reset_all()
    assert window.spec() == core.LabelSpec()


def test_gamma_box_shows_tenths(window):
    box = window.image_panel.gamma
    box.setValue(16)
    assert box.text() == "1.6" and box.valueFromText("2.5") == 25 and box.valueFromText("junk") == 16

def test_layout_controls_follow_the_image(window, tmp_path):
    content = window.content
    assert not content.image_layout.isEnabled() and not content.image_size.isEnabled()  # no image yet
    content.set_image(str(tmp_path / "x.png"))
    assert content.image_layout.isEnabled() and not content.image_size.isEnabled()  # "image only" has no size
    for layout, sized in (("left", True), ("top", True), ("behind", False), ("only", False)):
        content.image_layout.setCurrentIndex(content.image_layout.findData(layout))
        assert content.image_size.isEnabled() is sized, layout
    content.set_image("")
    assert not content.image_layout.isEnabled()


def test_layout_round_trips_through_the_content_panel(window):
    window.set_spec(core.LabelSpec(image_path="a.png", image_layout="bottom", image_size=65))
    spec = window.spec()
    assert (spec.image_layout, spec.image_size) == ("bottom", 65)
    window.set_spec(core.LabelSpec(image_layout="nonsense", image_size=999))  # clamped / defaulted, never crashes
    spec = window.spec()
    assert (spec.image_layout, spec.image_size) == ("only", 80)
