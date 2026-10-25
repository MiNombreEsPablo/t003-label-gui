"""What an installed copy needs, and that the parts without Qt really work without it."""
import ast
import fnmatch
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACKAGE = ROOT / "src" / "t003gui"


def _package_data_patterns() -> list[str]:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r"\[tool\.setuptools\.package-data\]\s*t003gui\s*=\s*(\[.*?\])", text, re.S)
    assert match, "pyproject.toml has no package-data for t003gui"
    return ast.literal_eval(match.group(1))


def test_package_data_covers_every_asset_and_font():
    """A wheel only contains what package-data lists. The editable dev install hid a wheel with no icons or
    arrows, so every non-code file under the package must match a pattern."""
    patterns = _package_data_patterns()
    for path in PACKAGE.rglob("*"):
        rel = path.relative_to(PACKAGE).as_posix()
        if path.is_dir() or path.suffix in {".py", ".pyc"} or "__pycache__" in rel:
            continue
        assert any(fnmatch.fnmatch(rel, pattern) for pattern in patterns), f"{rel} would be missing from the wheel"


def _run_without_qt(code: str) -> subprocess.CompletedProcess:
    blocker = "import sys; sys.modules['PySide6'] = None; "  # any import of PySide6 now fails
    return subprocess.run([sys.executable, "-c", blocker + code], capture_output=True, text=True, cwd=ROOT, timeout=60)


def test_core_and_cli_work_without_qt(tmp_path):
    out = tmp_path / "label.png"
    result = _run_without_qt(
        "from t003gui import cli, core, composition, presets, imaging; "
        f"cli.main(['Hello', '--preview', {str(out)!r}]); "
        "print('ok')"
    )
    assert result.returncode == 0 and "ok" in result.stdout, result.stderr
    assert out.exists()


def test_launcher_says_what_to_install_when_qt_is_missing():
    result = _run_without_qt("from t003gui import launcher; launcher.main()")
    assert result.returncode != 0
    assert "pip install 't003-label-gui[gui]'" in result.stderr and "t003-print" in result.stderr
    assert "Traceback" not in result.stderr  # a message, not a stack trace


def test_launcher_does_not_hide_real_import_errors():
    """Only a missing PySide6 gets the friendly message; any other ImportError is a bug and must surface."""
    code = (
        "import sys, importlib.abc\n"
        "class Break(importlib.abc.MetaPathFinder):\n"
        "    def find_spec(self, name, path, target=None):\n"
        "        if name == 't003gui.app':\n"
        "            raise ImportError('boom', name='some.other.module')\n"
        "sys.meta_path.insert(0, Break())\n"
        "from t003gui import launcher\n"
        "launcher.main()\n"
    )
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, cwd=ROOT, timeout=60)
    assert result.returncode != 0 and "Traceback" in result.stderr and "boom" in result.stderr
    assert "pip install" not in result.stderr


def test_launcher_says_what_to_install_when_pywebview_is_missing():
    blocker = "import sys; sys.modules['webview'] = None; sys.argv = ['t003-gui', '--web']; "
    result = subprocess.run([sys.executable, "-c", blocker + "from t003gui import launcher; launcher.main()"],
                            capture_output=True, text=True, cwd=ROOT, timeout=60)
    assert result.returncode != 0
    assert "pip install 't003-label-gui[web]'" in result.stderr
