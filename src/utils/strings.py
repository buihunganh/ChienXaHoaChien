"""String table and t() helper for Vietnamese/English localisation.

Usage:
    from src.utils.strings import t, set_language
    set_language("en")
    t("menu_start")   # → "Start"
    set_language("vi")
    t("menu_start")   # → "Bat dau"
"""

from __future__ import annotations

_STRINGS: dict[str, str] = {
    # ----- Main menu -----
    "menu_start":       "Start",
    "menu_settings":    "Settings",
    "menu_guide":       "How to Play",
    "menu_title":       "Tank Battle",
    "menu_quit_to_main":"Main Menu",

    # ----- Mode selection -----
    "mode_title":       "Game Mode",
    "mode_pvp_sub":     "2 Player battle",
    "mode_pve_sub":     "vs Computer (AI)",

    # ----- Difficulty -----
    "diff_title":       "Difficulty",
    "diff_easy":        "Easy",
    "diff_medium":      "Medium",
    "diff_hard":        "Hard",

    # ----- Level select -----
    "level_title":      "Select Level",
    "level_locked":     "Locked",
    "level_ready":      "Ready",

    # ----- HUD -----
    "hud_wind":         "Wind",
    "hud_power":        "Power",
    "hud_fuel":         "Fuel",
    "hud_player1":      "Player 1",
    "hud_player2":      "Player 2",
    "hud_hint_aim":     "Up/Down to aim",
    "hud_hint_charge":  "Space: hold to charge",
    "hud_hint_fire":    "Release Space to fire",
    "hud_ammo":         "Ammo",
    "hud_dmg":          "Dmg",

    # ----- Game over -----
    "gameover_win":     "Player {n} wins",
    "gameover_draw":    "Draw",
    "gameover_restart": "Press R to restart",

    # ----- Settings screen -----
    "settings_title":   "Settings",
    "settings_sfx":     "Sound FX",
    "settings_music":   "Music",
    "settings_fullscreen": "Fullscreen",
    "settings_save":    "Save & Close",
    "settings_save_resume": "Save & Resume",
    "settings_on":      "ON",
    "settings_off":     "OFF",

    # ----- Guide -----
    "guide_title":      "How to Play",
    "guide_line1":      "Left/Right: move tank (uses fuel)",
    "guide_line2":      "Up/Down (W/S): adjust barrel angle",
    "guide_line3":      "Hold Space: charge power, release: fire",
    "guide_line4":      "Wind and ammo type change each turn",
    "guide_line5":      "Reduce enemy HP to 0 to win",

    # ----- Back -----
    "back":             "< Back",
}

def t(key: str, **kwargs: object) -> str:
    """Return the localised string for *key*.
    Supports simple format placeholders: t("gameover_win", n=1).
    """
    text = _STRINGS.get(key, key)
    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, ValueError):
            pass
    return text
