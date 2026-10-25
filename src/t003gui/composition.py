"""Label composition files: a whole label design saved to / loaded from one self-contained file. Qt-free.

JSON, so it is diffable and survives version changes (unknown fields are ignored, a newer format is refused). Unlike a
preset (which lives in the app's config and only stores a path), a composition embeds its image, so the file still works on
another machine.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import json
import re
import tempfile
from dataclasses import asdict, replace
from pathlib import Path

from . import doodle
from .spec import IMAGE_SUFFIXES, LabelSpec

FORMAT = "t003-label"
VERSION = 1
SUFFIX = ".t003label"


def dumps(spec: LabelSpec) -> str:
    spec = replace(spec, doodle=doodle.canonical(spec.doodle))  # compact, whichever client drew it
    data = {"format": FORMAT, "version": VERSION, "spec": asdict(spec)}
    source = Path(spec.image_path) if spec.image_path else None
    if source and source.is_file():
        data["image"] = {"name": source.name, "data": base64.b64encode(source.read_bytes()).decode("ascii")}
        data["spec"]["image_path"] = ""  # a path on this machine means nothing in the file; the bytes travel instead
    return json.dumps(data, indent=2)


def loads(text: str, image_dir: Path | None = None) -> LabelSpec:
    """Parse a composition. An embedded image is written under `image_dir` (default: a temp folder)."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"not a label file ({e.msg})") from e
    if not isinstance(data, dict) or data.get("format") != FORMAT or not isinstance(data.get("spec"), dict):
        raise ValueError("not a T003 label file")
    version = data.get("version")
    if not isinstance(version, int) or version > VERSION:
        raise ValueError("this file was made by a newer version of T003 Label Studio")
    spec = LabelSpec.from_dict(data["spec"])
    image = data.get("image")
    if isinstance(image, dict):
        try:
            blob = base64.b64decode(image.get("data", ""), validate=True)
        except (binascii.Error, ValueError) as e:
            raise ValueError("the embedded image is damaged") from e
        spec.image_path = str(_store_image(str(image.get("name", "")), blob, image_dir))
    return spec


def _store_image(name: str, blob: bytes, folder: Path | None) -> Path:
    folder = folder or Path(tempfile.gettempdir()) / "t003-label-gui" / "compositions"
    folder.mkdir(parents=True, exist_ok=True)
    suffix = Path(name).suffix.lower()
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(name).stem)[:40] or "image"
    # The content hash in the name keeps it unique and stable, and nothing from the file picks the directory.
    path = folder / f"{hashlib.sha256(blob).hexdigest()[:12]}-{stem}{suffix if suffix in IMAGE_SUFFIXES else '.png'}"
    if not path.exists():
        path.write_bytes(blob)
    return path


def save(path: Path | str, spec: LabelSpec) -> None:
    path = Path(path)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(dumps(spec), encoding="utf-8")
    tmp.replace(path)


def load(path: Path | str, image_dir: Path | None = None) -> LabelSpec:
    return loads(Path(path).read_text(encoding="utf-8"), image_dir)
