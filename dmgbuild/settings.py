# dmgbuild/settings.py
import os.path

APP_NAME = "Rich Music Presence"
APP_PATH = "dist/Rich Music Presence.app"
DMG_NAME = "RichMusicPresence"

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BG_PATH = os.path.join(ROOT_DIR, "dmgbackground.png")

application = APP_NAME
format = "UDZO"
size = "600M"

files = [APP_PATH]
symlinks = {"Applications": "/Applications"}

icon_size = 128
text_size = 12
badge_icon = os.path.join(ROOT_DIR, "logo.png")

background = BG_PATH
window_rect = ((200, 120), (640, 420))
icon_locations = {
    "Rich Music Presence.app": (180, 210),
    "Applications": (460, 210),
}

default_view = "icon-view"
show_status_bar = False
show_tab_view = False
show_toolbar = False
show_pathbar = False
show_sidebar = False
sidebar_width = 180

icon_view_settings = {
    "arrange_by": None,
    "grid_offset": (0, 0),
    "grid_spacing": 80,
    "label_pos": "bottom",
    "text_size": 12,
}
