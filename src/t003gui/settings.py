"""Small remembered settings for the web UI's desktop shell (the printer choice, later more), as one JSON file under
the XDG config dir next to the presets. Qt-free, and tolerant: a missing or damaged file just means "no settings"."""
from __future__ import annotations

import json
import os
from pathlib import Path


def default_path() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config"
    return Path(base) / "t003-label-gui" / "settings.json"


class Settings:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or default_path()

    def _read(self) -> dict:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        return data if isinstance(data, dict) else {}

    def get(self, key: str, default=None):
        return self._read().get(key, default)

    def set(self, key: str, value) -> None:
        """Remember a JSON-serialisable value (None forgets the key). Raises OSError if the file can't be written."""
        data = self._read()
        if value is None:
            data.pop(key, None)
        else:
            data[key] = value
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self.path)  # a crash mid-write never leaves half a file behind
