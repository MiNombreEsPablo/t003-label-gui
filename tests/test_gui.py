import pytest
from PIL import Image

pytest.importorskip("PySide6")  # the window is the optional [gui] extra
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
    assert values(window.decoration.background) == list(core.BACKGROUNDS)
    assert values(window.decoration.border_box) == [None, *core.BORDER_STYLES]


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
    for key in ("y2k-blue", "y2k-pink", "gunmetal", "handheld"):
        window.apply_theme(key)
        assert "QMainWindow" in window.styleSheet() and app.styleSheet() == ""
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
    assert [tabs.tabText(i) for i in range(tabs.count())] == ["Content", "Font", "Image", "Decoration", "Doodle"]


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


def test_dragging_a_slider_changes_the_spec_and_the_preview(window, tmp_path):
    from PIL import Image

    art = tmp_path / "grey.png"
    Image.new("L", (100, 100), 128).save(art)
    window.content.set_image(str(art))
    panel = window.image_panel
    before = window.preview.pixmap().toImage()
    panel.brightness.slider.setValue(panel.brightness.slider.maximum())  # all the way up
    assert window.spec().brightness == 100
    assert window.preview.pixmap().toImage() != before  # the preview followed the drag
    panel.brightness.slider.reset_requested.emit()  # double-click
    assert window.spec().brightness == 0


def test_sliders_dim_with_the_rest_of_the_image_panel(window):
    panel = window.image_panel
    sliders = (panel.brightness, panel.contrast, panel.gamma, panel.pixelate)
    assert all(not s.slider.isEnabled() and not s.spin.isEnabled() for s in sliders)  # no image yet
    window.content.set_image("x.png")
    assert all(s.slider.isEnabled() and s.spin.isEnabled() for s in sliders)
    window.image_panel.dither.setCurrentIndex(window.image_panel.dither.findData("threshold"))
    assert panel.cutoff.slider.isEnabled()  # the cutoff joins in when the hard cutoff is chosen


def test_gamma_slider_covers_the_whole_range(window):
    gamma = window.image_panel.gamma
    window.set_spec(core.LabelSpec(gamma=0.3))
    assert window.spec().gamma == 0.3 and gamma.slider.value() == 0
    window.set_spec(core.LabelSpec(gamma=3.0))
    assert window.spec().gamma == 3.0 and gamma.slider.value() == gamma.slider.maximum()


def test_every_neutral_handle_sits_at_the_same_spot(window):
    """Brightness 0, contrast 0 and gamma 1.0 are all "no change": their handles must line up, dead centre."""
    window.set_spec(core.LabelSpec())
    panel = window.image_panel
    fractions = {round(c.slider.value() / c.slider.maximum(), 6) for c in (panel.brightness, panel.contrast, panel.gamma)}
    assert fractions == {0.5}


def test_gamma_box_shows_tenths(window):
    box = window.image_panel.gamma.spin
    box.setValue(16)
    assert box.text() == "1.6" and box.valueFromText("2.5") == 25 and box.valueFromText("junk") == 16


def test_handheld_theme_tints_the_preview_but_not_the_print(window):
    from t003gui import theme

    assert theme.HANDHELD.preview_tint == ("#0f380f", "#9bbc0f")
    window.content.text.setPlainText("")
    window.apply_theme("handheld")
    assert window.preview.pixmap().toImage().pixelColor(4, 4).name() == "#9bbc0f"  # paper
    window.apply_theme("y2k-blue")
    assert window.preview.pixmap().toImage().pixelColor(4, 4).name() == "#ffffff"
    window.apply_theme("system")
    assert window.preview.pixmap().toImage().pixelColor(4, 4).name() == "#ffffff"
    # the printed bitmap never depends on the theme
    before = core.to_bitmap(core.render(window.spec())).tobytes()
    window.apply_theme("handheld")
    assert core.to_bitmap(core.render(window.spec())).tobytes() == before


def test_every_theme_is_complete_and_selectable(window):
    from t003gui import theme

    assert set(theme.THEMES) == {"y2k-blue", "y2k-pink", "gunmetal", "handheld"}
    for t in theme.THEMES.values():
        assert t.title and window.theme_actions[t.key].text() == t.title
        assert "-" not in str(t.r_ctl) and t.font_pt >= 9  # no negative radii or tiny type


def test_layout_controls_follow_the_image(window, tmp_path):
    panel = window.image_panel
    assert not panel.image_layout.isEnabled() and not panel.image_size.isEnabled()  # no image yet
    window.content.set_image(str(tmp_path / "x.png"))
    assert panel.image_layout.isEnabled() and not panel.image_size.isEnabled()  # "image only" has no size
    for layout, sized in (("left", True), ("top", True), ("behind", False), ("only", False)):
        panel.image_layout.setCurrentIndex(panel.image_layout.findData(layout))
        assert panel.image_size.isEnabled() is sized, layout
    window.content.set_image("")
    assert not panel.image_layout.isEnabled() and not panel.image_size.isEnabled()


def test_layout_round_trips_through_the_image_panel(window):
    window.set_spec(core.LabelSpec(image_path="a.png", image_layout="bottom", image_size=65))
    spec = window.spec()
    assert (spec.image_layout, spec.image_size) == ("bottom", 65)
    window.set_spec(core.LabelSpec(image_layout="nonsense", image_size=999))  # clamped / defaulted, never crashes
    spec = window.spec()
    assert (spec.image_layout, spec.image_size) == ("only", 80)
    window.image_panel.reset_all()  # the Image tab's Reset brings the layout back too
    assert window.spec() == core.LabelSpec()


def test_preview_explains_the_gap_strip(window):
    assert f"{core.W} × {core.SH} dots" in window.preview.toolTip()
    img = window.preview.pixmap().toImage()
    strip_top = core.SH * 2  # the preview is drawn at 2x
    colours = {img.pixelColor(x, y).rgb() for x in range(img.width()) for y in range(strip_top + 2, img.height() - 2)}
    assert len(colours) > 2  # shaded background plus the caption's text, not a blank grey bar
    # the caption is preview-only: the exported bitmap has nothing below the sticker
    assert set(core.to_bitmap(core.render(window.spec())).crop((0, core.SH, core.W, core.H)).tobytes()) == {255}


@pytest.mark.parametrize("key", ["y2k-blue", "gunmetal", "handheld", "system"])
def test_fields_line_up_across_all_panels(window, app, key):
    """The Output box and every tab share one label column, so no field starts a few pixels left of another."""
    from PySide6.QtCore import QPoint

    window.apply_theme(key)
    window.resize(window.sizeHint())
    tabs = window.findChild(QTabWidget)
    fields = {0: window.content.text, 1: window.text_panel.font_box, 2: window.image_panel.dither,
              3: window.decoration.border_box}
    starts = set()
    for index, field in fields.items():
        tabs.setCurrentIndex(index)
        app.processEvents()
        starts.add(field.mapTo(window, QPoint(0, 0)).x())
    starts.add(window.output.copies.mapTo(window, QPoint(0, 0)).x())
    # exact for our themes; the platform style draws tab panes and group boxes with frames a pixel apart
    assert max(starts) - min(starts) <= (2 if key == "system" else 0), starts


def test_an_added_image_can_be_removed_again(window, tmp_path):
    from PIL import Image

    art = tmp_path / "art.png"
    Image.new("L", (50, 50), 0).save(art)
    window.content.text.setPlainText("Caption")
    window.content.set_image(str(art))
    with_image = core.to_bitmap(core.render(window.spec())).tobytes()
    assert window.content.image.isClearButtonEnabled()  # the visible x in the field
    window.content.image.clear()  # what clicking it does
    spec = window.spec()
    assert spec.image_path == "" and spec.text == "Caption"
    assert not window.image_panel.dither.isEnabled() and not window.image_panel.image_layout.isEnabled()
    assert core.to_bitmap(core.render(spec)).tobytes() != with_image  # back to the text-only label


def _menu_texts(window):
    return {top.text().replace("&", ""): [a.text().replace("&", "") for a in top.menu().actions() if not a.isSeparator()]
            for top in window.menuBar().actions() if top.menu()}


def test_menu_bar_has_file_edit_view_help_in_that_order(window):
    assert [top.text().replace("&", "") for top in window.menuBar().actions()] == ["File", "Edit", "View", "Help"]
    menus = _menu_texts(window)
    assert "Print label" in menus["File"]
    assert {"Paste image", "Clear image", "Clear doodle", "Copy label as image"} <= set(menus["Edit"])


def test_print_is_in_the_file_menu_and_on_ctrl_p(window, monkeypatch):
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest

    sent = []
    monkeypatch.setattr(core, "print_label", lambda spec: sent.append(spec) or [])
    window.content.text.setPlainText("Hello")
    assert window.print_action.shortcut().toString() == "Ctrl+P"
    window.print_action.trigger()
    QTest.keyClick(window, Qt.Key_P, Qt.ControlModifier)
    assert [s.text for s in sent] == ["Hello", "Hello"]
    assert window.print_action.isEnabled() and window.print_button.isEnabled()  # both come back after printing


def test_printing_an_empty_label_says_so_instead_of_sending(window, monkeypatch):
    monkeypatch.setattr(core, "print_label", lambda spec: (_ for _ in ()).throw(AssertionError("must not print")))
    window.content.text.setPlainText("")
    window.print_action.trigger()
    assert "Nothing to print" in window.status.text()


def test_paste_image_from_the_edit_menu(window, app, tmp_path):
    from PySide6.QtGui import QColor, QImage

    app.clipboard().clear()
    window.paste_image_from_clipboard()
    assert "no image on the clipboard" in window.status.text()
    image = QImage(20, 10, QImage.Format_RGB32)
    image.fill(QColor("black"))
    app.clipboard().setImage(image)
    window.paste_image_from_clipboard()
    assert window.content.image.text() and "Pasted" in window.status.text()


def test_clear_image_in_the_edit_menu_follows_the_image(window, tmp_path):
    from PIL import Image

    assert not window.clear_image_action.isEnabled()
    art = tmp_path / "a.png"
    Image.new("L", (10, 10), 0).save(art)
    window.content.set_image(str(art))
    assert window.clear_image_action.isEnabled()
    window.clear_image_action.trigger()
    assert window.content.image.text() == "" and not window.clear_image_action.isEnabled()


def test_copy_label_puts_the_printed_sticker_on_the_clipboard(window, app):
    app.clipboard().clear()
    window.content.text.setPlainText("")
    window.copy_label_image()
    assert "Nothing to copy" in window.status.text() and app.clipboard().image().isNull()
    window.content.text.setPlainText("Hi")
    window.copy_label_image()
    image = app.clipboard().image()
    assert (image.width(), image.height()) == (core.W, core.SH) and "Copied" in window.status.text()
    expected = core.label_bitmap(window.spec()).convert("L").tobytes()
    assert bytes(image.constBits())[: core.W * core.SH] == expected  # the very bitmap that prints


def test_keyboard_focus_cycle_follows_the_screen(window, app):
    """Tab goes preset bar, tabs, the page, Output, Print, and round again. (Qt's default creation order already does
    this; the test pins it so adding controls can't quietly break it. Hidden tabs and disabled controls are skipped.)"""
    from PySide6.QtWidgets import QTabWidget

    window.activateWindow()
    window.preset_box.setFocus()
    app.processEvents()
    stops = []
    for _ in range(13):
        stops.append(QApplication.focusWidget())
        window.focusNextChild()
        app.processEvents()
    tab_bar = window.findChild(QTabWidget).tabBar()
    # (the Delete button and the layout box are disabled, so they are skipped)
    names = [type(w).__name__ for w in stops]
    assert names[:12] == ["QComboBox", "QPushButton", "QTabBar", "QPlainTextEdit", "QLineEdit", "QLineEdit",
                          "QPushButton", "QPushButton", "QSpinBox", "QSpinBox", "QComboBox", "QPushButton"]
    assert stops[0] is window.preset_box and stops[2] is tab_bar and stops[10] is window.output.printer
    assert stops[11] is window.print_button
    assert stops[12] is window.preset_box  # after Print it wraps to the preset bar


def test_every_image_control_has_an_accessible_name(window):
    panel = window.image_panel
    for control, name in ((panel.cutoff, "Cutoff"), (panel.brightness, "Brightness"), (panel.contrast, "Contrast"),
                          (panel.gamma, "Gamma"), (panel.pixelate, "Pixelate")):
        assert control.slider.accessibleName() == name and control.spin.accessibleName() == f"{name} value"
    assert window.content.image.accessibleName() == "Image file"
    assert panel.image_layout.accessibleName() == "Layout" and panel.image_size.accessibleName()


def test_a_hidden_text_is_explained_not_silent(window, tmp_path):
    from PIL import Image

    art = tmp_path / "a.png"
    Image.new("L", (10, 10), 0).save(art)
    window.content.text.setPlainText("Caption")
    window.content.set_image(str(art))
    assert "text isn't printed" in window.status.text() and "Image tab" in window.status.text()
    window.content.qr.setText("https://example.com")
    assert "text and QR code aren't printed" in window.status.text()
    window.image_panel.image_layout.setCurrentIndex(window.image_panel.image_layout.findData("left"))
    assert window.status.text() == ""  # a real layout: nothing is hidden, nothing to say
    window.image_panel.image_layout.setCurrentIndex(window.image_panel.image_layout.findData("only"))
    window.content.text.setPlainText("")
    window.content.qr.setText("")
    assert window.status.text() == ""  # a picture on its own: nothing hidden either


def test_a_render_error_while_printing_is_reported_not_raised(window, monkeypatch):
    from PySide6.QtWidgets import QMessageBox

    shown = []
    monkeypatch.setattr(QMessageBox, "critical", lambda *a, **k: shown.append(a[2]))
    window.content.text.setPlainText("Hello")
    monkeypatch.setattr(core, "print_label", lambda spec: (_ for _ in ()).throw(FileNotFoundError("gone.png")))
    window.print_now()
    assert shown and "gone.png" in shown[0]
    assert window.print_button.isEnabled()


def test_drawing_on_the_doodle_pad_changes_the_label_and_undo_removes_it(window, app):
    window.tabs.setCurrentWidget(window.doodle)
    assert window.spec().doodle == "" and not window.doodle.clear.isEnabled()
    _use(window, "pen", (20, 20), (120, 80))
    drawn = core.render(window.spec())
    assert window.spec().doodle and drawn.getpixel((20, 20)) == 0
    assert window.doodle.undo.isEnabled() and window.doodle.clear.isEnabled()
    window.doodle.undo.click()
    assert window.spec().doodle == ""
    window.doodle.clear.click()  # nothing to clear: stays empty and disabled
    assert not window.doodle.clear.isEnabled()


def test_loading_a_spec_shows_its_doodle_and_the_eraser_works(window):
    from t003gui import doodle as doodle_mod

    mask = Image.new("L", (core.W, core.SH), 0)
    mask.paste(255, (0, 0, 199, 99))
    window.set_spec(core.LabelSpec(doodle=doodle_mod.encode(mask)))
    assert window.doodle.canvas.data() == doodle_mod.encode(mask)
    window.doodle.brush.setValue(10)
    ink = _use(window, "eraser", (50, 50))
    assert ink.getpixel((50, 50)) == 0 and ink.getpixel((150, 50)) == 255


def _use(window, tool, *points, ink=None):
    """Drag the doodle pad's `tool` through `points` (a single point is a click)."""
    from PySide6.QtCore import QPoint, Qt
    from PySide6.QtTest import QTest

    window.tabs.setCurrentWidget(window.doodle)
    window.doodle.tool.setCurrentIndex(window.doodle.tool.findData(tool))
    if ink:
        window.doodle.ink.setCurrentIndex(window.doodle.ink.findData(ink))
    pad = window.doodle.canvas
    z = pad.zoom  # the canvas is laid over the preview, so a dot is z x z pixels: click in the middle of it
    at = [QPoint(x * z + z // 2, y * z + z // 2) for x, y in points]
    QTest.mousePress(pad, Qt.LeftButton, Qt.NoModifier, at[0])
    for p in at[1:]:
        QTest.mouseMove(pad, p)
    QTest.mouseRelease(pad, Qt.LeftButton, Qt.NoModifier, at[-1])
    from t003gui import doodle as doodle_mod

    return doodle_mod.decode(window.spec().doodle)


@pytest.mark.parametrize("tool,points", [
    ("pen", [(20, 20), (80, 60)]), ("square", [(20, 20), (80, 60)]), ("italic", [(20, 20), (80, 60)]),
    ("spray", [(50, 50)]), ("line", [(20, 20), (80, 60)]), ("box", [(20, 20), (80, 60)]),
    ("oval", [(20, 20), (80, 60)]), ("stamp", [(100, 100)]),
])
def test_every_drawing_tool_leaves_ink_and_undo_takes_it_back(window, tool, points):
    ink = _use(window, tool, *points)
    assert ink is not None and ink.getbbox(), tool
    window.doodle.undo.click()
    assert window.spec().doodle == ""


def test_a_slanted_nib_draws_thin_horizontals_and_thick_diagonals(window):
    window.doodle.brush.setValue(12)
    flat = _use(window, "italic", (20, 100), (120, 100))
    flat_h = flat.getbbox()[3] - flat.getbbox()[1]
    window.doodle.clear.click()
    steep = _use(window, "italic", (200, 20), (200, 120))
    assert flat_h >= 12 and steep.getbbox()[2] - steep.getbbox()[0] >= 12  # the nib spans 12 dots on its diagonal


def doodle_ink(window):
    from t003gui import doodle as doodle_mod

    return doodle_mod.decode(window.spec().doodle)


def test_the_paint_bucket_fills_inside_a_shape_and_stops_at_its_edge(window):
    _use(window, "box", (50, 50), (150, 120))
    ink = _use(window, "fill", (100, 80))
    assert ink.getpixel((100, 80)) == 255 and ink.getpixel((60, 110)) == 255
    assert ink.getpixel((200, 80)) == 0 and ink.getpixel((20, 20)) == 0  # outside the box
    before = window.spec().doodle
    _use(window, "fill", (50, 80))  # on the outline itself: nothing to fill
    assert window.spec().doodle == before
    window.doodle.undo.click()
    assert doodle_ink(window).getpixel((100, 80)) == 0  # one undo took the whole fill back


def test_the_bucket_also_stops_at_the_labels_own_text(window):
    window.content.text.setPlainText("I")
    window.tabs.setCurrentWidget(window.doodle)
    ink = _use(window, "fill", (5, 5))
    assert ink.getpixel((5, 5)) == 255
    letter = core.render(core.LabelSpec(text="I", font=window.spec().font, bold=True))
    row = [x for x in range(core.W) if letter.getpixel((x, core.SH // 2)) < 128]
    assert ink.getpixel((row[len(row) // 2], core.SH // 2)) == 0  # the middle of the letter stays unfilled


def test_patterned_ink_covers_only_part_of_a_filled_area(window):
    _use(window, "box", (50, 50), (150, 120))
    window.doodle.ink.setCurrentIndex(window.doodle.ink.findData("half"))
    ink = _use(window, "fill", (100, 80))
    inside = [ink.getpixel((x, y)) for x in range(60, 140) for y in range(60, 110)]
    assert 0.35 < inside.count(255) / len(inside) < 0.65


def test_stickers_land_centred_on_the_click_and_the_picker_lists_them_all(window):
    from t003gui import stickers

    assert window.doodle.sticker.count() == len(stickers.STICKERS)
    window.doodle.sticker.setCurrentIndex(window.doodle.sticker.findData("heart"))
    window.doodle.sticker_size.setValue(3)
    ink = _use(window, "stamp", (200, 100))
    left, top, right, bottom = ink.getbbox()
    heart = stickers.mask("heart", 3).getbbox()
    assert (right - left, bottom - top) == (heart[2] - heart[0], heart[3] - heart[1])
    assert abs((left + right) / 2 - 200) <= 36 and abs((top + bottom) / 2 - 100) <= 36


def test_each_tool_shows_only_its_own_controls(window):
    def visible(widget):
        return not widget.isHidden()

    for tool, ink, brush, sticker in (("pen", True, True, False), ("spray", False, True, False),
                                      ("fill", True, False, False), ("stamp", False, False, True),
                                      ("eraser", False, True, False)):
        window.doodle.tool.setCurrentIndex(window.doodle.tool.findData(tool))
        assert (visible(window.doodle.ink), visible(window.doodle.brush), visible(window.doodle.sticker)) == \
            (ink, brush, sticker), tool


def test_the_bucket_does_not_leak_through_a_patterned_outline(window):
    for pattern in ("half", "quarter", "lines", "diagonal"):
        window.doodle.clear.click()
        _use(window, "box", (50, 50), (150, 120), ink=pattern)
        ink = _use(window, "fill", (100, 80), ink="solid")
        assert ink.getpixel((100, 80)) == 255 and ink.getpixel((200, 80)) == 0 and ink.getpixel((20, 20)) == 0, pattern


def test_the_canvas_lies_over_the_preview_only_while_the_doodle_tab_is_open(window, app):
    canvas = window.doodle.canvas
    assert not canvas.isVisible()
    window.tabs.setCurrentWidget(window.doodle)
    app.processEvents()
    assert canvas.isVisible() and canvas.parent() is window.preview
    pix = window.preview.pixmap()
    assert canvas.size().width() == core.W * canvas.zoom == pix.width()
    assert canvas.height() == core.SH * canvas.zoom  # the sticker part: the gap strip stays out of reach
    assert canvas.x() == (window.preview.width() - pix.width()) // 2 and canvas.y() == 0
    window.tabs.setCurrentWidget(window.content)
    assert not canvas.isVisible()


def test_the_preview_shows_the_doodle_via_the_canvas_while_drawing_and_prints_it_after(window, app):
    from PySide6.QtGui import QImage

    def pixel(x, y):  # of the preview label's pixmap, not of the canvas
        return QImage(window.preview.pixmap().toImage()).pixelColor(x * 2 + 1, y * 2 + 1).red()

    window.content.text.setPlainText("")
    _use(window, "box", (10, 10), (60, 60))
    assert pixel(10, 10) == 255  # drawing: the preview itself is the label without the doodle...
    window.tabs.setCurrentWidget(window.content)
    assert pixel(10, 10) == 0  # ...and once you leave, it is the exact printed label


def test_a_calligraphy_stroke_has_no_holes_along_a_diagonal(window):
    window.doodle.brush.setValue(10)
    ink = _use(window, "italic", (20, 20), (120, 120))
    row = [ink.getpixel((x, 70)) for x in range(core.W)]
    first, last = row.index(255), len(row) - 1 - row[::-1].index(255)
    assert last - first >= 8 and 0 not in row[first:last + 1]  # one solid run across the stroke, not a checker


def test_clear_doodle_in_the_edit_menu_follows_the_doodle_and_is_undoable(window):
    assert not window.clear_doodle_action.isEnabled()
    _use(window, "box", (10, 10), (60, 60))
    assert window.clear_doodle_action.isEnabled()
    window.clear_doodle_action.trigger()
    assert window.spec().doodle == "" and not window.clear_doodle_action.isEnabled()
    window.doodle.undo.click()
    assert window.spec().doodle and window.clear_doodle_action.isEnabled()
    window.set_spec(core.LabelSpec())  # loading a label without one
    assert not window.clear_doodle_action.isEnabled()


def test_the_status_line_mentions_a_doodle_except_while_drawing(window):
    _use(window, "box", (10, 10), (60, 60))
    assert "doodle" not in window.status.text().lower()  # you are looking at it
    window.tabs.setCurrentWidget(window.content)
    assert "Clear doodle" in window.status.text()
    window.clear_doodle_action.trigger()
    assert "doodle" not in window.status.text().lower()


def test_loading_a_label_that_differs_only_by_its_doodle_updates_the_status(window):
    from t003gui import doodle as doodle_mod

    window.tabs.setCurrentWidget(window.content)
    mask = Image.new("L", (core.W, core.SH), 0)
    mask.paste(255, (5, 5, 30, 30))
    window.set_spec(core.LabelSpec(doodle=doodle_mod.encode(mask)))
    assert "Clear doodle" in window.status.text()


@pytest.fixture
def clean_connection():
    from PySide6.QtCore import QSettings

    yield
    QSettings().remove("connection")
    QSettings().remove("btAddress")


def test_output_box_prints_over_usb_by_default(window, monkeypatch):
    assert window.output.bluetooth_target() is None and not window.output.address.isVisibleTo(window)
    calls = []
    monkeypatch.setattr(core, "print_label", lambda spec: calls.append("usb") or [])
    window.content.text.setPlainText("hi")
    window.print_now()
    assert calls == ["usb"]


def test_output_box_prints_over_bluetooth_when_chosen(window, monkeypatch, clean_connection):
    sent = []
    monkeypatch.setattr(core, "print_label", lambda spec, bluetooth=None: sent.append(bluetooth) or [])
    window.content.text.setPlainText("hi")
    window.output.printer.setCurrentIndex(1)
    assert window.output.address.isVisibleTo(window) and window.output.bluetooth_target() == ""
    window.print_now()  # "" means the first paired T003
    window.output.address.setText(" 57:37:EB:A7:7A:36 ")
    window.print_now()
    assert sent == ["", "57:37:EB:A7:7A:36"]


def test_a_bluetooth_failure_is_shown_like_a_usb_one(window, monkeypatch, clean_connection):
    from PySide6.QtWidgets import QMessageBox

    def refuse(spec, bluetooth=None):
        raise core.PrinterError("No paired T003 found.")

    shown = []
    monkeypatch.setattr(core, "print_label", refuse)
    monkeypatch.setattr(QMessageBox, "critical", lambda parent, title, text: shown.append(text))
    window.content.text.setPlainText("hi")
    window.output.printer.setCurrentIndex(1)
    window.print_now()
    assert shown == ["No paired T003 found."] and "No paired T003" in window.status.text()


def test_the_printer_choice_is_remembered(app, clean_connection):
    first = MainWindow()
    first.output.address.setText("57:37:EB:A7:7A:36")
    first.output.address.editingFinished.emit()
    first.output.printer.setCurrentIndex(1)
    first.close()
    second = MainWindow()
    try:
        assert second.output.bluetooth_target() == "57:37:EB:A7:7A:36" and second.output.address.isVisibleTo(second)
    finally:
        second.close()


def test_the_printer_choice_is_not_part_of_a_label(window, clean_connection):
    window.output.printer.setCurrentIndex(1)
    assert "bluetooth" not in window.spec().__dict__ and set(window.output.read()) == {"copies", "density"}
