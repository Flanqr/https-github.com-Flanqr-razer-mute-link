import json
import os
from pathlib import Path

APP_DIR = Path(os.getenv("APPDATA", "")) / "RazerMuteLink"
APP_DIR.mkdir(parents=True, exist_ok=True)
CONFIG_PATH = APP_DIR / "config.json"

DEFAULTS = {
    "target_mic_substring": "",
    "autostart_enabled": False,
    "listener_enabled": True
}

def load_config():
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {**DEFAULTS, **data}
        except Exception:
            pass
    return DEFAULTS.copy()

def save_config(cfg):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
