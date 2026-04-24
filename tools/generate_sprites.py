"""
generate_sprites.py — Phase 1 asset generation script.

Generates all tank (body, turret, barrel) and HUD sprites programmatically using
pygame so pixel dimensions and alpha channels are exact.

Run once from the project root:
    python tools/generate_sprites.py
"""

import sys
from pathlib import Path

# Ensure project root on path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pygame

pygame.init()
# Headless: create a dummy display so convert_alpha works
pygame.display.set_mode((1, 1), pygame.NOFRAME)


TANKS_DIR = ROOT / "assets" / "images" / "tanks"
UI_DIR    = ROOT / "assets" / "images" / "ui"
TANKS_DIR.mkdir(parents=True, exist_ok=True)
UI_DIR.mkdir(parents=True, exist_ok=True)


def save(surface: pygame.Surface, path: Path) -> None:
    pygame.image.save(surface, str(path))
    print(f"  [OK] {path.relative_to(ROOT)}")


# ---------------------------------------------------------------------------
# TANK BODY — 96×44 px canvas (body hull + track strip)
# Colors: green=(80,180,90) red=(210,60,60)  matching constants.py
# ---------------------------------------------------------------------------
BODY_W, BODY_H = 96, 44          # canvas
HULL_W, HULL_H = 64, 24          # hull rectangle
TRACK_W, TRACK_H = 70, 10        # track strip

def make_body(color: tuple, highlight: tuple, track_color: tuple) -> pygame.Surface:
    surf = pygame.Surface((BODY_W, BODY_H), pygame.SRCALPHA)
    cx, cy = BODY_W // 2, BODY_H // 2

    # Track strip (bottom)
    track_rect = pygame.Rect(0, 0, TRACK_W, TRACK_H)
    track_rect.center = (cx, cy + 10)
    pygame.draw.rect(surf, track_color, track_rect, border_radius=4)

    # Track ridges
    for i in range(5):
        rx = track_rect.left + 6 + i * 13
        pygame.draw.rect(surf, (20, 20, 20), (rx, track_rect.top + 2, 6, TRACK_H - 4), border_radius=2)

    # Hull body
    hull_rect = pygame.Rect(0, 0, HULL_W, HULL_H)
    hull_rect.center = (cx, cy - 4)
    pygame.draw.rect(surf, color, hull_rect, border_radius=6)

    # Hull highlight (top edge shimmer)
    hilite_rect = pygame.Rect(hull_rect.left + 6, hull_rect.top + 3, hull_rect.width - 12, 5)
    pygame.draw.rect(surf, highlight, hilite_rect, border_radius=3)

    # Hull bottom shadow
    shadow_rect = pygame.Rect(hull_rect.left + 4, hull_rect.bottom - 5, hull_rect.width - 8, 4)
    pygame.draw.rect(surf, (max(0, color[0]-40), max(0, color[1]-40), max(0, color[2]-40)), shadow_rect, border_radius=2)

    return surf

GREEN       = (80, 180, 90)
GREEN_HI    = (130, 220, 140)
RED         = (210, 60, 60)
RED_HI      = (240, 110, 110)
TRACK_DARK  = (35, 35, 35)

print("\nGenerating tank bodies...")
save(make_body(GREEN, GREEN_HI, TRACK_DARK), TANKS_DIR / "tank_green_body.png")
save(make_body(RED,   RED_HI,   TRACK_DARK), TANKS_DIR / "tank_red_body.png")


# ---------------------------------------------------------------------------
# TANK TURRET — 36×36 px canvas, circle dome with highlight
# ---------------------------------------------------------------------------
TURRET_CANVAS = 36
TURRET_R      = 13

def make_turret(color: tuple, highlight: tuple) -> pygame.Surface:
    surf = pygame.Surface((TURRET_CANVAS, TURRET_CANVAS), pygame.SRCALPHA)
    cx = cy = TURRET_CANVAS // 2

    # Shadow circle (slightly offset down-right)
    shadow_col = (max(0, color[0]-50), max(0, color[1]-50), max(0, color[2]-50))
    pygame.draw.circle(surf, shadow_col, (cx+2, cy+2), TURRET_R)

    # Main dome
    pygame.draw.circle(surf, color, (cx, cy), TURRET_R)

    # Highlight dot (top-left)
    pygame.draw.circle(surf, highlight, (cx - 4, cy - 4), 5)

    # Thin dark outline
    pygame.draw.circle(surf, (20, 20, 20), (cx, cy), TURRET_R, width=2)

    return surf

print("\nGenerating tank turrets...")
save(make_turret(GREEN, GREEN_HI), TANKS_DIR / "tank_green_turret.png")
save(make_turret(RED,   RED_HI),   TANKS_DIR / "tank_red_turret.png")


# ---------------------------------------------------------------------------
# TANK BARREL — 76×14 px canvas
# Left 38px = transparent padding (pivot center), Right 38px = barrel tube
# ---------------------------------------------------------------------------
BARREL_W, BARREL_H = 76, 14
BARREL_COLOR  = (45, 45, 45)
BARREL_HI     = (90, 90, 90)

def make_barrel() -> pygame.Surface:
    surf = pygame.Surface((BARREL_W, BARREL_H), pygame.SRCALPHA)
    # Only the RIGHT half is drawn; left half stays transparent
    tube_rect = pygame.Rect(BARREL_W // 2, 3, BARREL_W // 2 - 2, BARREL_H - 6)
    pygame.draw.rect(surf, BARREL_COLOR, tube_rect, border_radius=3)

    # Taper: slightly narrower at tip
    tip_rect = pygame.Rect(BARREL_W - 8, 4, 8, BARREL_H - 8)
    pygame.draw.rect(surf, (30, 30, 30), tip_rect, border_radius=2)

    # Highlight stripe
    hilite_rect = pygame.Rect(BARREL_W // 2 + 2, 4, BARREL_W // 2 - 10, 3)
    pygame.draw.rect(surf, BARREL_HI, hilite_rect, border_radius=2)

    return surf

print("\nGenerating barrel...")
save(make_barrel(), TANKS_DIR / "tank_barrel.png")
# Both tank colors share the same barrel sprite
import shutil
shutil.copy(str(TANKS_DIR / "tank_barrel.png"), str(TANKS_DIR / "tank_green_barrel.png"))
shutil.copy(str(TANKS_DIR / "tank_barrel.png"), str(TANKS_DIR / "tank_red_barrel.png"))
print(f"  [OK] assets/images/tanks/tank_green_barrel.png (copy)")
print(f"  [OK] assets/images/tanks/tank_red_barrel.png (copy)")


# ---------------------------------------------------------------------------
# HUD PANELS
# panel_left  — 360×80 px, blue-bordered frame
# panel_right — 360×80 px, red-bordered frame
# shield_vs   — 130×130 px, hexagonal split shield
# power_bar_bg — 64×270 px, vertical bar background
# ---------------------------------------------------------------------------

def make_panel(border_color: tuple, width: int = 360, height: int = 80) -> pygame.Surface:
    surf = pygame.Surface((width, height), pygame.SRCALPHA)
    bg_color = (18, 28, 52, 210)           # dark navy, semi-transparent
    inner_color = (12, 22, 44, 230)

    # Outer frame
    pygame.draw.rect(surf, bg_color, (0, 0, width, height), border_radius=14)
    # Inner inset
    pygame.draw.rect(surf, inner_color, (6, 6, width-12, height-12), border_radius=10)
    # Glowing border
    pygame.draw.rect(surf, border_color, (0, 0, width, height), width=3, border_radius=14)
    # Inner border highlight
    lighter = tuple(min(255, c + 40) for c in border_color)
    pygame.draw.rect(surf, lighter, (3, 3, width-6, height-6), width=1, border_radius=12)

    return surf

def make_shield_vs() -> pygame.Surface:
    size = 130
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    cx = cy = size // 2

    # Hexagon points
    import math
    points = []
    for k in range(6):
        angle = math.radians(k * 60 - 30)
        points.append((cx + int(56 * math.cos(angle)), cy + int(56 * math.sin(angle))))

    # Left half (blue)
    blue_pts = [p for p in points if p[0] <= cx] + [(cx, 10), (cx, size-10)]
    pygame.draw.polygon(surf, (52, 124, 210, 230), points)   # full blue first
    # Right half (red) by drawing right side over
    right_pts = [p for p in points if p[0] >= cx] + [(cx, 10), (cx, size-10)]
    pygame.draw.polygon(surf, (200, 50, 65, 230), right_pts)

    # Silver border
    pygame.draw.polygon(surf, (210, 220, 235), points, width=4)

    return surf

def make_power_bar_bg() -> pygame.Surface:
    w, h = 64, 270
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    bg = (18, 35, 72, 220)
    pygame.draw.rect(surf, bg, (0, 0, w, h), border_radius=14)
    pygame.draw.rect(surf, (55, 110, 190), (0, 0, w, h), width=3, border_radius=14)
    return surf

print("\nGenerating HUD panels...")
save(make_panel((47, 123, 178)),  UI_DIR / "panel_left.png")
save(make_panel((186, 67, 86)),   UI_DIR / "panel_right.png")
save(make_shield_vs(),            UI_DIR / "shield_vs.png")
save(make_power_bar_bg(),         UI_DIR / "power_bar_bg.png")

print("\n✅ All sprites generated successfully!")
pygame.quit()
