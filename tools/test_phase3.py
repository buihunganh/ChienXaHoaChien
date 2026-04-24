import os
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame
pygame.init()

from src.utils.settings_store import settings
settings.load()
print("[OK] settings.sfx_volume  =", settings.sfx_volume)
print("[OK] settings.music_volume=", settings.music_volume)
print("[OK] settings.language    =", settings.language)
print("[OK] settings.fullscreen  =", settings.fullscreen)

from src.utils.strings import t, set_language
set_language("en")
print("[OK] t(menu_start) EN:", t("menu_start"))
set_language("vi")
print("[OK] t(menu_start) VI:", t("menu_start"))
print("[OK] t(settings_save) VI:", t("settings_save"))

pygame.display.set_mode((1280, 720))
from src.utils.asset_manager import assets
from src.utils.audio_manager import audio
assets.load_all()
audio.init()

from src.ui.settings_screen import SettingsScreen
ss = SettingsScreen()
print("[OK] SettingsScreen instantiated")

from src.ui.main_menu import MainMenu
mm = MainMenu()
print("[OK] MainMenu instantiated with SettingsScreen")

audio.teardown()
pygame.quit()
print("All Phase 3 checks passed.")
