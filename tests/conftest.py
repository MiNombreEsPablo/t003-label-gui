import os
import tempfile

# Must be set before Qt / QSettings are first used: headless, and never touch the real config or presets.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["XDG_CONFIG_HOME"] = tempfile.mkdtemp(prefix="t003-test-config-")
