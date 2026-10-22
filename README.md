# t003-label-gui

A small desktop app for printing text, QR codes and images to the ORGBRO T003 thermal label printer (48 × 28 mm stickers) over USB, with a live preview of exactly what will be printed.

```bash
python -m venv --system-site-packages .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/t003-gui
```

Also installed: `t003-print` (CLI with the same options, `--preview out.png` to render without printing, `--preset NAME` to use a preset saved in the GUI). Run `packaging/install.sh` to add a KDE menu entry and a `~/.local/bin/print-label` shortcut for the CLI.

Text can use any installed font (family + bold toggle, resolved via fontconfig) and left/centre/right alignment (`--font`, `--bold/--no-bold`, `--align` on the CLI). Drop an image file onto the window to load it. Presets are saved to `~/.config/t003-label-gui/presets.json`.

The printer speaks TSPL; this talks to it directly via libusb (pyusb), so no CUPS or kernel printer driver is needed. Your user needs access to the USB device (on Arch/CachyOS, being in the `lp` group is enough).
