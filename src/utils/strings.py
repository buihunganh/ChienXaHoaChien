"""String table and t() helper for Vietnamese/English localisation.

Usage:
    from src.utils.strings import t, set_language
    set_language("en")
    t("menu_start")   # → "Start"
    set_language("vi")
    t("menu_start")   # → "Bat dau"
"""

from __future__ import annotations

_STRINGS: dict[str, dict[str, str]] = {
    # ----- Main menu -----
    "menu_start":       {"vi": "Bat dau",      "en": "Start"},
    "menu_settings":    {"vi": "Cai dat",       "en": "Settings"},
    "menu_guide":       {"vi": "Huong dan",     "en": "How to Play"},
    "menu_title":       {"vi": "Chien Xa Hoa Chien", "en": "Tank Battle"},

    # ----- Mode selection -----
    "mode_title":       {"vi": "Che do",        "en": "Game Mode"},
    "mode_pvp_sub":     {"vi": "Doi dau 2 nguoi choi", "en": "2 Player battle"},
    "mode_pve_sub":     {"vi": "Dau voi may (AI)",      "en": "vs Computer (AI)"},

    # ----- Difficulty -----
    "diff_title":       {"vi": "Do kho",        "en": "Difficulty"},
    "diff_easy":        {"vi": "De",            "en": "Easy"},
    "diff_medium":      {"vi": "Trung binh",    "en": "Medium"},
    "diff_hard":        {"vi": "Kho",           "en": "Hard"},

    # ----- Level select -----
    "level_title":      {"vi": "Man choi",      "en": "Select Level"},
    "level_locked":     {"vi": "Chua mo khoa",  "en": "Locked"},
    "level_ready":      {"vi": "San sang",      "en": "Ready"},

    # ----- HUD -----
    "hud_wind":         {"vi": "Gio",           "en": "Wind"},
    "hud_power":        {"vi": "Luc",           "en": "Power"},
    "hud_fuel":         {"vi": "Nhien lieu",    "en": "Fuel"},
    "hud_player1":      {"vi": "Nguoi choi 1",  "en": "Player 1"},
    "hud_player2":      {"vi": "Nguoi choi 2",  "en": "Player 2"},
    "hud_hint_aim":     {"vi": "Len/Xuong de ngam",     "en": "Up/Down to aim"},
    "hud_hint_charge":  {"vi": "Giu Space de nan luc",  "en": "Space: hold to charge"},
    "hud_hint_fire":    {"vi": "Tha Space de ban",       "en": "Release Space to fire"},
    "hud_ammo":         {"vi": "Dan",           "en": "Ammo"},
    "hud_dmg":          {"vi": "ST",            "en": "Dmg"},

    # ----- Game over -----
    "gameover_win":     {"vi": "Nguoi choi {n} thang", "en": "Player {n} wins"},
    "gameover_draw":    {"vi": "Hoa",           "en": "Draw"},
    "gameover_restart": {"vi": "Nhan R de choi lai",   "en": "Press R to restart"},

    # ----- Settings screen -----
    "settings_title":   {"vi": "Cai dat",       "en": "Settings"},
    "settings_sfx":     {"vi": "Am thanh",      "en": "Sound FX"},
    "settings_music":   {"vi": "Nhac nen",      "en": "Music"},
    "settings_fullscreen": {"vi": "Toan man hinh", "en": "Fullscreen"},
    "settings_language":{"vi": "Ngon ngu",      "en": "Language"},
    "settings_save":    {"vi": "Luu & Dong",    "en": "Save & Close"},
    "settings_on":      {"vi": "Bat",           "en": "ON"},
    "settings_off":     {"vi": "Tat",           "en": "OFF"},

    # ----- Guide -----
    "guide_title":      {"vi": "Huong dan",     "en": "How to Play"},
    "guide_line1":      {"vi": "Trai/Phai: di chuyen xe tang (ton nhien lieu)",
                         "en": "Left/Right: move tank (uses fuel)"},
    "guide_line2":      {"vi": "Len/Xuong (W/S): dieu chinh goc nong sung",
                         "en": "Up/Down (W/S): adjust barrel angle"},
    "guide_line3":      {"vi": "Nhan giu Space: nan luc, tha Space: ban",
                         "en": "Hold Space: charge power, release: fire"},
    "guide_line4":      {"vi": "Gio va loai dan thay doi moi luot",
                         "en": "Wind and ammo type change each turn"},
    "guide_line5":      {"vi": "Ha HP doi thu ve 0 de chien thang",
                         "en": "Reduce enemy HP to 0 to win"},

    # ----- Back -----
    "back":             {"vi": "< Quay lai",    "en": "< Back"},
}

_active_language: str = "vi"


def set_language(lang: str) -> None:
    """Switch the active language. Accepts 'vi' or 'en'."""
    global _active_language
    if lang in ("vi", "en"):
        _active_language = lang


def get_language() -> str:
    return _active_language


def t(key: str, **kwargs: object) -> str:
    """Return the localised string for *key* in the active language.

    Falls back to Vietnamese, then to the raw key if missing.
    Supports simple format placeholders: t("gameover_win", n=1).
    """
    entry = _STRINGS.get(key)
    if entry is None:
        return key  # unknown key: return key itself as fallback
    text = entry.get(_active_language) or entry.get("vi") or key
    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, ValueError):
            pass
    return text
