"""Report the oldest glibc a built Linux app runs on: the highest GLIBC_x.y symbol any bundled binary asks for.

    python packaging/check_glibc.py dist/t003-label-studio [--max 2.28]

With --max the exit status is 1 if anything needs a newer glibc. PyInstaller copies in whatever libraries (and
libpython) the *build machine* has, so the floor is set by the build environment, not by Qt's wheels; this keeps a
change to that environment from quietly raising it. Needs `objdump` (binutils).
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path


def version(text: str) -> tuple[int, ...]:
    return tuple(int(part) for part in text.split("."))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--max", help="fail if any file needs a newer glibc than this, e.g. 2.28")
    args = parser.parse_args()

    worst: dict[Path, tuple[int, ...]] = {}
    for path in args.root.rglob("*"):
        if path.is_symlink() or not path.is_file():
            continue
        with open(path, "rb") as f:
            if f.read(4) != b"\x7fELF":
                continue
        out = subprocess.run(["objdump", "-T", str(path)], capture_output=True, text=True).stdout
        found = [version(m) for m in re.findall(r"GLIBC_(\d+\.\d+(?:\.\d+)?)", out)]
        if found:
            worst[path] = max(found)
    if not worst:
        print("no ELF files with glibc symbols found")
        return 1
    ranked = sorted(worst.items(), key=lambda kv: kv[1], reverse=True)
    floor = ranked[0][1]
    print(f"{len(worst)} ELF files; the app needs glibc {'.'.join(map(str, floor))} or newer. The most demanding:")
    for path, v in ranked[:6]:
        print(f"  {'.'.join(map(str, v)):>5}  {path.relative_to(args.root)}")
    if args.max and floor > version(args.max):
        print(f"FAIL: more than the allowed glibc {args.max}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
