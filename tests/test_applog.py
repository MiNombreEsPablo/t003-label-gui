import logging
import sys

from t003gui import applog


def test_log_records_the_environment_and_errors(tmp_path, monkeypatch):
    monkeypatch.setenv("T003_LOG_DIR", str(tmp_path))
    monkeypatch.setattr(sys, "excepthook", sys.excepthook)  # start() replaces it
    root = logging.getLogger()
    before = list(root.handlers)
    try:
        path = applog.start()
        assert path == tmp_path / applog.NAME
        try:
            raise RuntimeError("boom in the toolkit")
        except RuntimeError as e:
            applog.record(e)
    finally:
        for handler in root.handlers[:]:
            if handler not in before:
                handler.flush()
                root.removeHandler(handler)
    text = path.read_text(encoding="utf-8")
    assert "start: t003-label-gui" in text and "Python " in text
    assert "RuntimeError: boom in the toolkit" in text and "Traceback" in text


def test_an_old_big_log_is_kept_as_dot_one(tmp_path, monkeypatch):
    monkeypatch.setenv("T003_LOG_DIR", str(tmp_path))
    monkeypatch.setattr(sys, "excepthook", sys.excepthook)
    (tmp_path / applog.NAME).write_text("x" * (applog.MAX_BYTES + 1), encoding="utf-8")
    root = logging.getLogger()
    before = list(root.handlers)
    try:
        applog.start()
    finally:
        for handler in root.handlers[:]:
            if handler not in before:
                root.removeHandler(handler)
    assert (tmp_path / (applog.NAME + ".1")).exists()
    assert (tmp_path / applog.NAME).stat().st_size < applog.MAX_BYTES


def test_an_unwritable_log_location_does_not_stop_the_app(tmp_path, monkeypatch):
    blocker = tmp_path / "file"
    blocker.write_text("not a folder")
    monkeypatch.setenv("T003_LOG_DIR", str(blocker / "sub"))
    assert applog.start() is None
