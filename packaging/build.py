"""Build the standalone app for the current OS with PyInstaller.

    python packaging/build.py            # -> dist/t003-label-studio/ (Linux), dist/T003 Label Studio/ (Windows),
                                         #    dist/T003 Label Studio.app (macOS)
Each OS must build for itself (PyInstaller does not cross-compile); the release workflow does all three.
"""
import os
import platform
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SYSTEM = platform.system()


def main() -> None:
    sep = os.pathsep
    name = "t003-label-studio" if SYSTEM == "Linux" else "T003 Label Studio"
    args = [
        sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--windowed", "--noupx",
        "--name", name,
        "--paths", str(ROOT / "src"),
        "--add-data", f"{ROOT / 'src/t003gui/fonts'}{sep}t003gui/fonts",
        "--add-data", f"{ROOT / 'src/t003gui/assets'}{sep}t003gui/assets",
        "--collect-all", "libusb_package",  # the libusb shared library that pyusb loads
        "--exclude-module", "tkinter",
        "--distpath", str(ROOT / "dist"), "--workpath", str(ROOT / "build"), "--specpath", str(ROOT / "build"),
    ]
    icon = {"Windows": "t003-label-gui.ico", "Darwin": "t003-label-gui.icns"}.get(SYSTEM)
    if icon:
        args += ["--icon", str(ROOT / "packaging/icons" / icon)]
    if SYSTEM == "Darwin":
        args += ["--osx-bundle-identifier", "io.github.minombreespablo.t003labelstudio"]
    args.append(str(ROOT / "packaging/entry.py"))
    subprocess.check_call(args, cwd=ROOT)


if __name__ == "__main__":
    main()
