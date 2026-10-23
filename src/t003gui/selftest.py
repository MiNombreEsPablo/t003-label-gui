"""`t003-gui --selftest`: prove an installed or frozen build is complete, without a printer or a display.

CI runs this against every packaged app, so a missing font, icon or libusb in a bundle fails the build.
"""
from __future__ import annotations

import os
import sys


def _report(text: str, *, error: bool) -> None:
    print(text, file=sys.stderr if error else sys.stdout)
    log = os.environ.get("T003_SELFTEST_LOG")  # windowed Windows builds have no console, so CI reads this file
    if log:
        with open(log, "a", encoding="utf-8") as f:
            f.write(text + "\n")


def run() -> int:
    from . import core, fonts, theme

    problems: list[str] = []
    for font in fonts.BUNDLED:
        for filename in font.files.values():
            if not (fonts.FONT_DIR / filename).exists():
                problems.append(f"missing font file {filename}")
        if not (fonts.FONT_DIR / "LICENSES" / font.license_file).exists():
            problems.append(f"missing licence {font.license_file}")
    for asset in ("icon-256.png", "icon-mark.png", "arrow-down.png", "arrow-up.png", "arrow-down-plum.png", "arrow-up-plum.png",
                  "arrow-down-lcd.png", "arrow-up-lcd.png", "arrow-down-dmg.png", "arrow-up-dmg.png"):
        if not (theme.ASSETS / asset).exists():
            problems.append(f"missing asset {asset}")

    spec = core.LabelSpec(text="日本語 TEST", font="Orbitron", effect="neon", background="circuit", qr="t003")
    if core.render(spec).point(lambda v: 255 - v).getbbox() is None:
        problems.append("rendering produced a blank label")
    if not core.tspl(spec).startswith(b"SIZE "):
        problems.append("TSPL payload is malformed")
    backend = core._backend()
    if backend is None:
        problems.append("no libusb backend found (libusb-package missing from the build?)")
    printer = core.printer_presence() if backend is not None else "not checked"  # informational: CI has no printer

    if problems:
        _report("selftest FAILED:\n  " + "\n  ".join(problems), error=True)
        return 1
    _report(
        f"selftest ok: {len(fonts.BUNDLED)} bundled font families, Japanese render, TSPL, libusb; printer {printer}",
        error=False,
    )
    return 0
