# AGENTS.md

Desktop GUI (PySide6) for the ORGBRO T003 USB thermal label printer.

## Commands

```bash
python -m venv --system-site-packages .venv   # PySide6 comes from the system package
.venv/bin/pip install -e '.[dev]'
.venv/bin/t003-gui                            # run the app
.venv/bin/t003-print "text" --qr URL          # CLI (same options as the GUI; --preview out.png to not print)
.venv/bin/pytest                              # tests (no printer needed)
packaging/install.sh                          # KDE launcher, icons + ~/.local/bin/print-label wrapper
.venv/bin/t003-gui --selftest                 # verifies fonts/licences/assets/libusb/render (also what CI runs on built apps)
python packaging/build.py                     # PyInstaller build for the current OS (dist/); make_appimage.sh wraps the Linux one
```

## Layout

- `src/t003gui/spec.py` — `LabelSpec` dataclass (everything a label can be) plus geometry constants and the allowed choices (`EFFECTS`, `BACKGROUNDS`, `BORDER_STYLES`, …). Presets are `asdict(LabelSpec)`, so new fields must have defaults.
- `src/t003gui/render.py` — Qt-free drawing: fonts via fontconfig (`font_path` resolves family→file; variable fonts load at their default weight so `_apply_weight` sets the weight axis for the bold toggle; `list_font_families` feeds the GUI picker), auto-fit text layers (shadow/outline/3D/glitch/neon/scanlines, synthetic italic), backgrounds (cached, seeded RNG so they are stable), borders, hazard bars, QR. Effect parameters scale with font size; glitch drops its fringe/gaps below ~24/30 dots because small text turns to mush. Text is positioned by measured ink bounds, not Pillow's bbox (side-bearings). Lines are laid out by `_layout` with a fixed pitch — never use `multiline_text` with `stroke_width`: Pillow widens the pitch by 2×stroke per line, so stroked passes (outline/3D/neon/halo) drift off the unstroked fill on lines 2+ (regression test in tests/test_render.py). Over a background pattern text gets a white halo. Nothing may be drawn below `SH` (tests enforce it).
- `src/t003gui/fonts.py` + `fonts/` — the **bundled** OFL fonts (23 families incl. DejaVu, ~20 MB, licences in `fonts/LICENSES/`), grouped by category for the GUI. `font_path` prefers these over fontconfig, so labels print identically on any machine. To add one: put the .ttf and its `LICENSE.<slug>` in `fonts/`, add a `BundledFont` entry; `tests/test_fonts.py` checks files, licence, coverage flag and Japanese support.
- **Japanese:** none of the Latin display fonts have kana/kanji. `render._FontSet` picks a font per glyph (cmap via fontTools): the primary font if it covers the character, else the bundled `Zen Kaku Gothic New` fallback; text is split into runs sharing one baseline (anchor `ls`). Fonts flagged `ja=True` cover Japanese in their own style (DotGothic16, Yusei Magic, Dela Gothic One, Stick, Zen Kaku). Any new bundled font must still print Japanese (test enforces).
- `src/t003gui/core.py` — builds the TSPL payload and sends it over USB with pyusb; re-exports spec/render names so callers use `core.X`.
- `src/t003gui/app.py` — the Qt window: arranges the panels (tabs: Content / Text / Retro, plus the Output box), the preset bar, the preview and the Print button, and handles drag-and-drop/paste of images. Live preview uses `core.to_bitmap`, so it shows exactly what will print. `MainWindow.spec()` / `set_spec()` just merge/dispatch to the panels. The font picker is an editable combo showing the curated bundled set by default (grouped, previewed in each font; "Show all installed fonts" switches to `core.list_font_families()`, fontconfig names), NOT QFontComboBox: Qt lists variable-font instances as bogus families ("Akatab Black") and foundry duplicates that fontconfig cannot resolve. Supports drag-and-drop of image files and named presets.
- `src/t003gui/panels.py` — the editing controls as self-contained widgets (`ContentPanel`, `TextPanel`, `RetroPanel`, `OutputPanel`). Each owns its widgets, maps its slice of `LabelSpec` via `read()`/`write(spec)` and emits `changed`; a test checks that every spec field belongs to exactly one panel. Layout is the window's job, so a new layout (side modules etc.) only rearranges panels. A new `LabelSpec` field goes into a panel's `read`/`write`.
- `src/t003gui/theme.py` — the `Theme` dataclass (colours, bevels, radii as CSS fragments), the built-ins `Y2K_BLUE`, `Y2K_PINK` (a `dataclasses.replace` of blue: colours only) and `GUNMETAL` in `THEMES`, one `stylesheet(theme)` template, and the `Banner` widget (styled by `Theme.banner`). The stylesheet is set on the **main window**, never the app, and the image file dialog is opened unparented: that keeps the system dialog unstyled (a parented dialog inherits the sheet). Choice is stored in QSettings (`theme`: a key or `system`; the old `y2k` bool is migrated). To add a theme: fill in a `Theme`, add it to `THEMES` (the View > Theme menu is built from that). QSS can't draw triangles, so arrow PNGs live in `assets/` (`arrow-*.png` navy, `arrow-*-lcd.png` green, selected by `Theme.arrow`; generated by `packaging/make_icons.py`, as are the icons). Don't name a widget attribute after a QWidget method (`self.size` once shadowed `QWidget.size()`; a test guards this).
- `src/t003gui/selftest.py` — `--selftest`; set `T003_SELFTEST_LOG` to also write to a file (windowed Windows builds have no console).
- `src/t003gui/about.py` + the Help menu (in `app.py`, headed by a disabled "Version x.y.z" line): About box (version, printer found/not, bundled-font credit, repo link), "Check for updates…" (`updates.py`: on request only, one HEAD request to `github.com/<repo>/releases/latest` whose 302 target ends in the tag, compared numerically with `__version__`; shows the running version, then up to date / newer / couldn't check, with a link to the release page; no REST API, no auto-update, prereleases are never offered; tested against a local HTTP server, never GitHub), "Report an issue…", "Open presets folder". The version lives ONLY in `t003gui.__version__` (pyproject reads it dynamically; frozen builds have no package metadata); `release.yml` fails a tag that doesn't match it.
- `src/t003gui/presets.py` — Qt-free preset store, JSON at `$XDG_CONFIG_HOME/t003-label-gui/presets.json`. Shared by the GUI and `t003-print --preset NAME`.
- `src/t003gui/cli.py` — `t003-print`, installed as `~/.local/bin/print-label` by `packaging/install.sh`.
- `packaging/` — `build.py` (PyInstaller), `make_appimage.sh`, `make_icons.py` (icon.svg → PNG/ICO/ICNS + theme arrows; outputs are committed), launcher `.desktop`, udev rule, `install.sh`.
- `.github/workflows/release.yml` — Linux (ubuntu-22.04 for old glibc), Windows, macOS-arm64 builds, each self-tested; tagging `v*` publishes a GitHub release. Windows/macOS cannot be built or hardware-tested from the Linux dev machine: CI is the only way. Windows would need the WinUSB driver (Zadig) for libusb; a spooler-based RAW path would avoid that but doesn't exist yet.

## Hardware facts (found by calibration — don't re-derive)

- USB `0483:5743`, TSPL, bulk OUT `0x01` / IN `0x82`. Kernel 7.x has no `usblp`; no CUPS needed. Device node is group `lp`, no sudo.
- 58 mm paper, **384 printable dots** wide at 203 dpi. Label pitch is 240 dots (`SIZE 72 mm,30 mm`, `GAP 2 mm`), but the sticker is only **224 dots** (`core.SH`) tall; anything below that falls in the gap and is lost.
- TSPL `BITMAP` mode 0: bit 1 = white, 0 = black (same as Pillow mode "1").
- Status query `ESC !?`: `0x00` ready, `0x20` printing; bit flags in `core.STATUS_FLAGS`.
- Each real print uses a sticker — prefer `--preview`/the GUI preview and tests over test prints.
