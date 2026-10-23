import os
import tempfile

# Must be set before Qt / QSettings are first used: headless, and never touch the real config or presets.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["XDG_CONFIG_HOME"] = tempfile.mkdtemp(prefix="t003-test-config-")

# QSettings on Windows/macOS is the registry/plist, which XDG_CONFIG_HOME doesn't redirect: use a throwaway INI file
# there too, so the tests never touch (or depend on) the machine's real settings.
from PySide6.QtCore import QSettings  # noqa: E402

QSettings.setDefaultFormat(QSettings.IniFormat)
QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, tempfile.mkdtemp(prefix="t003-test-settings-"))
