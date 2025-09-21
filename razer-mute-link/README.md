# Razer Mute Link (Windows)

Link your Razer headset’s mute button to any selected microphone. Runs in the system tray, remembers settings, and supports auto-start.

## Features
- Shared-mode HID listener (works alongside Synapse)
- Mirrors Razer mute (data[1] == 8 muted, 0 unmuted) to your chosen mic
- Tray menu: enable/disable, select mic, toggle auto-start
- Config stored in %AppData%\RazerMuteLink\config.json

## Install
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pythonw.exe .\src\main.py
