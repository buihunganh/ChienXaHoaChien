"""AssetManager — module-level singleton for eager asset loading.

Usage from any module:
    from src.utils.asset_manager import assets
    bg = assets.get_image("bg/battlefield")   # pygame.Surface or None
    font = assets.get_font("gunbai_36")       # pygame.font.Font
"""

from __future__ import annotations

from pathlib import Path
import pygame

from src.utils.constants import FONTS_DIR, HEIGHT, IMAGES_DIR, WIDTH


# ---------------------------------------------------------------------------
# Image key → relative path inside IMAGES_DIR (no extension)
# ---------------------------------------------------------------------------
_IMAGE_REGISTRY: dict[str, str] = {
    # Backgrounds
    "bg/battlefield":   "bg/battlefield.png",
    "bg/main_menu":     "bg/main_menu.png",
    # Tank sprites
    "tanks/tank_green_body":    "tanks/tank_green_body.png",
    "tanks/tank_green_turret":  "tanks/tank_green_turret.png",
    "tanks/tank_green_barrel":  "tanks/tank_green_barrel.png",
    "tanks/tank_red_body":      "tanks/tank_red_body.png",
    "tanks/tank_red_turret":    "tanks/tank_red_turret.png",
    "tanks/tank_red_barrel":    "tanks/tank_red_barrel.png",
    # Bullet sprite
    "in_game/rocket":           "in_game/rocket_or_bullet.png",
    # UI / HUD panels
    "ui/panel_left":    "ui/panel_left.png",
    "ui/panel_right":   "ui/panel_right.png",
    "ui/shield_vs":     "ui/shield_vs.png",
    "ui/power_bar_bg":  "ui/power_bar_bg.png",
    # Icons
    "icons/volume":   "icons/volume_icon.png",
    "icons/victory":  "icons/Victory_popup_sign.png",
    "icons/lose":     "icons/Lose_popup_sign.png",
}

# Images that are loaded WITHOUT alpha and scaled to screen (solid full-screen backgrounds)
_SOLID_BG_KEYS: frozenset[str] = frozenset({"bg/battlefield", "bg/main_menu"})

# Font size variants to pre-load
_FONT_SIZES: tuple[int, ...] = (22, 28, 36, 52, 64)


class AssetManager:
    """Eager-loading, caching asset manager (module-level singleton)."""

    def __init__(self) -> None:
        self._images: dict[str, pygame.Surface | None] = {}
        self._fonts: dict[str, pygame.font.Font | None] = {}
        self._font_path: Path | None = None
        self._loaded = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_all(self) -> None:
        """Load every registered asset. Call once after pygame.display.set_mode()."""
        if self._loaded:
            return

        self._find_font()
        self._load_images()
        self._load_fonts()
        self._loaded = True

    def get_image(self, key: str) -> pygame.Surface | None:
        """Return cached Surface for *key*, or None if not available."""
        if not self._loaded:
            raise RuntimeError("AssetManager.load_all() must be called before get_image()")
        return self._images.get(key)

    def get_font(self, size: int) -> pygame.font.Font:
        """Return cached Font at *size* (px). Falls back to pygame default."""
        if not self._loaded:
            raise RuntimeError("AssetManager.load_all() must be called before get_font()")
        key = f"font_{size}"
        font = self._fonts.get(key)
        if font is None:
            font = pygame.font.Font(None, size)
        return font

    # ------------------------------------------------------------------
    # Internal loading helpers
    # ------------------------------------------------------------------

    def _find_font(self) -> None:
        """Locate any .ttf/.otf in FONTS_DIR; use first match."""
        for ext in ("*.ttf", "*.otf"):
            matches = list(FONTS_DIR.glob(ext))
            if matches:
                self._font_path = matches[0]
                print(f"[AssetManager] Font: {self._font_path.name}")
                return
        print("[AssetManager] WARNING: No custom font found in assets/fonts/ — using pygame default.")

    def _load_images(self) -> None:
        for key, rel_path in _IMAGE_REGISTRY.items():
            full_path = IMAGES_DIR / rel_path
            if not full_path.exists():
                print(f"[AssetManager] MISSING (non-fatal): {rel_path}")
                self._images[key] = None
                continue
            try:
                raw = pygame.image.load(str(full_path))
                if key in _SOLID_BG_KEYS:
                    surface = raw.convert()
                    # Scale to screen size once at load time — free at render time
                    if surface.get_size() != (WIDTH, HEIGHT):
                        surface = pygame.transform.scale(surface, (WIDTH, HEIGHT))
                else:
                    surface = raw.convert_alpha()
                self._images[key] = surface
                print(f"[AssetManager] Loaded: {rel_path} {raw.get_size()}")
            except Exception as exc:
                print(f"[AssetManager] ERROR loading {rel_path}: {exc}")
                self._images[key] = None

    def _load_fonts(self) -> None:
        font_path_str = str(self._font_path) if self._font_path else None
        for size in _FONT_SIZES:
            key = f"font_{size}"
            try:
                self._fonts[key] = pygame.font.Font(font_path_str, size)
            except Exception as exc:
                print(f"[AssetManager] Font size {size} failed: {exc} — using default")
                self._fonts[key] = pygame.font.Font(None, size)


# Module-level singleton — import this instance everywhere
assets = AssetManager()
