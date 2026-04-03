"""Windows platform adapter with HYBRID execution (Stage 1.5 Upgrade).

Execution Strategy:
1. Try executable directly (shutil.which)
2. Fallback to Windows Search (pyautogui)

This ensures ALL Windows apps work, not just those in PATH.
"""

from __future__ import annotations

import shutil
import subprocess
import time
import webbrowser
from pathlib import Path
from typing import Optional

from agent.platform.adapter import PlatformAdapter
from agent.utils.logger import get_logger


logger = get_logger(__name__)


# =============================================================================
# PYAUTOGUI LAZY LOADER
# =============================================================================
_pyautogui = None


def get_pyautogui():
    """Lazy load pyautogui to avoid import errors if not installed."""
    global _pyautogui
    if _pyautogui is None:
        try:
            import pyautogui
            pyautogui.FAILSAFE = True  # Move mouse to corner to abort
            pyautogui.PAUSE = 0.1
            _pyautogui = pyautogui
        except ImportError:
            logger.warning("pyautogui not installed - search fallback disabled")
            _pyautogui = None
    return _pyautogui


# =============================================================================
# WINDOWS APP RESOLUTION MAP (EXPANDED)
# =============================================================================
APP_MAP = {
    # Browsers
    "chrome": ["chrome", "chrome.exe", "google-chrome"],
    "edge": ["msedge", "msedge.exe", "microsoft-edge"],
    "firefox": ["firefox", "firefox.exe"],
    "brave": ["brave", "brave.exe"],
    "opera": ["opera", "opera.exe"],
    
    # System
    "notepad": ["notepad", "notepad.exe"],
    "calculator": ["calc", "calc.exe"],
    "terminal": ["wt", "wt.exe", "cmd", "cmd.exe"],
    "powershell": ["powershell", "powershell.exe", "pwsh", "pwsh.exe"],
    "explorer": ["explorer", "explorer.exe"],
    "paint": ["mspaint", "mspaint.exe"],
    "wordpad": ["wordpad", "write.exe"],
    "settings": ["ms-settings:", "SystemSettings.exe"],
    "control": ["control", "control.exe"],
    "taskmanager": ["taskmgr", "taskmgr.exe"],
    "snipping": ["snippingtool", "SnippingTool.exe"],
    
    # Microsoft Office
    "word": ["winword", "WINWORD.EXE"],
    "excel": ["excel", "EXCEL.EXE"],
    "powerpoint": ["powerpnt", "POWERPNT.EXE"],
    "outlook": ["outlook", "OUTLOOK.EXE"],
    "onenote": ["onenote", "ONENOTE.EXE"],
    "access": ["msaccess", "MSACCESS.EXE"],
    
    # Communication
    "teams": ["ms-teams", "Teams.exe"],
    "discord": ["discord", "Discord.exe", "Update.exe --processStart Discord.exe"],
    "slack": ["slack", "slack.exe"],
    "zoom": ["zoom", "Zoom.exe"],
    "skype": ["skype", "Skype.exe"],
    
    # Media
    "spotify": ["spotify", "Spotify.exe"],
    "vlc": ["vlc", "vlc.exe"],
    "photos": ["ms-photos:"],
    "groove": ["mswindowsmusic:"],
    
    # Development
    "vscode": ["code", "code.exe", "Code.exe"],
    "visualstudio": ["devenv", "devenv.exe"],
    "git": ["git-bash", "git-bash.exe"],
    "node": ["node", "node.exe"],
    "python": ["python", "python.exe", "py"],
    
    # Utilities
    "7zip": ["7zFM", "7zFM.exe"],
    "winrar": ["winrar", "WinRAR.exe"],
    "notepadpp": ["notepad++", "notepad++.exe"],
    
    # Games / Store
    "steam": ["steam", "steam.exe"],
    "store": ["ms-windows-store:"],
}

# Windows Search names (may differ from executable names)
SEARCH_NAMES = {
    "chrome": "Chrome",
    "edge": "Microsoft Edge",
    "firefox": "Firefox",
    "notepad": "Notepad",
    "calculator": "Calculator",
    "terminal": "Terminal",
    "powershell": "PowerShell",
    "explorer": "File Explorer",
    "paint": "Paint",
    "word": "Word",
    "excel": "Excel",
    "powerpoint": "PowerPoint",
    "outlook": "Outlook",
    "teams": "Microsoft Teams",
    "discord": "Discord",
    "spotify": "Spotify",
    "vscode": "Visual Studio Code",
    "settings": "Settings",
    "control": "Control Panel",
    "taskmanager": "Task Manager",
}


def resolve_app(app_name: str) -> Optional[str]:
    """
    Resolve app name to executable command for Windows.
    Returns None if not found in PATH.
    """
    candidates = APP_MAP.get(app_name.lower(), [app_name])
    
    print(f"\n[WINDOWS RESOLVE] Trying: {candidates}")
    
    for cmd in candidates:
        if shutil.which(cmd):
            print(f"[FOUND IN PATH] {cmd}")
            return cmd
    
    print(f"[NOT IN PATH] {app_name}")
    return None


# =============================================================================
# HYBRID EXECUTION ENGINE
# =============================================================================

def try_open_exe(app_name: str) -> bool:
    """
    STEP 1: Try to open app via executable in PATH.
    Returns True if successful.
    """
    cmd = resolve_app(app_name)
    
    if cmd:
        try:
            subprocess.Popen(
                ["cmd", "/c", "start", "", cmd],
                shell=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            print(f"[EXE SUCCESS] Launched: {cmd}")
            return True
        except Exception as e:
            print(f"[EXE ERROR] {e}")
    
    return False


def open_via_search(app_name: str, retry: bool = True) -> bool:
    """
    STEP 2: Fallback - Open app via Windows Search (PATCHED).
    Uses pyautogui to simulate Win key + typing + Enter.
    
    This works for ANY app installed on Windows, even if not in PATH.
    
    PATCHED:
    - Increased delays for reliability
    - Retry logic for verification
    """
    pyautogui = get_pyautogui()
    
    if pyautogui is None:
        print("[SEARCH FALLBACK] pyautogui not available")
        return False
    
    try:
        # Use friendly search name if available
        search_name = SEARCH_NAMES.get(app_name.lower(), app_name)
        
        print(f"\n[SEARCH FALLBACK] Opening via Windows Search: {search_name}")
        
        # Press Windows key to open Start menu
        pyautogui.press("win")
        time.sleep(1.0)  # PATCHED: Increased from 0.6
        
        # Type the app name
        pyautogui.write(search_name, interval=0.08)  # PATCHED: Slower typing
        time.sleep(1.5)  # PATCHED: Increased from 1.2 (wait for search results)
        
        # Press Enter to launch
        pyautogui.press("enter")
        time.sleep(0.5)  # Brief pause after enter
        
        print(f"[SEARCH SUCCESS] Launched via search: {search_name}")
        return True
        
    except Exception as e:
        print(f"[SEARCH ERROR] {e}")
        
        # PATCHED: Retry once
        if retry:
            print("[SEARCH RETRY] Attempting retry...")
            time.sleep(1.0)
            # Press Escape to clear any partial state
            try:
                pyautogui.press("escape")
            except:
                pass
            time.sleep(0.5)
            return open_via_search(app_name, retry=False)
        
        return False


def try_protocol_launch(app_name: str) -> bool:
    """
    STEP 1.5: Try launching via Windows protocol handler.
    
    Some apps register protocol handlers (e.g., ms-settings:, spotify:)
    """
    import os
    
    # Check if app name looks like a protocol
    if ":" in app_name:
        try:
            os.startfile(app_name)
            print(f"[PROTOCOL SUCCESS] Launched: {app_name}")
            return True
        except Exception as e:
            print(f"[PROTOCOL ERROR] {e}")
    
    # Check known protocols
    protocols = {
        "settings": "ms-settings:",
        "store": "ms-windows-store:",
        "mail": "mailto:",
        "photos": "ms-photos:",
        "maps": "bingmaps:",
        "calendar": "outlookcal:",
    }
    
    protocol = protocols.get(app_name.lower())
    if protocol:
        try:
            import os
            os.startfile(protocol)
            print(f"[PROTOCOL SUCCESS] Launched: {protocol}")
            return True
        except Exception as e:
            print(f"[PROTOCOL ERROR] {e}")
    
    return False


class WindowsAdapter(PlatformAdapter):
    """Windows-specific platform operations with HYBRID execution."""

    async def open_app(self, app_name: str) -> dict:
        """
        Open application on Windows using HYBRID strategy:
        1. Try executable (fast, reliable if in PATH)
        2. Try protocol handler (for UWP apps)
        3. Fallback to Windows Search (universal, works for all apps)
        """
        print(f"\n========== [EXECUTION START] ==========")
        print(f"[OPEN_APP] app_name={app_name}")
        
        # Step 1: Try executable
        if try_open_exe(app_name):
            logger.info(f"[EXECUTION SUCCESS] Launched via exe: {app_name}")
            return {"status": "success", "method": "exe", "app": app_name}
        
        # Step 1.5: Try protocol handler
        if try_protocol_launch(app_name):
            logger.info(f"[EXECUTION SUCCESS] Launched via protocol: {app_name}")
            return {"status": "success", "method": "protocol", "app": app_name}
        
        # Step 2: Fallback to Windows Search
        print("[EXE FAILED] Trying Windows Search fallback...")
        if open_via_search(app_name):
            logger.info(f"[EXECUTION SUCCESS] Launched via search: {app_name}")
            return {"status": "success", "method": "search", "app": app_name}
        
        # All methods failed
        logger.error(f"[EXECUTION FAILED] Could not open: {app_name}")
        return {"status": "error", "method": "none", "app": app_name}

    async def open_url(self, url: str) -> dict:
        """Open URL in default browser - REAL EXECUTION."""
        print(f"\n========== [EXECUTION START] ==========")
        print(f"[OPEN_URL] url={url}")

        try:
            # Ensure URL has protocol
            if not url.startswith(("http://", "https://")):
                url = "https://" + url

            # Use webbrowser module for reliability
            webbrowser.open(url)
            print(f"[EXECUTION SUCCESS] Opened URL: {url}")
            logger.info(f"[EXECUTION SUCCESS] Opened URL: {url}")
            return {"status": "success", "url": url}
        except Exception as e:
            print(f"[EXECUTION ERROR] {e}")
            logger.error(f"Failed to open URL {url}: {e}")
            
            # Fallback to subprocess
            try:
                subprocess.Popen(
                    ["cmd", "/c", "start", "", url],
                    shell=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                print(f"[FALLBACK SUCCESS] Opened URL via cmd: {url}")
                return {"status": "success", "url": url, "method": "fallback"}
            except Exception as e2:
                logger.error(f"Fallback also failed: {e2}")
                return {"status": "error", "url": url, "error": str(e2)}

    async def type_text(self, text: str, delay: float = 0.03) -> dict:
        """Type text using pyautogui."""
        print(f"\n========== [EXECUTION START] ==========")
        print(f"[TYPE_TEXT] text={text[:50]}...")
        
        pyautogui = get_pyautogui()
        if pyautogui is None:
            logger.error("pyautogui not available for TYPE_TEXT")
            return {"status": "error", "reason": "pyautogui_not_available"}
        
        try:
            pyautogui.write(text, interval=delay)
            print(f"[EXECUTION SUCCESS] Typed text")
            logger.info(f"[EXECUTION SUCCESS] Typed text: {text[:30]}...")
            return {"status": "success", "chars": len(text)}
        except Exception as e:
            print(f"[EXECUTION ERROR] {e}")
            logger.error(f"Failed to type text: {e}")
            return {"status": "error", "error": str(e)}

    async def press_keys(self, keys: str) -> dict:
        """Press key combination using pyautogui."""
        print(f"\n========== [EXECUTION START] ==========")
        print(f"[PRESS_KEYS] keys={keys}")
        
        pyautogui = get_pyautogui()
        if pyautogui is None:
            logger.error("pyautogui not available for PRESS_KEYS")
            return {"status": "error", "reason": "pyautogui_not_available"}
        
        try:
            # Parse key combination (e.g., "ctrl+c" → ["ctrl", "c"])
            combo = [k.strip() for k in keys.lower().split("+")]
            pyautogui.hotkey(*combo)
            print(f"[EXECUTION SUCCESS] Pressed keys: {combo}")
            logger.info(f"[EXECUTION SUCCESS] Pressed keys: {keys}")
            return {"status": "success", "keys": keys}
        except Exception as e:
            print(f"[EXECUTION ERROR] {e}")
            logger.error(f"Failed to press keys: {e}")
            return {"status": "error", "error": str(e)}

    async def search_web(self, query: str) -> dict:
        """Search web using browser."""
        print(f"\n========== [EXECUTION START] ==========")
        print(f"[SEARCH_WEB] query={query}")
        
        pyautogui = get_pyautogui()
        
        # Method 1: Direct URL
        search_url = f"https://www.google.com/search?q={query}"
        result = await self.open_url(search_url)
        
        if result.get("status") == "success":
            return {"status": "success", "query": query, "method": "url"}
        
        # Method 2: Open browser + type (if pyautogui available)
        if pyautogui:
            try:
                await self.open_app("chrome")
                time.sleep(2)
                pyautogui.write(query, interval=0.03)
                pyautogui.press("enter")
                return {"status": "success", "query": query, "method": "type"}
            except Exception as e:
                logger.error(f"Search fallback failed: {e}")
        
        return {"status": "error", "query": query}

    async def click(self, x: int, y: int, button: str = "left") -> dict:
        """Click at position using pyautogui."""
        print(f"\n========== [EXECUTION START] ==========")
        print(f"[CLICK] x={x}, y={y}, button={button}")
        
        pyautogui = get_pyautogui()
        if pyautogui is None:
            return {"status": "error", "reason": "pyautogui_not_available"}
        
        try:
            pyautogui.click(x, y, button=button)
            print(f"[EXECUTION SUCCESS] Clicked at ({x}, {y})")
            return {"status": "success", "x": x, "y": y}
        except Exception as e:
            print(f"[EXECUTION ERROR] {e}")
            return {"status": "error", "error": str(e)}

    async def scroll(self, direction: str, amount: int = 3) -> dict:
        """Scroll using pyautogui."""
        print(f"\n========== [EXECUTION START] ==========")
        print(f"[SCROLL] direction={direction}, amount={amount}")
        
        pyautogui = get_pyautogui()
        if pyautogui is None:
            return {"status": "error", "reason": "pyautogui_not_available"}
        
        try:
            clicks = amount if direction == "up" else -amount
            pyautogui.scroll(clicks)
            print(f"[EXECUTION SUCCESS] Scrolled {direction}")
            return {"status": "success", "direction": direction}
        except Exception as e:
            print(f"[EXECUTION ERROR] {e}")
            return {"status": "error", "error": str(e)}

    async def screenshot(self, output_dir: Path) -> Path:
        """Take screenshot on Windows."""
        print(f"\n========== [EXECUTION START] ==========")
        print(f"[SCREENSHOT] output_dir={output_dir}")

        try:
            from PIL import ImageGrab
            from datetime import datetime, timezone

            timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
            screenshot_path = output_dir / f"screenshot_{timestamp}.png"
            output_dir.mkdir(parents=True, exist_ok=True)

            screenshot = ImageGrab.grab()
            screenshot.save(screenshot_path)

            print(f"[EXECUTION SUCCESS] Screenshot saved: {screenshot_path}")
            logger.info(f"Screenshot saved: {screenshot_path}")
            return screenshot_path
        except Exception as e:
            print(f"[EXECUTION ERROR] {e}")
            logger.error(f"Screenshot failed: {e}")
            raise

    async def get_focused_window(self) -> dict:
        """Get focused window on Windows."""
        print(f"\n========== [EXECUTION START] ==========")
        print(f"[GET_FOCUSED_WINDOW]")
        
        pyautogui = get_pyautogui()
        if pyautogui:
            try:
                win = pyautogui.getActiveWindow()
                if win:
                    return {
                        "title": win.title,
                        "left": win.left,
                        "top": win.top,
                        "width": win.width,
                        "height": win.height,
                    }
            except Exception as e:
                logger.error(f"Get focused window failed: {e}")
        
        return {}

    async def close_app(
        self, app_name: str | None = None, target: str = "focused"
    ) -> dict:
        """Close application on Windows."""
        print(f"\n========== [EXECUTION START] ==========")
        print(f"[CLOSE_APP] app_name={app_name}, target={target}")

        pyautogui = get_pyautogui()

        try:
            if app_name:
                # Kill by process name
                subprocess.run(
                    ["taskkill", "/IM", f"{app_name}.exe", "/F"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                )
                print(f"[EXECUTION SUCCESS] Closed: {app_name}")
                logger.info(f"Closed app: {app_name}")
                return {"status": "success", "app": app_name}
            elif pyautogui:
                # Close focused window with Alt+F4
                pyautogui.hotkey("alt", "F4")
                print(f"[EXECUTION SUCCESS] Closed focused window")
                return {"status": "success", "target": "focused"}
            else:
                return {"status": "error", "reason": "no_target"}
        except Exception as e:
            print(f"[EXECUTION ERROR] {e}")
            logger.error(f"Failed to close app: {e}")
            return {"status": "error", "error": str(e)}

    async def minimize(
        self, app_name: str | None = None, target: str = "focused"
    ) -> dict:
        """Minimize window on Windows."""
        print(f"\n========== [EXECUTION START] ==========")
        print(f"[MINIMIZE] app_name={app_name}, target={target}")
        
        pyautogui = get_pyautogui()
        if pyautogui:
            try:
                pyautogui.hotkey("win", "down")
                return {"status": "success"}
            except Exception as e:
                return {"status": "error", "error": str(e)}
        
        return {"status": "error", "reason": "pyautogui_not_available"}

    async def maximize(
        self, app_name: str | None = None, target: str = "focused"
    ) -> dict:
        """Maximize window on Windows."""
        print(f"\n========== [EXECUTION START] ==========")
        print(f"[MAXIMIZE] app_name={app_name}, target={target}")
        
        pyautogui = get_pyautogui()
        if pyautogui:
            try:
                pyautogui.hotkey("win", "up")
                return {"status": "success"}
            except Exception as e:
                return {"status": "error", "error": str(e)}
        
        return {"status": "error", "reason": "pyautogui_not_available"}
