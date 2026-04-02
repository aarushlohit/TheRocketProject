"""Best-effort runtime dependency checks for the Linux backend."""

from __future__ import annotations

import asyncio
import os
import platform
import subprocess
from pathlib import Path

from agent.utils.logger import get_logger


logger = get_logger(__name__)

HAS_WMCTRL = False
HAS_SCROT = False
HAS_XDG_OPEN = False


async def check_and_prepare_dependencies() -> None:
    """Check required tools, attempt safe installs, and never crash startup."""
    global HAS_WMCTRL, HAS_SCROT, HAS_XDG_OPEN

    logger.info("[INFO] Checking system dependencies...")
    os_name, distro_id = detect_environment()

    if os_name == "linux":
        distro_label = distro_id or "unknown"
        logger.info(f"[INFO] Predicted environment: Linux ({distro_label})")
    else:
        logger.info(f"[INFO] Predicted environment: {os_name}")

    HAS_XDG_OPEN = await _check_dependency(
        command="xdg-open",
        package_name="xdg-utils",
        os_name=os_name,
        distro_id=distro_id,
        required=True,
        fallback_message="webbrowser fallback enabled",
    )
    HAS_WMCTRL = await _check_dependency(
        command="wmctrl",
        package_name="wmctrl",
        os_name=os_name,
        distro_id=distro_id,
        required=False,
        fallback_message="pkill fallback enabled",
    )
    HAS_SCROT = await _check_dependency(
        command="scrot",
        package_name="scrot",
        os_name=os_name,
        distro_id=distro_id,
        required=False,
        fallback_message="PIL screenshot fallback enabled",
    )


def is_installed(command: str) -> bool:
    """Return True when a command is available in PATH."""
    try:
        result = subprocess.run(
            [command, "--version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False
    except Exception:
        return False


def detect_environment() -> tuple[str, str | None]:
    """Predict the current OS and Linux distro when possible."""
    os_name = platform.system().lower()
    if os_name != "linux":
        return os_name, None

    os_release = _read_os_release()
    distro_id = os_release.get("id")
    if distro_id:
        return os_name, distro_id.lower()

    distro_like = os_release.get("id_like")
    if distro_like:
        return os_name, distro_like.split()[0].lower()

    return os_name, None


async def _check_dependency(
    *,
    command: str,
    package_name: str,
    os_name: str,
    distro_id: str | None,
    required: bool,
    fallback_message: str,
) -> bool:
    if is_installed(command):
        logger.info(f"[OK] {command} installed")
        return True

    logger.warning(f"[WARN] {command} missing -> attempting install")
    install_ok = await _attempt_install(
        package_name=package_name,
        os_name=os_name,
        distro_id=distro_id,
    )

    if install_ok and is_installed(command):
        logger.info(f"[OK] {command} installed")
        return True

    severity = "FAIL" if required else "FAIL"
    logger.error(f"[{severity}] {command} install failed -> {fallback_message}")
    return False


async def _attempt_install(
    *,
    package_name: str,
    os_name: str,
    distro_id: str | None,
) -> bool:
    if os_name != "linux":
        return False

    if not _is_arch_linux(distro_id):
        logger.warning(
            f"[WARN] Auto-install unsupported for distro '{distro_id or 'unknown'}'"
        )
        return False

    command = _build_install_command(package_name)
    if command is None:
        logger.warning("[WARN] Could not build install command")
        return False

    try:
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        returncode = await asyncio.wait_for(process.wait(), timeout=45)
        return returncode == 0
    except asyncio.TimeoutError:
        logger.error(f"[FAIL] Install timed out for {package_name}")
        return False
    except FileNotFoundError:
        logger.error(f"[FAIL] Installer not available for {package_name}")
        return False
    except Exception:
        logger.exception(f"[FAIL] Install crashed for {package_name}")
        return False


def _build_install_command(package_name: str) -> list[str] | None:
    if os.geteuid() == 0:
        return ["pacman", "-S", "--noconfirm", package_name]

    if is_installed("sudo"):
        return ["sudo", "-n", "pacman", "-S", "--noconfirm", package_name]

    return None


def _is_arch_linux(distro_id: str | None) -> bool:
    return distro_id in {"arch", "archlinux", "manjaro", "endeavouros"}


def _read_os_release() -> dict[str, str]:
    os_release_path = Path("/etc/os-release")
    if not os_release_path.exists():
        return {}

    result: dict[str, str] = {}
    for line in os_release_path.read_text(encoding="utf-8").splitlines():
        cleaned = line.strip()
        if not cleaned or cleaned.startswith("#") or "=" not in cleaned:
            continue

        key, value = cleaned.split("=", 1)
        result[key.lower()] = value.strip().strip('"').strip("'")

    return result
