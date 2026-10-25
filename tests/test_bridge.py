import base64
import json

from t003gui import api, bluetooth, core
from t003gui.bridge import Bridge

SPEC = json.dumps({"text": "Hello", "border": True})


def test_options_are_the_apis():
    assert Bridge().options() == api.options()


def test_preview_is_the_api_pixels_in_base64():
    assert base64.b64decode(Bridge().preview(SPEC)) == api.preview_pixels(SPEC)


def test_print_goes_over_usb_without_a_target(monkeypatch):
    calls = []
    monkeypatch.setattr(core, "print_label", lambda spec: calls.append(spec) or ["out of paper"])
    result = Bridge().print_label(SPEC)
    assert result == {"problems": ["out of paper"], "error": None}
    assert calls[0].text == "Hello" and calls[0].border is True


def test_print_goes_over_bluetooth_with_a_target(monkeypatch):
    calls = []
    monkeypatch.setattr(core, "print_label", lambda spec, bluetooth=None: calls.append(bluetooth) or [])
    assert Bridge().print_label(SPEC, "AA:BB:CC:DD:EE:FF")["error"] is None
    assert Bridge().print_label(SPEC, "")["error"] is None  # "" = the first known T003
    assert calls == ["AA:BB:CC:DD:EE:FF", ""]


def test_failures_come_back_as_data_not_exceptions(monkeypatch):
    def fail(spec, bluetooth=None):
        raise core.PrinterError("T003 not found on USB")

    monkeypatch.setattr(core, "print_label", fail)
    assert Bridge().print_label(SPEC) == {"problems": [], "error": "T003 not found on USB"}
    monkeypatch.setattr(core, "print_label", lambda spec, bluetooth=None: (_ for _ in ()).throw(OSError("gone")))
    assert Bridge().print_label(SPEC)["error"] == "gone"
    broken = Bridge().print_label("{nope")  # bad JSON is a ValueError too
    assert broken["problems"] == [] and broken["error"]


def test_known_printers_are_plain_dicts(monkeypatch):
    monkeypatch.setattr(bluetooth, "known_printers", lambda: [("57:37:EB:A7:7A:36", "T003-7A36")])
    assert Bridge().known_printers() == [{"address": "57:37:EB:A7:7A:36", "name": "T003-7A36"}]


def test_the_bridge_needs_neither_qt_nor_pywebview():
    import subprocess
    import sys
    from pathlib import Path

    code = ("import sys; sys.modules['PySide6'] = None; sys.modules['webview'] = None\n"
            "from t003gui.bridge import Bridge; print(len(Bridge().preview('{}')) > 0)")
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                            cwd=Path(__file__).resolve().parent.parent, timeout=60)
    assert result.returncode == 0 and "True" in result.stdout, result.stderr
