import threading
import time
import sys
import os
from pathlib import Path

import pywinusb.hid as hid
from pycaw.pycaw import AudioUtilities
import pystray
from PIL import Image, ImageDraw
import json
import winreg

# ---------------- CONFIG ----------------
APP_NAME = "RazerMuteLink"
APP_DIR = Path(os.getenv("APPDATA", "")) / APP_NAME
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
                return {**DEFAULTS, **json.load(f)}
        except Exception:
            pass
    return DEFAULTS.copy()

def save_config(cfg):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)

CFG = load_config()

# ---------------- AUDIO ----------------
def list_capture_devices():
    devices = []
    for d in AudioUtilities.GetAllDevices():
        name = (d.FriendlyName or "").strip()
        if any(k in name.lower() for k in ["microphone", "mic", "line in"]):
            devices.append(name)
    return devices or [(d.FriendlyName or "").strip() for d in AudioUtilities.GetAllDevices()]

def get_endpoint_volume_by_name_substring(substring):
    if not substring:
        return None
    sub = substring.lower()
    for d in AudioUtilities.GetAllDevices():
        if sub in (d.FriendlyName or "").lower():
            return d.EndpointVolume
    return None

def is_muted(endpoint_volume):
    return endpoint_volume.GetMute() == 1

def set_mute(endpoint_volume, mute):
    endpoint_volume.SetMute(1 if mute else 0, None)

# ---------------- AUTOSTART ----------------
def enable_autostart(exe_path=None):
    if exe_path is None:
        exe_path = Path(sys.argv[0])
        if exe_path.suffix.lower() != ".exe":
            pythonw = Path(sys.executable)
            exe_path = f'"{pythonw}" "{Path(__file__).resolve()}"'
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                        r"Software\Microsoft\Windows\CurrentVersion\Run",
                        0, winreg.KEY_SET_VALUE) as key:
        winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, str(exe_path))

def disable_autostart():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            r"Software\Microsoft\Windows\CurrentVersion\Run",
                            0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, APP_NAME)
    except FileNotFoundError:
        pass

def is_autostart_enabled():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            r"Software\Microsoft\Windows\CurrentVersion\Run",
                            0, winreg.KEY_READ) as key:
            winreg.QueryValueEx(key, APP_NAME)
            return True
    except FileNotFoundError:
        return False

# ---------------- HID LISTENER ----------------
class RazerMuteListener:
    def __init__(self, on_state):
        self._on_state = on_state
        self._devices = []
        self._running = False
        self._thread = None

    def _raw_handler_factory(self):
        def handler(data):
            if len(data) > 1 and data[1] in (0, 8):
                self._on_state(data[1] == 8)
        return handler

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        for dev in self._devices:
            try:
                dev.close()
            except Exception:
                pass
        self._devices.clear()

    def _run(self):
        try:
            self._devices = hid.HidDeviceFilter(vendor_id=0x1532).get_devices()
            handler = self._raw_handler_factory()
            for dev in self._devices:
                try:
                    dev.open(shared=True)
                    dev.set_raw_data_handler(handler)
                except Exception:
                    pass
            while self._running:
                time.sleep(0.1)
        finally:
            self.stop()

# ---------------- TRAY APP ----------------
listener_enabled = CFG.get("listener_enabled", True)
mic_endpoint = None
listener = None
last_mic_state = False

def ensure_mic_endpoint():
    global mic_endpoint
    sub = CFG.get("target_mic_substring", "")
    mic_endpoint = get_endpoint_volume_by_name_substring(sub) if sub else None
    return mic_endpoint

def on_razer_state(muted):
    if not listener_enabled:
        return
    ep = mic_endpoint or ensure_mic_endpoint()
    if ep:
        set_mute(ep, muted)

def create_icon_image(active=True):
    img = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    color = (40, 200, 120) if active else (150, 150, 150)
    d.ellipse([8, 8, 56, 56], fill=color, outline=(20, 20, 20))
    return img

def build_menu(icon):
    names = list_capture_devices()
    selected = CFG.get("target_mic_substring", "")

    def make_mic_item(name):
        def set_mic(icon, item):
            CFG["target_mic_substring"] = name
            save_config(CFG)
            ensure_mic_endpoint()
            icon.title = f"{APP_NAME} — {name}"
        return pystray.MenuItem(name, set_mic, checked=lambda item: selected.lower() in name.lower())

    mic_items = [make_mic_item(n) for n in names] if names else [pystray.MenuItem("(No devices)", None, enabled=False)]

    def toggle_listener(icon, item):
        global listener_enabled, last_mic_state
        if listener_enabled:
            if mic_endpoint:
                last_mic_state = is_muted(mic_endpoint)
                set_mute(mic_endpoint, False)  # Unmute when disabling
            listener_enabled = False
        else:
            listener_enabled = True
            if mic_endpoint:
                set_mute(mic_endpoint, last_mic_state)
        CFG["listener_enabled"] = listener_enabled
        save_config(CFG)
        icon.icon = create_icon_image(listener_enabled)

    def toggle_autostart(icon, item):
        if is_autostart_enabled():
            disable_autostart()
        else:
            enable_autostart()
        icon.menu = build_menu(icon)

    def quit_app(icon, item):
        if listener:
            listener.stop()
        icon.stop()

    return pystray.Menu(
        pystray.MenuItem("Listener enabled", toggle_listener, checked=lambda item: listener_enabled),
        pystray.MenuItem("Auto-start on login", toggle_autostart, checked=lambda item: is_autostart_enabled()),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Select microphone", pystray.Menu(*mic_items)),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Quit", quit_app),
    )

def run_tray():
    icon = pystray.Icon(APP_NAME, create_icon_image(listener_enabled), APP_NAME)
    icon.menu = build_menu(icon)
    sub = CFG.get("target_mic_substring", "")
    if sub:
        icon.title = f"{APP_NAME} — {sub}"
    icon.run()

def main():
    global listener
    ensure_mic_endpoint()
    listener = RazerMuteListener(on_state=on_razer_state)
    listener.start()
    run_tray()

if __name__ == "__main__":
    main()
