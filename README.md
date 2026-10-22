# t003-label-gui

A small desktop app for printing text, QR codes and images to the ORGBRO T003 thermal label printer (48 × 28 mm stickers) over USB, with a live preview of exactly what will be printed.

```bash
python -m venv --system-site-packages .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/t003-gui
```

The printer speaks TSPL; this talks to it directly via libusb (pyusb), so no CUPS or kernel printer driver is needed. Your user needs access to the USB device (on Arch/CachyOS, being in the `lp` group is enough).
