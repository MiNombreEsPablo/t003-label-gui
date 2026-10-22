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


def _ink_extent(img):
    """(min_x, max_x) of black pixels."""
    inverted = img.point(lambda v: 255 - v)
    left, _, right, _ = inverted.getbbox()
    return left, right - 1


def test_alignment_moves_text_block():
    left = _ink_extent(core.render(core.LabelSpec(text="Hi", align="left")))
    centre = _ink_extent(core.render(core.LabelSpec(text="Hi", align="center")))
    right = _ink_extent(core.render(core.LabelSpec(text="Hi", align="right")))
    assert left[0] <= core.MARGIN + 2
    assert right[1] >= core.W - core.MARGIN - 2
    assert left[0] < centre[0] < right[0]


def test_multiline_lines_align_within_block():
    # short line under a long one: left-aligned starts at the block's left edge, right-aligned ends at its right edge
    spec = core.LabelSpec(text="WWWWWWWW\ni", align="left")
    left = core.render(spec).crop((0, core.SH // 2 + 20, core.W, core.SH))
    spec.align = "right"
    right = core.render(spec).crop((0, core.SH // 2 + 20, core.W, core.SH))
    assert _ink_extent(left)[0] < _ink_extent(right)[0]


def test_font_choice_changes_output_and_resolves():
    import os
    assert os.path.exists(core.font_path("DejaVu Sans", True))
    assert core.font_path("DejaVu Sans", True) != core.font_path("DejaVu Sans", False)
    a = core.render(core.LabelSpec(text="Hello", font="DejaVu Sans"))
    b = core.render(core.LabelSpec(text="Hello", font="Noto Sans Mono", bold=False))
    assert a.tobytes() != b.tobytes()


def test_unknown_font_and_bad_align_do_not_crash():
    core.render(core.LabelSpec(text="x", font="NoSuchFontXYZ", align="sideways"))
