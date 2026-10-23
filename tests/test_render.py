import itertools

import pytest
from PIL import Image

from t003gui import core


def _inked(img):
    return img.point(lambda v: 255 - v).getbbox()


@pytest.mark.parametrize("effect", core.EFFECTS)
@pytest.mark.parametrize("background", core.BACKGROUNDS)
def test_effects_and_backgrounds_stay_in_sticker(effect, background):
    img = core.render(core.LabelSpec(text="Hi\nthere", effect=effect, background=background, qr="x"))
    assert img.size == (core.W, core.H)
    assert img.crop((0, core.SH, core.W, core.H)).getextrema() == (255, 255)


@pytest.mark.parametrize("style", core.BORDER_STYLES)
@pytest.mark.parametrize("bars", [False, True])
def test_borders_and_bars_stay_in_sticker_and_leave_room(style, bars):
    spec = core.LabelSpec(text="Hello", border=True, border_style=style, bars=bars)
    img = core.render(spec)
    assert img.crop((0, core.SH, core.W, core.H)).getextrema() == (255, 255)
    assert _inked(img) is not None


def test_size_caps_text_and_auto_fills():
    small = core.render(core.LabelSpec(text="Hi", size=20))
    auto = core.render(core.LabelSpec(text="Hi"))
    assert _inked(small)[3] - _inked(small)[1] < _inked(auto)[3] - _inked(auto)[1]
    # a cap larger than what fits can't overflow the label
    huge = core.render(core.LabelSpec(text="Hi there friend", size=120))
    left, top, right, bottom = _inked(huge)
    assert left >= 0 and right <= core.W and bottom <= core.SH


def test_valign_positions():
    top = _inked(core.render(core.LabelSpec(text="Hi", size=40, valign="top")))
    mid = _inked(core.render(core.LabelSpec(text="Hi", size=40, valign="middle")))
    bot = _inked(core.render(core.LabelSpec(text="Hi", size=40, valign="bottom")))
    assert top[1] < mid[1] < bot[1]
    assert top[1] <= core.MARGIN + 2
    assert bot[3] >= core.SH - core.MARGIN - 2


def test_italic_changes_output_and_stays_within_width():
    plain = core.render(core.LabelSpec(text="Hello there", font="DejaVu Sans Mono", italic=False))
    slanted = core.render(core.LabelSpec(text="Hello there", font="DejaVu Sans Mono", italic=True))
    assert plain.tobytes() != slanted.tobytes()
    assert _inked(slanted)[2] <= core.W - core.MARGIN + 1


def test_effects_differ_from_plain():
    plain = core.render(core.LabelSpec(text="Hi")).tobytes()
    for effect in core.EFFECTS[1:]:
        assert core.render(core.LabelSpec(text="Hi", effect=effect)).tobytes() != plain


def test_invalid_choices_fall_back():
    core.render(core.LabelSpec(text="x", effect="sparkle", background="lava", border=True, border_style="wavy",
                               valign="sideways"))


def test_all_combos_render_quickly():
    import time
    start = time.time()
    for effect, bg in itertools.product(("none", "3d"), ("none", "gradient")):
        core.render(core.LabelSpec(text="WELCOME TO MY\nHOMEPAGE", effect=effect, background=bg, italic=True))
    assert time.time() - start < 5
