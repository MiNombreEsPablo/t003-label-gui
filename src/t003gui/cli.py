"""Command-line printing: print-label "text" --qr URL --image FILE ..."""
from __future__ import annotations

import argparse
import sys

from . import core
from .presets import PresetStore

EXAMPLES = r"""
examples:
  print-label "Hello"                          auto-fit text
  print-label "Line 1\nLine 2" --border        multiple lines
  print-label "Left" --align left --font "Noto Sans Mono" --no-bold
  print-label "Wi-Fi" --qr "WIFI:S:x;;"        text left, QR right
  print-label --image art.png --threshold 160  hard cutoff, good for flat colours
  print-label --preset shelf --copies 3        saved GUI preset
  print-label "x" --preview out.png            render to PNG, don't print
"""


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(
        prog="print-label",
        description="Print to the ORGBRO T003 label printer (384x224 dots).",
        epilog=EXAMPLES,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("text", nargs="?", help=r"text to print (use \n for newlines)")
    p.add_argument("--qr", help="QR code content")
    p.add_argument("--image", help="image file to print")
    p.add_argument("--threshold", type=int, help="image: hard black/white cutoff 0-255 instead of dithering")
    p.add_argument("--font", help="font family, e.g. 'Noto Sans Mono' (default DejaVu Sans)")
    p.add_argument("--bold", action=argparse.BooleanOptionalAction, default=None, help="bold text (default on)")
    p.add_argument("--align", choices=core.ALIGNMENTS, help="text alignment (default center)")
    p.add_argument("--border", action="store_true", help="draw a border")
    p.add_argument("--copies", type=int, help="number of copies (default 1)")
    p.add_argument("--density", type=int, help="darkness 0-15 (default 7)")
    p.add_argument("--preset", help="start from a preset saved in the GUI; other flags override it")
    p.add_argument("--preview", metavar="PNG", help="write the rendered label to PNG instead of printing")
    args = p.parse_args(argv)

    spec = core.LabelSpec()
    if args.preset:
        spec = PresetStore().get(args.preset)
        if spec is None:
            p.error(f"no preset named {args.preset!r}")
    for field in ("text", "qr", "threshold", "copies", "density", "font", "bold", "align"):
        if getattr(args, field) is not None:
            setattr(spec, field, getattr(args, field))
    if args.image:
        spec.image_path = args.image
    if args.border:
        spec.border = True
    if not (spec.text or spec.qr or spec.image_path):
        p.error("give some text, --qr, --image or --preset")

    try:
        if args.preview:
            core.to_bitmap(core.render(spec)).save(args.preview)
            return
        for problem in core.print_label(spec):
            print(f"printer: {problem}", file=sys.stderr)
    except (core.PrinterError, OSError) as e:
        sys.exit(f"error: {e}")


if __name__ == "__main__":
    main()
