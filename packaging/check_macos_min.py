"""Report the oldest macOS a built .app runs on: the highest minimum version declared by any Mach-O file inside it.

    python packaging/check_macos_min.py "dist/T003 Label Studio.app" [--max 12.0]

With --max the exit status is 1 if anything needs a newer macOS, so a dependency bump that quietly raises the floor
(Qt's wheels did: 11 -> 12 -> 13 -> 14) fails the build instead of shipping.
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

MAGIC = {b"\xfe\xed\xfa\xce", b"\xfe\xed\xfa\xcf", b"\xce\xfa\xed\xfe", b"\xcf\xfa\xed\xfe", b"\xca\xfe\xba\xbe", b"\xbe\xba\xfe\xca"}


def version(text: str) -> tuple[int, ...]:
    return tuple(int(part) for part in text.split("."))


def minimums(path: Path) -> list[tuple[int, ...]]:
    """Every deployment target in one Mach-O file (a universal binary has one per architecture)."""
    out = subprocess.run(["otool", "-l", str(path)], capture_output=True, text=True).stdout
    found = [version(m) for m in re.findall(r"^\s+minos (\d+(?:\.\d+)+)", out, re.M)]  # LC_BUILD_VERSION
    found += [version(m) for m in re.findall(r"LC_VERSION_MIN_MACOSX\s+cmdsize \d+\s+version (\d+(?:\.\d+)+)", out)]
    return found


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("app", type=Path)
    parser.add_argument("--max", help="fail if any file needs a newer macOS than this, e.g. 12.0")
    args = parser.parse_args()

    worst: dict[Path, tuple[int, ...]] = {}
    for path in args.app.rglob("*"):
        if path.is_symlink() or not path.is_file():
            continue
        with open(path, "rb") as f:
            if f.read(4) not in MAGIC:
                continue
        found = minimums(path)
        if found:
            worst[path] = max(found)
    if not worst:
        print("no Mach-O files found")
        return 1
    ranked = sorted(worst.items(), key=lambda kv: kv[1], reverse=True)
    floor = ranked[0][1]
    print(f"{len(worst)} Mach-O files; the app needs macOS {'.'.join(map(str, floor))} or newer. The most demanding:")
    for path, v in ranked[:6]:
        print(f"  {'.'.join(map(str, v)):>6}  {path.relative_to(args.app)}")
    if args.max and floor > version(args.max):
        print(f"FAIL: more than the allowed macOS {args.max}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
