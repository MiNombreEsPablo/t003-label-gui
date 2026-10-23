<p align="center"><img src="packaging/icons/t003-label-gui-128.png" alt="T003 Label Studio icon" width="96"></p>

# T003 Label Studio

Design and print stickers on the **ORGBRO T003** USB thermal label printer, with a live preview of exactly what the
printer will burn. Text, QR codes and images, plus a pile of early-web and cyberpunk styling, and every font can print
Japanese (日本語).

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

| OS | Get | Notes |
|---|---|---|
| **Linux** | `T003-Label-Studio-*-x86_64.AppImage` | `chmod +x` and run. Needs `libxcb-cursor0` (Qt 6 on X11). Install the udev rule below so you can use the printer without root. |
| **Windows** | `…-windows-x64.zip` | Unzip and run `T003 Label Studio.exe`. libusb needs the printer bound to the **WinUSB** driver (e.g. with [Zadig](https://zadig.akeo.ie/)), which stops Windows' own printing to that device. |
| **macOS** | `…-macos-arm64.zip` | Apple silicon only. The app is unsigned: right-click → Open the first time. |

> **Tested on:** Linux with real hardware. The Windows and macOS builds are produced and self-tested by CI but
> printing from them has not been tried on a physical machine; reports welcome.

**Linux udev rule** (lets your user open the printer):
```
sudo cp packaging/70-t003-label-printer.rules /etc/udev/rules.d/
sudo udevadm control --reload   # then replug the printer
```

## From source

```bash
python -m venv .venv && .venv/bin/pip install -e '.[dev]'
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

**Now** (the next release)
- [x] Image and text on one label: the picture beside, above, below or behind the text
- [x] An Image panel: choice of dither (Floyd–Steinberg, ordered/Bayer, hard threshold), brightness, contrast and gamma
- [x] Image looks: pixelate (chunky low-res), mirror, flip, invert
- [x] A four-shade green "handheld" theme
- [ ] Screenshots in this README

**Next**
- [ ] Batch-print from a CSV (`{column}` placeholders in the text and QR fields)
- [ ] Undo/redo, then an album: recent and saved labels as a thumbnail gallery
- [ ] Stickers and stamps: a built-in set of our own pixel icons (fragile, this side up, warning, arrows, ...) to place on a label
- [ ] Poster mode: split one large image across several stickers, with alignment marks

**Later**
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
