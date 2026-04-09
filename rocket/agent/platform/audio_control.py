"""Windows master audio control helpers."""

from __future__ import annotations

import platform


def _require_windows() -> None:
    if platform.system() != "Windows":
        raise RuntimeError("Audio control is only supported on Windows")


def get_volume_interface():
    """Return the Windows endpoint volume COM interface."""
    _require_windows()

    try:
        from ctypes import POINTER, cast
        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    except ImportError as exc:
        raise RuntimeError("pycaw/comtypes are not installed") from exc

    devices = AudioUtilities.GetSpeakers()
    interface = devices.Activate(
        IAudioEndpointVolume._iid_, CLSCTX_ALL, None
    )
    return cast(interface, POINTER(IAudioEndpointVolume))


def mute() -> None:
    volume = get_volume_interface()
    volume.SetMute(1, None)


def unmute() -> None:
    volume = get_volume_interface()
    volume.SetMute(0, None)


def is_muted() -> bool:
    volume = get_volume_interface()
    return bool(volume.GetMute())


def get_volume_scalar() -> float:
    volume = get_volume_interface()
    return float(volume.GetMasterVolumeLevelScalar())


def set_volume_scalar(value: float) -> float:
    volume = get_volume_interface()
    clamped = max(0.0, min(1.0, float(value)))
    volume.SetMasterVolumeLevelScalar(clamped, None)
    return clamped


def adjust_volume(delta: float) -> float:
    current = get_volume_scalar()
    return set_volume_scalar(current + float(delta))
