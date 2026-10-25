import json

from t003gui.settings import Settings


def test_round_trip_and_forgetting(tmp_path):
    settings = Settings(tmp_path / "dir" / "s.json")
    assert settings.get("a") is None and settings.get("a", 3) == 3
    settings.set("a", {"x": [1, "é"]})
    settings.set("b", False)
    assert settings.get("a") == {"x": [1, "é"]} and settings.get("b") is False
    settings.set("a", None)
    assert settings.get("a") is None and settings.get("b") is False
    assert not list((tmp_path / "dir").glob("*.tmp"))


def test_a_damaged_or_odd_file_means_no_settings(tmp_path):
    path = tmp_path / "s.json"
    for text in ("{not json", "[1, 2]", "", "null"):
        path.write_text(text)
        settings = Settings(path)
        assert settings.get("a", "fallback") == "fallback"
        settings.set("a", 1)  # and it can be written over
        assert json.loads(path.read_text()) == {"a": 1}


def test_default_path_follows_xdg(monkeypatch, tmp_path):
    from t003gui import settings

    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    assert settings.default_path() == tmp_path / "t003-label-gui" / "settings.json"
