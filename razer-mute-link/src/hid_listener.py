import time
import threading
import pywinusb.hid as hid

RAZER_VID = 0x1532

class RazerMuteListener:
    def __init__(self, on_state):
        # on_state(muted: bool) -> None
        self._on_state = on_state
        self._devices = []
        self._running = False
        self._thread = None

    def _raw_handler_factory(self):
        def handler(data):
            # data[1] == 8 => muted, data[1] == 0 => unmuted
            b = data[1] if len(data) > 1 else None
            if b in (0, 8):
                self._on_state(b == 8)
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
            self._devices = hid.HidDeviceFilter(vendor_id=RAZER_VID).get_devices()
            handler = self._raw_handler_factory()
            for dev in self._devices:
                try:
                    dev.open(shared=True)
                    dev.set_raw_data_handler(handler)
                except Exception:
                    # Ignore interfaces we cannot open; others may still work
                    pass
            while self._running:
                time.sleep(0.1)
        finally:
            self.stop()
