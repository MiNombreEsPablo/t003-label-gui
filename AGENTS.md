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

- `src/t003gui/core.py` — Qt-free: renders a `LabelSpec` to a 1-bit bitmap, builds the TSPL payload, sends it over USB with pyusb. All printing logic lives here.
- `src/t003gui/app.py` — the Qt window; live preview uses `core.to_bitmap`, so it shows exactly what will print. Supports drag-and-drop of image files and named presets.
- `src/t003gui/presets.py` — Qt-free preset store, JSON at `$XDG_CONFIG_HOME/t003-label-gui/presets.json`. Shared by the GUI and `t003-print --preset NAME`.
- `src/t003gui/cli.py` — `t003-print`, installed as `~/.local/bin/print-label` by `packaging/install.sh`.
- `packaging/` — `.desktop` launcher template and the installer (rewrites the Exec path for this checkout).

## Hardware facts (found by calibration — don't re-derive)

- USB `0483:5743`, TSPL, bulk OUT `0x01` / IN `0x82`. Kernel 7.x has no `usblp`; no CUPS needed. Device node is group `lp`, no sudo.
- 58 mm paper, **384 printable dots** wide at 203 dpi. Label pitch is 240 dots (`SIZE 72 mm,30 mm`, `GAP 2 mm`), but the sticker is only **224 dots** (`core.SH`) tall; anything below that falls in the gap and is lost.
- TSPL `BITMAP` mode 0: bit 1 = white, 0 = black (same as Pillow mode "1").
- Status query `ESC !?`: `0x00` ready, `0x20` printing; bit flags in `core.STATUS_FLAGS`.
- Each real print uses a sticker — prefer `--preview`/the GUI preview and tests over test prints.
