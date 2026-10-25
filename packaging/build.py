"""Build the standalone app for the current OS with PyInstaller.

    python packaging/build.py            # -> dist/t003-label-studio/ (Linux), dist/T003 Label Studio/ (Windows),
                                         #    dist/T003 Label Studio.app (macOS)
    python packaging/build.py --shell    # the web app (the web UI in a native window) instead of the Qt app
Each OS must build for itself (PyInstaller does not cross-compile); the release workflow does all three.
"""
import os
import platform
import plistlib
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SYSTEM = platform.system()


UNUSED_QT = ("Qt3DAnimation", "Qt3DCore", "Qt3DExtras", "Qt3DInput", "Qt3DLogic", "Qt3DRender", "QtCharts", "QtDataVisualization",
             "QtDesigner", "QtGraphs", "QtHelp", "QtMultimedia", "QtMultimediaWidgets", "QtNetworkAuth", "QtNfc", "QtPdf",
             "QtPdfWidgets", "QtQuick3D", "QtRemoteObjects", "QtScxml", "QtSensors", "QtSerialBus", "QtSerialPort", "QtSpatialAudio",
             "QtSql", "QtStateMachine", "QtSvg", "QtSvgWidgets", "QtTest", "QtTextToSpeech", "QtUiTools", "QtWebSockets", "QtXml")


def allow_bluetooth(app: Path) -> None:
    """macOS kills an app that uses Bluetooth without saying why in its Info.plist; the edit breaks the signature
    PyInstaller put on the bundle, so it is signed again (ad hoc, like PyInstaller's)."""
    plist_path = app / "Contents" / "Info.plist"
    info = plistlib.loads(plist_path.read_bytes())
    info["NSBluetoothAlwaysUsageDescription"] = "T003 Label Studio sends labels to your T003 printer over Bluetooth."
    plist_path.write_bytes(plistlib.dumps(info))
    subprocess.check_call(["codesign", "--force", "--deep", "--sign", "-", str(app)])


def prune(folder: Path) -> None:
    """Drop what the web window doesn't use from a Linux bundle: Qt's own translations and QML, and every Chromium
    language pack but English."""
    qt = next(folder.rglob("PySide6/Qt"), None)
    if qt is None:
        return
    for name in ("translations", "qml"):
        shutil.rmtree(qt / name, ignore_errors=True)
    for pack in qt.rglob("qtwebengine_locales/*.pak"):
        if pack.name != "en-US.pak":
            pack.unlink()


def main() -> None:
    shell = "--shell" in sys.argv[1:]
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
    if shell:
        args += ["--add-data", f"{ROOT / 'src/t003gui/web'}{sep}t003gui/web",  # the page and the dev server it is served by
                 "--collect-data", "webview",  # its JavaScript helpers; the backend is named below, per OS
                 "--hidden-import", "t003gui.web.dev_server", "--hidden-import", "t003gui.web.desktop"]
        # pywebview imports every backend it knows by name; each OS ships the one it uses, so nothing else is dragged in
        backends = {"Linux": "qt", "Windows": "winforms", "Darwin": "cocoa"}  # Linux: QtWebEngine comes with the bundle
        mine = backends[SYSTEM]
        args += ["--hidden-import", f"webview.platforms.{mine}"]
        if SYSTEM != "Linux":  # printing over BLE (ble.py): bleak picks its WinRT or CoreBluetooth backend by name
            args += ["--collect-submodules", "bleak"]
        if SYSTEM == "Darwin":
            args += ["--hidden-import", "CoreBluetooth", "--hidden-import", "objc"]
        if SYSTEM == "Windows":
            args += ["--hidden-import", "webview.platforms.edgechromium"]  # WebView2, which winforms draws with
        if SYSTEM == "Linux":
            args += ["--collect-submodules", "qtpy", "--hidden-import", "PySide6.QtWebEngineWidgets",
                     "--hidden-import", "PySide6.QtWebChannel"]
        for other in ("gtk", "cef", "android", "cocoa", "winforms", "qt", "edgechromium", "mshtml"):
            if other != mine and not (SYSTEM == "Windows" and other == "edgechromium"):
                args += ["--exclude-module", f"webview.platforms.{other}"]
        if SYSTEM == "Linux":  # PySide6 modules the web window never imports (QtWebEngine needs none of them from Python)
            for module in UNUSED_QT:
                args += ["--exclude-module", f"PySide6.{module}"]
        for foreign in ("gi", "PyQt5", "PyQt6", "PySide2") + (("PySide6", "qtpy") if mine != "qt" else ()):
            args += ["--exclude-module", foreign]
    icon = {"Windows": "t003-label-gui.ico", "Darwin": "t003-label-gui.icns"}.get(SYSTEM)
    if icon:
        args += ["--icon", str(ROOT / "packaging/icons" / icon)]
    if SYSTEM == "Darwin":
        args += ["--osx-bundle-identifier", "io.github.minombreespablo.t003labelstudio"]
    args.append(str(ROOT / "packaging" / ("entry_shell.py" if shell else "entry.py")))
    subprocess.check_call(args, cwd=ROOT)
    if shell and SYSTEM == "Linux":
        prune(ROOT / "dist" / name)
    if shell and SYSTEM == "Darwin":
        allow_bluetooth(ROOT / "dist" / f"{name}.app")


if __name__ == "__main__":
    main()
