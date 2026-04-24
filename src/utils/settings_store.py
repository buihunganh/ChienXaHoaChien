"""SettingsStore — reads/writes player preferences to assets/save/settings.json.

Design:
- Defaults are defined in code; file contents are overlaid on top
- Every load/save operation is wrapped in try/except — bad file → defaults
- Properties expose typed, clamped access to each setting
- No dependencies on AudioManager, MainMenu, or any game class

Usage:
    from src.utils.settings_store import settings
    settings.load()
    settings.sfx_volume   # float 0.0–1.0
    settings.sfx_volume = 0.8  # auto-saves to disk
"""

from __future__ import annotations

import json
from pathlib import Path

from src.utils.constants import ASSETS_DIR

_SAVE_DIR  = ASSETS_DIR / "save"
_SAVE_PATH = _SAVE_DIR / "settings.json"

_DEFAULTS: dict = {
    "sfx_volume":   0.8,
    "music_volume": 0.5,
    "fullscreen":   False,
    "max_unlocked_level": 1,
}


class SettingsStore:
    """Persistent settings backed by a JSON file."""

    def __init__(self) -> None:
        self._data: dict = dict(_DEFAULTS)

    # ------------------------------------------------------------------
    # Load / Save
    # ------------------------------------------------------------------

    def load(self) -> None:
        """Load settings from disk; silently falls back to defaults on any error."""
        try:
            if _SAVE_PATH.exists():
                raw = _SAVE_PATH.read_text(encoding="utf-8")
                file_data = json.loads(raw)
                # Overlay file data on top of defaults — unknown keys are ignored
                for key in _DEFAULTS:
                    if key in file_data:
                        self._data[key] = file_data[key]
        except Exception as exc:
            print(f"[SettingsStore] Could not load settings ({exc}) — using defaults")
            self._data = dict(_DEFAULTS)

    def save(self) -> None:
        """Write current settings to disk. Silently no-ops on failure."""
        try:
            _SAVE_DIR.mkdir(parents=True, exist_ok=True)
            _SAVE_PATH.write_text(
                json.dumps(self._data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception as exc:
            print(f"[SettingsStore] Could not save settings: {exc}")

    # ------------------------------------------------------------------
    # Typed properties
    # ------------------------------------------------------------------

    @property
    def sfx_volume(self) -> float:
        return float(self._data.get("sfx_volume", _DEFAULTS["sfx_volume"]))

    @sfx_volume.setter
    def sfx_volume(self, value: float) -> None:
        self._data["sfx_volume"] = max(0.0, min(1.0, float(value)))
        self.save()

    @property
    def music_volume(self) -> float:
        return float(self._data.get("music_volume", _DEFAULTS["music_volume"]))

    @music_volume.setter
    def music_volume(self, value: float) -> None:
        self._data["music_volume"] = max(0.0, min(1.0, float(value)))
        self.save()

    @property
    def fullscreen(self) -> bool:
        return bool(self._data.get("fullscreen", _DEFAULTS["fullscreen"]))

    @fullscreen.setter
    def fullscreen(self, value: bool) -> None:
        self._data["fullscreen"] = bool(value)
        self.save()

    @property
    def max_unlocked_level(self) -> int:
        return int(self._data.get("max_unlocked_level", _DEFAULTS["max_unlocked_level"]))

    @max_unlocked_level.setter
    def max_unlocked_level(self, value: int) -> None:
        self._data["max_unlocked_level"] = max(1, min(6, int(value)))
        self.save()


# Module-level singleton
settings = SettingsStore()
