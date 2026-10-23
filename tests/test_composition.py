import json

import pytest
from PIL import Image

from t003gui import cli, composition, core


def _spec(**kw):
    base = dict(text="Hello\nWorld", qr="https://example.com", copies=3, density=9, font="Orbitron", bold=False,
                italic=True, size=40, align="left", valign="top", effect="shadow", border=True,
                border_style="double", background="grid", bars=True, threshold=99)
    return core.LabelSpec(**{**base, **kw})


def test_round_trip(tmp_path):
    path = tmp_path / ("a" + composition.SUFFIX)
    composition.save(path, _spec())
    assert composition.load(path) == _spec()
    assert not list(tmp_path.glob("*.tmp"))  # the atomic write cleaned up


def test_image_is_embedded_so_the_file_travels(tmp_path):
    art = tmp_path / "art.png"
    Image.new("L", (30, 20), 0).save(art)
    path = tmp_path / ("a" + composition.SUFFIX)
    composition.save(path, _spec(image_path=str(art)))
    art.unlink()  # as if the file were opened on another machine

    data = json.loads(path.read_text())
    assert data["spec"]["image_path"] == "" and data["image"]["name"] == "art.png"
    loaded = composition.load(path, image_dir=tmp_path / "out")
    assert loaded.image_path.startswith(str(tmp_path / "out")) and Image.open(loaded.image_path).size == (30, 20)
    assert core.render(loaded).size == (core.W, core.H)  # and it renders


def test_a_missing_image_keeps_its_path_instead_of_failing(tmp_path):
    path = tmp_path / ("a" + composition.SUFFIX)
    composition.save(path, _spec(image_path="/no/such/file.png"))
    assert composition.load(path).image_path == "/no/such/file.png"


def test_embedded_names_cannot_escape_the_image_folder(tmp_path):
    blob = "aGk="  # "hi"
    for name in ("../../evil.png", "/etc/passwd", "a/b/c.png", "x.sh", ""):
        text = json.dumps({"format": composition.FORMAT, "version": 1, "spec": {}, "image": {"name": name, "data": blob}})
        out = tmp_path / "out"
        path = composition.Path(composition.loads(text, image_dir=out).image_path)
        assert path.parent == out and path.suffix in {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp"}


@pytest.mark.parametrize("text, message", [
    ("not json", "not a label file"),
    ("[]", "not a T003 label file"),
    (json.dumps({"format": "other", "version": 1, "spec": {}}), "not a T003 label file"),
    (json.dumps({"format": composition.FORMAT, "version": 99, "spec": {}}), "newer version"),
    (json.dumps({"format": composition.FORMAT, "spec": {}}), "newer version"),
    (json.dumps({"format": composition.FORMAT, "version": 1, "spec": {}, "image": {"name": "a.png", "data": "@@"}}),
     "damaged"),
])
def test_bad_files_are_refused_with_a_reason(text, message):
    with pytest.raises(ValueError, match=message):
        composition.loads(text)


def test_unknown_fields_are_ignored():
    text = json.dumps({"format": composition.FORMAT, "version": 1, "spec": {"text": "hi", "from_the_future": 1}})
    assert composition.loads(text).text == "hi"


def test_export_png_is_the_printed_sticker(tmp_path):
    spec = core.LabelSpec(text="Hi")
    one, four = tmp_path / "1.png", tmp_path / "4.png"
    core.export_png(spec, one)
    core.export_png(spec, four, scale=4)
    a, b = Image.open(one), Image.open(four)
    assert (a.size, a.mode) == ((core.W, core.SH), "1")
    assert (b.size, b.mode) == ((core.W * 4, core.SH * 4), "1")
    assert b.resize(a.size, Image.Resampling.NEAREST).tobytes() == a.tobytes()  # nothing but enlarged dots
    expected = core.to_bitmap(core.render(spec)).crop((0, 0, core.W, core.SH))
    assert a.tobytes() == expected.tobytes()


def test_cli_loads_a_composition_and_flags_override_it(tmp_path):
    saved = tmp_path / ("a" + composition.SUFFIX)
    composition.save(saved, core.LabelSpec(text="from file", effect="outline"))
    out = tmp_path / "p.png"
    cli.main(["--file", str(saved), "--preview", str(out)])
    expected = core.to_bitmap(core.render(core.LabelSpec(text="from file", effect="outline")))
    assert Image.open(out).tobytes() == expected.tobytes()
    with pytest.raises(SystemExit):
        cli.main(["--file", str(tmp_path / ("missing" + composition.SUFFIX))])
    with pytest.raises(SystemExit):
        cli.main(["--file", str(saved), "--preset", "x"])
