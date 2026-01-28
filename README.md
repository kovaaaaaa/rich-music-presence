# Rich Music Presence

Display your Apple Music playback on your Discord profile with rich presence, album art, and a polished desktop UI.

## Features
- Real-time Apple Music detection
- Discord Rich Presence with track details and artwork
- macOS support (Music.app) and Windows 10/11 support (Apple Music app via GSMTC)
- Modern UI with album art, progress, and background art
- Tray mode: close the window and keep presence running

## Requirements
- Python 3.9+ recommended
- Discord desktop app running
- Apple Music:
  - macOS: Music.app
  - Windows 10/11: Apple Music app

### Python packages
- `PySide6`
- `pypresence`
- `requests`
- Windows only: `winsdk` (for GSMTC)

Install:
```bash
pip install -r requirements.txt
```
On Windows:
```bash
pip install winsdk
```

## Running the App (GUI)
```bash
python app.py
```
Click **Connect Now** to start presence updates.

### Background / Tray
- Closing the window hides it to the system tray and keeps presence running.
- Use the tray icon menu to show or quit.

## CLI Mode (Legacy)
If you want the simple console loop:
```bash
python main.py
```

## How It Works
- **core/music_macos.py**: AppleScript integration with Music.app (macOS)
- **core/music_windows.py**: GSMTC integration for Apple Music (Windows 10/11)
- **core/discord_rpc.py**: Discord Rich Presence API wiring
- **ui/worker.py**: Background worker thread polling Apple Music and updating Discord
- **ui/main_window.py**: UI, animations, tray behavior, and updates

## Configuration
No config file is required. The app auto-detects OS and uses the correct music source:
- macOS → Music.app
- Windows → Apple Music (GSMTC)

## Build macOS .app
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install pyinstaller

pyinstaller --windowed --name "Rich Music Presence" \
  --icon "logo.png" \
  --add-data "logo.png:." \
  app.py
```

Output:
```
dist/Rich Music Presence.app
```

## Build DMG (optional)
Using `dmgbuild`:
```bash
pip install dmgbuild
dmgbuild -s dmgbuild/settings.py "Rich Music Presence" "RichMusicPresence.dmg"
```

## Notes
- Discord must be running for presence updates.
- If Apple Music is paused or stopped, the presence is cleared.

## Troubleshooting
- **No presence updates**: Make sure Discord is open and Apple Music is playing.
- **Windows music not detected**: Install `winsdk` and ensure Apple Music is the active media session.
- **macOS not detected**: Allow Music.app access for AppleScript if prompted.

## License
See `LICENSE`.
