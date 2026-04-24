"""AudioManager — centralizes all pygame.mixer interactions.

Usage:
    from src.utils.audio_manager import audio
    audio.init()                     # after pygame.init()
    audio.play_music("battle")       # start looping BGM
    audio.play_sfx("shoot")          # one-shot SFX
    audio.update_movement(moving)    # call every frame with bool

Volume API (for Settings screen):
    audio.set_sfx_volume(0.8)        # 0.0 – 1.0
    audio.set_music_volume(0.5)
    audio.sfx_volume / audio.music_volume  # read current values
"""

from __future__ import annotations

from pathlib import Path

import pygame

from src.utils.constants import SOUNDS_DIR


# ---------------------------------------------------------------------------
# File registry
# ---------------------------------------------------------------------------

# SFX: key → filename  (fully pre-loaded into memory)
_SFX_REGISTRY: dict[str, str] = {
    "shoot":        "sfx_shooting.mp3",
    "hit_ground":   "sfx_bullet_hit_ground.mp3",
    "hit_tank":     "sfx_bullet_hit_tank.mp3",
    "move":         "sfx_tank_moving.mp3",
    "angle":        "sfx_changing_angle.mp3",
    "click":        "click_sound.mp3",
}

# Music: key → filename  (streamed from disk)
_MUSIC_REGISTRY: dict[str, str] = {
    "menu":    "theme_music_background.mp3",
    "battle":  "theme_music_background.mp3",
    "victory": "music_when_victory.mp3",
    "lose":    "music_when_lose.mp3",
}

# Channel index reserved for the looping movement sound
_MOVE_CHANNEL_IDX = 0

# Fade duration (ms) for movement loop start/stop to avoid click artifacts
_MOVE_FADE_MS = 120

# Music tracks that should loop indefinitely
_LOOPING_MUSIC: frozenset[str] = frozenset({"menu", "battle"})


class AudioManager:
    """Centralised audio controller (module-level singleton)."""

    def __init__(self) -> None:
        self._sfx: dict[str, pygame.mixer.Sound] = {}
        self._ready = False
        self._current_music: str | None = None
        self._move_channel: pygame.mixer.Channel | None = None
        self._move_playing = False

        self.sfx_volume   = 0.8
        self.music_volume = 0.5

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def init(self) -> None:
        """Initialise mixer and pre-load all SFX. Call after pygame.init()."""
        try:
            pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=512)
            pygame.mixer.init()
            pygame.mixer.set_num_channels(16)
            self._move_channel = pygame.mixer.Channel(_MOVE_CHANNEL_IDX)
            self._load_sfx()
            self._ready = True
            print("[AudioManager] Mixer initialised OK")
        except Exception as exc:
            print(f"[AudioManager] WARNING: mixer failed to init — audio disabled ({exc})")

    def _load_sfx(self) -> None:
        for key, filename in _SFX_REGISTRY.items():
            path = SOUNDS_DIR / filename
            if not path.exists():
                print(f"[AudioManager] MISSING sfx: {filename}")
                continue
            try:
                snd = pygame.mixer.Sound(str(path))
                snd.set_volume(self.sfx_volume)
                self._sfx[key] = snd
                print(f"[AudioManager] Loaded sfx: {filename}")
            except Exception as exc:
                print(f"[AudioManager] ERROR loading {filename}: {exc}")

    # ------------------------------------------------------------------
    # SFX playback
    # ------------------------------------------------------------------

    def play_sfx(self, key: str) -> None:
        """Play a one-shot SFX by key. Silently no-ops if unavailable."""
        if not self._ready:
            return
        snd = self._sfx.get(key)
        if snd is None:
            return
        try:
            snd.play()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Movement loop
    # ------------------------------------------------------------------

    def update_movement(self, is_moving: bool) -> None:
        """Call every frame with whether the active tank is moving.

        Fades the movement loop in/out rather than cutting abruptly.
        """
        if not self._ready or self._move_channel is None:
            return

        snd = self._sfx.get("move")
        if snd is None:
            return

        if is_moving and not self._move_playing:
            self._move_channel.play(snd, loops=-1, fade_ms=_MOVE_FADE_MS)
            self._move_playing = True
        elif not is_moving and self._move_playing:
            self._move_channel.fadeout(_MOVE_FADE_MS)
            self._move_playing = False

    def stop_movement(self) -> None:
        """Immediately stop the movement loop (e.g. on turn change)."""
        if self._ready and self._move_channel is not None and self._move_playing:
            self._move_channel.fadeout(_MOVE_FADE_MS)
            self._move_playing = False

    # ------------------------------------------------------------------
    # Music
    # ------------------------------------------------------------------

    def play_music(self, key: str, fade_ms: int = 600) -> None:
        """Start a music track by key. No-op if the same track is already playing."""
        if not self._ready:
            return
        if self._current_music == key:
            return

        filename = _MUSIC_REGISTRY.get(key)
        if filename is None:
            print(f"[AudioManager] Unknown music key: {key}")
            return

        path = SOUNDS_DIR / filename
        if not path.exists():
            print(f"[AudioManager] MISSING music: {filename}")
            return

        try:
            loops = -1 if key in _LOOPING_MUSIC else 0
            pygame.mixer.music.load(str(path))
            pygame.mixer.music.set_volume(self.music_volume)
            pygame.mixer.music.play(loops=loops, fade_ms=fade_ms)
            self._current_music = key
        except Exception as exc:
            print(f"[AudioManager] ERROR playing music {filename}: {exc}")

    def stop_music(self, fade_ms: int = 600) -> None:
        """Fade out and stop current music."""
        if not self._ready:
            return
        try:
            pygame.mixer.music.fadeout(fade_ms)
            self._current_music = None
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Volume controls  (called by Settings screen in Phase 3)
    # ------------------------------------------------------------------

    def set_sfx_volume(self, volume: float) -> None:
        """Set SFX volume 0.0–1.0 and apply immediately to all loaded sounds."""
        self.sfx_volume = max(0.0, min(1.0, volume))
        for snd in self._sfx.values():
            snd.set_volume(self.sfx_volume)

    def set_music_volume(self, volume: float) -> None:
        """Set music volume 0.0–1.0 and apply to currently playing music."""
        self.music_volume = max(0.0, min(1.0, volume))
        if self._ready:
            try:
                pygame.mixer.music.set_volume(self.music_volume)
            except Exception:
                pass

    def teardown(self) -> None:
        """Clean up mixer on game exit."""
        if self._ready:
            try:
                pygame.mixer.music.stop()
                pygame.mixer.quit()
            except Exception:
                pass


# Module-level singleton
audio = AudioManager()
