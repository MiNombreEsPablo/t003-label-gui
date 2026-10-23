<p align="center"><img src="packaging/icons/t003-label-gui-128.png" alt="T003 Label Studio icon" width="96"></p>

# T003 Label Studio

Design and print stickers on the **ORGBRO T003** USB thermal label printer, with a live preview of exactly what the
printer will burn. Text, QR codes and images, plus a pile of early-web and cyberpunk styling, and every font can print
Japanese (日本語).

<table>
  <tr>
    <td><img src="docs/screenshots/theme-y2k-blue.png" alt="Y2K Blue theme with a neon-effect label"></td>
    <td><img src="docs/screenshots/theme-y2k-pink.png" alt="Y2K Pink theme"></td>
  </tr>
  <tr>
    <td><img src="docs/screenshots/theme-gunmetal.png" alt="Gunmetal theme"></td>
    <td><img src="docs/screenshots/theme-handheld.png" alt="Handheld theme, with the preview tinted olive green"></td>
  </tr>
</table>

<p align="center"><img src="docs/screenshots/image-layout.png" width="720"
alt="A dithered picture next to a caption, with the Image tab's dither, tone and looks controls"></p>

<p align="center"><sub>The four themes (Y2K Blue, Y2K Pink, Gunmetal, Handheld), and a picture with a caption using ordered
dithering. Regenerate with <code>python packaging/make_screenshots.py</code>.</sub></p>

## Features

- **Live 1-bit preview** that is the same bitmap that gets printed (what you see is what you stick).
- **Text:** 23 bundled open-licence fonts in five groups (Cyber, Pixel, Early web, Display, Clean), bold/italic, size,
  left/centre/right and top/middle/bottom alignment. Latin-only fonts borrow kana and kanji from Zen Kaku Gothic New;
  DotGothic16, Yusei Magic, Dela Gothic One and Stick have their own Japanese.
- **Effects:** dithered shadow, outline, 3D WordArt, glitch, neon glow, scanline text.
- **Backgrounds:** checker, dots, stripes, dithered gradient, stars, graph paper, scanlines, circuit board, hex grid,
  synthwave sun, matrix rain, halftone. **Borders:** solid, double, dotted, checker, Win95 bevel, marquee lights,
  cyber panel, HUD brackets, ruler ticks. **Bars:** under-construction hazard stripes.
- **QR codes, images** (drag and drop or paste), copies, darkness, saved **presets**. **Image and text together:** put the
  picture left, right, above, below or behind the text (and QR code), with a size control. **Image tab:** Floyd–Steinberg,
  ordered (Bayer) crosshatch or hard-cutoff dithering, brightness, contrast and gamma, and looks: pixelate (chunky
  handheld-camera dots), mirror, flip and invert. Transparent PNGs print on white and phone photos keep their orientation.
- **Save and share:** File > Save/Open composition keeps a whole label in one `.t003label` file (the image is embedded, so
  it works on another machine; drop one on the window to open it, or `t003-print --file x.t003label`). File > Export
  image writes the exact 1-bit label as a PNG, at printed size or enlarged 4×.
- Themes (View > Theme): Y2K candy plastic in blue or pink, gunmetal with LCD-green text, a four-shade olive
  "handheld" look (which also tints the preview; prints stay black on white), or the plain platform look.
- Help menu: version, an About box (with a printer-found check) and a manual **Check for updates** that compares your
  version with the latest GitHub release. It only runs when you ask.
- A CLI with the same options: `t003-print "NEON\nNIGHTS" --effect neon --frame brackets`.

## Install

Downloads are on the [Releases](../../releases) page. Every build runs a self-test (fonts, licences, icons, a Japanese
render, libusb) in CI before it is published.

| OS | Get | Needs | Notes |
|---|---|---|---|
| **Linux** (x86-64) | `T003-Label-Studio-*-x86_64.AppImage` | glibc 2.28 or newer: Ubuntu 20.04+, Debian 10+, RHEL/Alma/Rocky 8+, Fedora, Arch and anything newer | `chmod +x` and run. On X11 it needs `libxcb-cursor0`. If it doesn't start, run it as `./T003-Label-Studio-*.AppImage --appimage-extract-and-run` (no FUSE needed). Install the udev rule below so you can use the printer without root. |
| **Windows** (x64) | `…-windows-x64.zip` | Windows 10 or 11 | Unzip and run `T003 Label Studio.exe`. libusb needs the printer bound to the **WinUSB** driver (e.g. with [Zadig](https://zadig.akeo.ie/)), which stops Windows' own printing to that device. |
| **macOS** (Apple silicon or Intel) | `…-macos-arm64.zip` or `…-macos-x86_64.zip` | macOS 12 or newer | The app is unsigned: right-click → Open the first time. |

Not covered by a download? See the pip install below: it works on anything with Python 3.9+ and USB, including
Linux on ARM (Raspberry Pi), older macOS and Python-capable systems we don't build for.

> **What is tested.** Printing: Linux with real hardware only. Every release build runs its self-test in CI, and the
> Linux AppImage is self-tested in Ubuntu 20.04 and 24.04, Debian 11 and 12, AlmaLinux 8 and 9, Fedora and Arch
> containers. The macOS minimum (12) and the Linux minimum (glibc 2.28) are measured on each build, and the build
> fails if a dependency raises them. Printing from Windows and macOS hasn't been tried on a physical machine, and
> Windows on ARM should work through x64 emulation but is untested; reports welcome.

**Linux udev rule** (lets your user open the printer):
```
sudo cp packaging/70-t003-label-printer.rules /etc/udev/rules.d/
sudo udevadm control --reload   # then replug the printer
```

## With pip, on any system with Python 3.9+

```bash
pip install "t003-label-gui[gui] @ git+https://github.com/MiNombreEsPablo/t003-label-gui"   # the window and the CLI
pip install "t003-label-gui @ git+https://github.com/MiNombreEsPablo/t003-label-gui"        # only the CLI (no Qt)
```

pip picks the newest Qt that exists for your system, so this reaches older distros and Python versions than the
downloads above. The command-line tool `t003-print` needs no Qt at all, so it also runs on a Raspberry Pi, a server or
anything else with Python and USB; on platforms without a bundled libusb, install the system one (`apt install
libusb-1.0-0`). The window is `t003-gui`.

## From source

```bash
python -m venv .venv && .venv/bin/pip install -e '.[dev]'   # [dev] includes the window (PySide6) and pytest
.venv/bin/t003-gui          # the app
.venv/bin/t003-print --help # the CLI
.venv/bin/pytest            # tests, no printer needed
packaging/install.sh        # KDE/GNOME launcher, icons and a print-label shortcut
```

## How it works

The T003 speaks TSPL over a plain USB printer interface. The app renders a 384×224 dot label (58 mm paper, 203 dpi,
28 mm stickers), sends it as a TSPL bitmap with pyusb/libusb, and needs no CUPS or kernel driver. See
[AGENTS.md](AGENTS.md) for the hardware facts and the code layout.

## Roadmap

Ordered by priority, with no promised dates. Several ideas are inspired by 90s handheld cameras and their thermal
printers.

**Next**
- [ ] Publish to PyPI, so `pip install t003-label-gui` works without the git URL (the wheel is already built and tested in CI)
- [ ] Sliders (with a small value box) for brightness, contrast, gamma, cutoff and pixelate, plus a cache of the decoded
      photo so dragging stays smooth with phone-sized pictures
- [ ] Batch-print from a CSV (`{column}` placeholders in the text and QR fields)
- [ ] Undo/redo, then an album: recent and saved labels as a thumbnail gallery
- [ ] Stickers and stamps: a built-in set of our own pixel icons (fragile, this side up, warning, arrows, ...) to place on a label
- [ ] Poster mode: split one large image across several stickers, with alignment marks

**Later**
- [ ] Native Linux ARM64 and Windows ARM64 builds (newer ARM Linux needs glibc 2.39; until then use the pip install)
- [ ] More themes: Win95/98 grey, and user-defined colour themes
- [ ] Zoomable preview with a ruler/grid overlay
- [ ] Draw tool: freehand doodling on the label
- [ ] Webcam capture: take a photo and print it (needs Qt Multimedia, so a larger download)

**Needs hardware or research first**
- [ ] Hardware testing on Windows and macOS (CI builds them, but they are untested with a printer). Testers wanted.
- [ ] Windows printing through the spooler, so no Zadig/WinUSB driver is needed (needs a Windows machine to test)
- [ ] Bluetooth printing (USB only for now; first check whether the T003 has Bluetooth at all)

## Building releases

`python packaging/build.py` builds for the OS it runs on (PyInstaller does not cross-compile).
Bump `__version__` in `src/t003gui/__init__.py` first (the About box, `--version` and the package metadata all read it).
`.github/workflows/release.yml` builds Linux, Windows and macOS on tag push (`git tag v0.2.1 && git push --tags`; the tag must match `__version__`),
self-tests each, and attaches them to a GitHub release with checksums.

## Licence

MIT for the code (see [LICENSE](LICENSE)). The bundled fonts keep their own licences, mostly the SIL Open Font
License; all texts are in `src/t003gui/fonts/LICENSES/`.
