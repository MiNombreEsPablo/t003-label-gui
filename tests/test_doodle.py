import base64
import io

import pytest
from PIL import Image

from t003gui import composition, core, doodle
from t003gui.spec import SH, W, LabelSpec


def _mask(*boxes) -> Image.Image:
    img = Image.new("L", (W, SH), 0)
    for box in boxes:
        img.paste(255, box)
    return img


def test_round_trip_and_empty():
    text = doodle.encode(_mask((10, 10, 29, 19)))
    ink = doodle.decode(text)
    assert ink.size == (W, SH) and ink.getpixel((10, 10)) == 255 and ink.getpixel((30, 10)) == 0
    assert doodle.encode(_mask()) == "" and doodle.decode("") is None


@pytest.mark.parametrize("bad", ["not base64!", base64.b64encode(b"nope").decode(),
                                 base64.b64encode(io.BytesIO().getvalue()).decode()])
def test_damaged_doodle_is_ignored(bad):
    assert doodle.decode(bad) is None
    assert core.render(LabelSpec(text="x", doodle=bad)).size == (W, core.H)


def test_wrong_size_is_ignored():
    out = io.BytesIO()
    Image.new("1", (10, 10), 1).save(out, "PNG")
    assert doodle.decode(base64.b64encode(out.getvalue()).decode()) is None


def test_ink_is_drawn_on_top_of_everything():
    plain = core.render(LabelSpec(text="HELLO", background="checker"))
    inked = core.render(LabelSpec(text="HELLO", background="checker", doodle=doodle.encode(_mask((0, 0, 99, 99)))))
    assert {inked.getpixel((x, y)) for x in range(99) for y in range(99)} == {0}
    assert inked.crop((100, 0, W, core.H)).tobytes() == plain.crop((100, 0, W, core.H)).tobytes()


def test_doodle_also_sits_on_an_image_only_label(tmp_path):
    path = tmp_path / "white.png"
    Image.new("RGB", (50, 50), "white").save(path)
    spec = LabelSpec(image_path=str(path), doodle=doodle.encode(_mask((5, 5, 14, 14))))
    assert core.render(spec).getpixel((5, 5)) == 0


def test_the_doodle_never_reaches_the_gap():
    img = core.render(LabelSpec(doodle=doodle.encode(_mask((0, 0, W - 1, SH - 1)))))
    assert {img.getpixel((x, y)) for x in (0, W - 1) for y in range(SH, core.H)} == {255}


def test_doodle_travels_in_a_composition_and_a_bad_type_falls_back():
    spec = LabelSpec(text="a", doodle=doodle.encode(_mask((1, 1, 5, 5))))
    assert composition.loads(composition.dumps(spec)).doodle == spec.doodle
    assert LabelSpec.from_dict({"doodle": 5}).doodle == ""


GRID_DOTS = 24 * 24


def test_every_sticker_has_ink_and_fits_the_sticker_at_every_size():
    from t003gui import stickers

    for name in stickers.STICKERS:
        for scale in range(1, stickers.MAX_SCALE + 1):
            m = stickers.mask(name, scale)
            assert m.size == (stickers.GRID * scale,) * 2 and m.getbbox(), (name, scale)
            assert m.size[1] <= SH
        hist = stickers.mask(name, 1).histogram()
        assert hist[0] + hist[255] == GRID_DOTS
