from PIL import Image

from t003gui import core


def test_render_size_and_gap_stays_white():
    img = core.render(core.LabelSpec(text="hello", qr="https://example.com", border=True))
    assert img.size == (core.W, core.H)
    gap = img.crop((0, core.SH, core.W, core.H))
    assert gap.getextrema() == (255, 255)


def test_text_is_black_on_white():
    img = core.render(core.LabelSpec(text="X"))
    assert img.getextrema() == (0, 255)


def test_tspl_payload_layout():
    payload = core.tspl(core.LabelSpec(text="x", copies=3, density=9))
    assert payload.startswith(b"SIZE 72 mm,30 mm\r\n")
    assert b"DENSITY 9\r\n" in payload
    head, _, rest = payload.partition(b"BITMAP 0,0,48,240,0,")
    assert rest.endswith(b"\r\nPRINT 3,1\r\n")
    assert len(rest) == 48 * 240 + len(b"\r\nPRINT 3,1\r\n")


def test_image_threshold_removes_light_colours(tmp_path):
    path = tmp_path / "yellow.png"
    Image.new("RGB", (100, 100), (255, 230, 0)).save(path)
    img = core.render(core.LabelSpec(image_path=str(path), threshold=160))
    assert img.getextrema() == (255, 255)
