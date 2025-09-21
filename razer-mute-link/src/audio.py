from pycaw.pycaw import AudioUtilities

def list_capture_devices():
    # Return input (capture) devices; pycaw exposes all endpoints, so filter by "Microphone"
    devices = []
    for d in AudioUtilities.GetAllDevices():
        name = (d.FriendlyName or "").strip()
        # Basic heuristic: contains "Microphone" or "Line In"
        if any(k in name.lower() for k in ["microphone", "mic", "line in"]):
            devices.append((name, d))
    # Fallback: if heuristic too strict, return all devices
    return devices or [(d.FriendlyName, d) for d in AudioUtilities.GetAllDevices()]

def get_endpoint_volume_by_name_substring(substring):
    if not substring:
        return None
    sub = substring.lower()
    for d in AudioUtilities.GetAllDevices():
        name = (d.FriendlyName or "").lower()
        if sub in name:
            return d.EndpointVolume
    return None

def get_endpoint_volume_exact(name_exact):
    for d in AudioUtilities.GetAllDevices():
        if (d.FriendlyName or "").strip() == name_exact.strip():
            return d.EndpointVolume
    return None

def is_muted(endpoint_volume):
    return endpoint_volume.GetMute() == 1

def set_mute(endpoint_volume, mute):
    endpoint_volume.SetMute(1 if mute else 0, None)
