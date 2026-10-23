# AGENTS.md

Desktop GUI (PySide6) for the ORGBRO T003 USB thermal label printer.

## Commands

```bash
python -m venv --system-site-packages .venv   # PySide6 comes from the system package
.venv/bin/pip install -e '.[dev]'
.venv/bin/t003-gui                            # run the app
.venv/bin/t003-print "text" --qr URL          # CLI (same options as the GUI; --preview out.png to not print)
.venv/bin/pytest                              # tests (no printer needed)
packaging/install.sh                          # KDE launcher + ~/.local/bin/print-label wrapper
```

## Layout

- `src/t003gui/spec.py` — `LabelSpec` dataclass (everything a label can be) plus geometry constants and the allowed choices (`EFFECTS`, `BACKGROUNDS`, `BORDER_STYLES`, …). Presets are `asdict(LabelSpec)`, so new fields must have defaults.
- `src/t003gui/render.py` — Qt-free drawing: fonts via fontconfig (`font_path` resolves family→file; variable fonts load at their default weight so `_apply_weight` sets the weight axis for the bold toggle; `list_font_families` feeds the GUI picker), auto-fit text layers (shadow/outline/3D/glitch/neon/scanlines, synthetic italic), backgrounds (cached, seeded RNG so they are stable), borders, hazard bars, QR. Effect parameters scale with font size; glitch drops its fringe/gaps below ~24/30 dots because small text turns to mush. Text is positioned by measured ink bounds, not Pillow's bbox (side-bearings). Lines are laid out by `_layout` with a fixed pitch — never use `multiline_text` with `stroke_width`: Pillow widens the pitch by 2×stroke per line, so stroked passes (outline/3D/neon/halo) drift off the unstroked fill on lines 2+ (regression test in tests/test_render.py). Over a background pattern text gets a white halo. Nothing may be drawn below `SH` (tests enforce it).
- `src/t003gui/fonts.py` + `fonts/` — the **bundled** OFL fonts (21 families, ~17 MB, licences in `fonts/LICENSES/`), grouped by category for the GUI. `font_path` prefers these over fontconfig, so labels print identically on any machine. To add one: put the .ttf and its `LICENSE.<slug>` in `fonts/`, add a `BundledFont` entry; `tests/test_fonts.py` checks files, licence, coverage flag and Japanese support.
- **Japanese:** none of the Latin display fonts have kana/kanji. `render._FontSet` picks a font per glyph (cmap via fontTools): the primary font if it covers the character, else the bundled `Zen Kaku Gothic New` fallback; text is split into runs sharing one baseline (anchor `ls`). Fonts flagged `ja=True` cover Japanese in their own style (DotGothic16, Yusei Magic, Dela Gothic One, Stick, Zen Kaku). Any new bundled font must still print Japanese (test enforces).
- `src/t003gui/core.py` — builds the TSPL payload and sends it over USB with pyusb; re-exports spec/render names so callers use `core.X`.
- `src/t003gui/app.py` — the Qt window; live preview uses `core.to_bitmap`, so it shows exactly what will print. Tabs: Content / Text / Retro. The font picker is an editable combo showing the curated bundled set by default (grouped, previewed in each font; "Show all installed fonts" switches to `core.list_font_families()`, fontconfig names), NOT QFontComboBox: Qt lists variable-font instances as bogus families ("Akatab Black") and foundry duplicates that fontconfig cannot resolve. Supports drag-and-drop of image files and named presets.
- `src/t003gui/presets.py` — Qt-free preset store, JSON at `$XDG_CONFIG_HOME/t003-label-gui/presets.json`. Shared by the GUI and `t003-print --preset NAME`.
- `src/t003gui/cli.py` — `t003-print`, installed as `~/.local/bin/print-label` by `packaging/install.sh`.
- `packaging/` — `.desktop` launcher template and the installer (rewrites the Exec path for this checkout).

## Hardware facts (found by calibration — don't re-derive)

- USB `0483:5743`, TSPL, bulk OUT `0x01` / IN `0x82`. Kernel 7.x has no `usblp`; no CUPS needed. Device node is group `lp`, no sudo.
- 58 mm paper, **384 printable dots** wide at 203 dpi. Label pitch is 240 dots (`SIZE 72 mm,30 mm`, `GAP 2 mm`), but the sticker is only **224 dots** (`core.SH`) tall; anything below that falls in the gap and is lost.
- TSPL `BITMAP` mode 0: bit 1 = white, 0 = black (same as Pillow mode "1").
- Status query `ESC !?`: `0x00` ready, `0x20` printing; bit flags in `core.STATUS_FLAGS`.
- Each real print uses a sticker — prefer `--preview`/the GUI preview and tests over test prints.
