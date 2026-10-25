import json

import pytest
from PIL import Image

from t003gui import cli, core
from t003gui.presets import PresetStore


def test_preset_roundtrip_and_delete(tmp_path):
    store = PresetStore(tmp_path / "sub" / "presets.json")
    assert store.names() == []
    spec = core.LabelSpec(text="shelf", qr="x", threshold=120, border=True, copies=2, density=9)
    store.save("Shelf", spec)
    store.save("alpha", core.LabelSpec(text="a"))
    assert store.names() == ["alpha", "Shelf"]
    assert store.get("Shelf") == spec
    store.delete("Shelf")
    assert store.get("Shelf") is None


def test_preset_ignores_unknown_fields_and_bad_json(tmp_path):
    path = tmp_path / "presets.json"
    path.write_text(json.dumps({"old": {"text": "t", "removed_field": 1}}))
    assert PresetStore(path).get("old") == core.LabelSpec(text="t")
    path.write_text("not json")
    assert PresetStore(path).names() == []


def test_cli_preview_with_preset_override(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    PresetStore().save("p", core.LabelSpec(text="from preset", border=True))
    out = tmp_path / "out.png"
    cli.main(["--preset", "p", "--copies", "4", "--preview", str(out)])
    assert Image.open(out).size == (core.W, core.H)


def test_cli_requires_content():
    with pytest.raises(SystemExit):
        cli.main([])


def test_cli_reports_an_oversized_qr_instead_of_a_traceback(tmp_path):
    with pytest.raises(SystemExit) as e:
        cli.main(["x", "--qr", "x" * 5000, "--preview", str(tmp_path / "o.png")])
    assert "error:" in str(e.value)


def test_a_saved_label_that_is_only_a_doodle_prints(tmp_path, monkeypatch):
    from t003gui import composition, doodle

    ink = Image.new("L", (core.W, core.SH), 0)
    ink.paste(255, (10, 10, 100, 30))
    path = tmp_path / "scribble.t003label"
    composition.save(path, core.LabelSpec(doodle=doodle.encode(ink)))
    sent = []
    monkeypatch.setattr(core, "print_label", lambda spec, bluetooth=None: sent.append(spec) or [])
    cli.main(["--file", str(path)])
    assert len(sent) == 1 and sent[0].doodle


def test_an_empty_label_still_asks_for_something_to_print(monkeypatch):
    monkeypatch.setattr(core, "print_label", lambda *a, **k: (_ for _ in ()).throw(AssertionError("must not print")))
    with pytest.raises(SystemExit) as e:
        cli.main([])
    assert e.value.code == 2
