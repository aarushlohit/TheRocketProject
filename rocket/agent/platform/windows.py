"""Windows platform adapter with HYBRID execution (Stage 1.5 Upgrade).

Execution Strategy:
1. Try executable directly (shutil.which)
2. Fallback to Windows Search (pyautogui)

This ensures ALL Windows apps work, not just those in PATH.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import time
import webbrowser
import ctypes
from pathlib import Path
from typing import Optional

from agent.platform.adapter import PlatformAdapter
from agent.platform.audio_control import adjust_volume, mute, unmute
from agent.platform.window_control import maximize_window, minimize_window, restore_window
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
    
    FIX 1: APP RESOLUTION FALLBACK
    If app not found in PATH, return raw app name instead of None.
    This ensures execution always proceeds to Windows Search fallback.
    """
    candidates = APP_MAP.get(app_name.lower(), [app_name])
    print(f"[RUNTIME VERIFY][resolve_app] file={__file__} app='{app_name}'")
    
    print(f"\n[WINDOWS RESOLVE] Trying: {candidates}")
    
    for cmd in candidates:
        if shutil.which(cmd):
            print(f"[FOUND IN PATH] {cmd}")
            return cmd
    
    # FIX 1: Return raw app name as fallback instead of None
    print(f"[NOT IN PATH] {app_name} - using raw name as fallback")
    return app_name


# =============================================================================
# FOCUS APP UTILITY (PATCH 4)
# =============================================================================

def focus_app(name: str) -> bool:
    """
    Focus a window by partial title match.
    
    Improves shortcut reliability by ensuring the target app has focus.
    """
    try:
        import pygetwindow as gw
        windows = gw.getWindowsWithTitle(name)
        for w in windows:
            try:
                w.activate()
                time.sleep(0.3)  # Brief pause for focus
                return True
            except Exception:
                continue
        return False
    except ImportError:
        logger.warning("pygetwindow not installed - focus_app disabled")
        return False
    except Exception as e:
        logger.error(f"focus_app failed: {e}")
        return False


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
    Deterministic human-like app launch.
    Uses Win -> type app name -> Enter.
    """
    pyautogui = get_pyautogui()
    
    if pyautogui is None:
        print("[SEARCH FALLBACK] pyautogui not available")
        return False
    
    try:
        search_name = app_name.strip()
        if not search_name:
            print("[SEARCH FALLBACK] Empty app name")
            return False

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

    async def show_desktop(self) -> dict:
        """Show the Windows desktop without pyautogui."""
        print(f"\n========== [EXECUTION START] ==========")
        print("[SHOW_DESKTOP]")

        try:
            user32 = ctypes.windll.user32
            user32.keybd_event(0x5B, 0, 0, 0)
            user32.keybd_event(0x44, 0, 0, 0)
            user32.keybd_event(0x44, 0, 2, 0)
            user32.keybd_event(0x5B, 0, 2, 0)
            return {"status": "success", "action": "show_desktop", "method": "user32.keybd_event"}
        except Exception as e:
            print(f"[EXECUTION ERROR] {e}")
            return {"status": "error", "error": str(e)}

    async def lock_screen(self) -> dict:
        """Lock the current Windows workstation deterministically.
        
        Uses multiple execution methods with fallback:
        1. subprocess.run (preferred - synchronous, reliable)
        2. ctypes.windll.user32.LockWorkStation (direct Windows API)
        """
        import platform
        import ctypes
        
        print(f"\n========== [EXECUTION START] ==========")
        print(f"[LOCK_SCREEN] Platform: {platform.system()}")
        
        if platform.system() != "Windows":
            print("[EXECUTION ERROR] Not running on Windows")
            return {"status": "error", "error": "Not running on Windows"}
        
        # Method 1: subprocess.run (synchronous, reliable)
        print("[EXECUTION] Attempting subprocess.run method...")
        try:
            result = subprocess.run(
                ["rundll32.exe", "user32.dll,LockWorkStation"],
                check=True,
                shell=False,
                capture_output=True,
                timeout=5
            )
            print(f"[EXECUTION SUCCESS] subprocess completed, returncode={result.returncode}")
            return {"status": "success", "method": "subprocess_rundll32"}
        except subprocess.TimeoutExpired:
            print("[EXECUTION WARNING] subprocess timed out, trying ctypes fallback...")
        except subprocess.CalledProcessError as e:
            print(f"[EXECUTION WARNING] subprocess failed: {e}, trying ctypes fallback...")
        except Exception as e:
            print(f"[EXECUTION WARNING] subprocess error: {e}, trying ctypes fallback...")
        
        # Method 2: ctypes direct Windows API call (most reliable)
        print("[EXECUTION] Attempting ctypes.windll method...")
        try:
            result = ctypes.windll.user32.LockWorkStation()
            if result:
                print(f"[EXECUTION SUCCESS] ctypes LockWorkStation returned {result}")
                return {"status": "success", "method": "ctypes_lockworkstation"}
            else:
                # Get last error for debugging
                error_code = ctypes.get_last_error()
                print(f"[EXECUTION ERROR] ctypes returned 0, GetLastError={error_code}")
                return {"status": "error", "error": f"LockWorkStation returned 0, error={error_code}"}
        except Exception as e:
            print(f"[EXECUTION ERROR] ctypes failed: {e}")
            logger.error(f"Failed to lock workstation: {e}")
            return {"status": "error", "error": str(e)}

    async def open_app(self, app_name: str) -> dict:
        """
        Open application on Windows using deterministic human-like control:
        Win -> type app -> Enter.
        If first attempt fails, retry once with an alternate shell launch.
        """
        print(f"\n========== [EXECUTION START] ==========")
        print(f"[OPEN_APP] app_name={app_name}")

        if open_via_search(app_name):
            logger.info(f"[EXECUTION SUCCESS] Launched via search: {app_name}")
            return {"status": "success", "method": "search", "app": app_name}

        # Self-correction retry once using alternate shell method.
        try:
            subprocess.Popen(
                ["cmd", "/c", "start", "", app_name],
                shell=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            logger.info(f"[EXECUTION SUCCESS] Launched via retry shell start: {app_name}")
            return {"status": "success", "method": "retry_shell_start", "app": app_name}
        except Exception as e:
            logger.error(f"[EXECUTION FAILED] Could not open {app_name}: {e}")
            return {"status": "error", "method": "none", "app": app_name, "error": str(e)}

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

    async def click(self, x: int = None, y: int = None, button: str = "left") -> dict:
        """Click at position using pyautogui."""
        print(f"\n========== [EXECUTION START] ==========")
        print(f"[CLICK] x={x}, y={y}, button={button}")
        
        pyautogui = get_pyautogui()
        if pyautogui is None:
            return {"status": "error", "reason": "pyautogui_not_available"}
        
        try:
            if x is not None and y is not None:
                pyautogui.click(x, y, button=button)
                print(f"[EXECUTION SUCCESS] Clicked at ({x}, {y})")
            else:
                # Click at current position
                pyautogui.click(button=button)
                print(f"[EXECUTION SUCCESS] Clicked at current position")
            return {"status": "success", "x": x, "y": y, "button": button}
        except Exception as e:
            print(f"[EXECUTION ERROR] {e}")
            return {"status": "error", "error": str(e)}

    async def double_click(self, x: int = None, y: int = None) -> dict:
        """Double click at position using pyautogui."""
        print(f"\n========== [EXECUTION START] ==========")
        print(f"[DOUBLE_CLICK] x={x}, y={y}")
        
        pyautogui = get_pyautogui()
        if pyautogui is None:
            return {"status": "error", "reason": "pyautogui_not_available"}
        
        try:
            if x is not None and y is not None:
                pyautogui.doubleClick(x, y)
                print(f"[EXECUTION SUCCESS] Double-clicked at ({x}, {y})")
            else:
                pyautogui.doubleClick()
                print(f"[EXECUTION SUCCESS] Double-clicked at current position")
            return {"status": "success", "x": x, "y": y}
        except Exception as e:
            print(f"[EXECUTION ERROR] {e}")
            return {"status": "error", "error": str(e)}

    async def right_click(self, x: int = None, y: int = None) -> dict:
        """Right click at position using pyautogui."""
        print(f"\n========== [EXECUTION START] ==========")
        print(f"[RIGHT_CLICK] x={x}, y={y}")
        
        pyautogui = get_pyautogui()
        if pyautogui is None:
            return {"status": "error", "reason": "pyautogui_not_available"}
        
        try:
            if x is not None and y is not None:
                pyautogui.rightClick(x, y)
                print(f"[EXECUTION SUCCESS] Right-clicked at ({x}, {y})")
            else:
                pyautogui.rightClick()
                print(f"[EXECUTION SUCCESS] Right-clicked at current position")
            return {"status": "success", "x": x, "y": y}
        except Exception as e:
            print(f"[EXECUTION ERROR] {e}")
            return {"status": "error", "error": str(e)}

    async def scroll(self, direction: str, amount: int = 500) -> dict:
        """Scroll using pyautogui with proper scroll amounts."""
        print(f"\n========== [EXECUTION START] ==========")
        print(f"[SCROLL] direction={direction}, amount={amount}")
        
        pyautogui = get_pyautogui()
        if pyautogui is None:
            return {"status": "error", "reason": "pyautogui_not_available"}
        
        try:
            # Use larger scroll amounts for visible effect
            # Positive = scroll up, Negative = scroll down
            scroll_amount = amount if direction.lower() == "up" else -amount
            pyautogui.scroll(scroll_amount)
            print(f"[EXECUTION SUCCESS] Scrolled {direction} by {abs(scroll_amount)}")
            return {"status": "success", "direction": direction, "amount": scroll_amount}
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
        """Close application on Windows using Alt+F4."""
        print(f"\n========== [EXECUTION START] ==========")
        print(f"[CLOSE_APP] app_name={app_name}, target={target}")

        pyautogui = get_pyautogui()

        try:
            if pyautogui:
                pyautogui.hotkey("alt", "f4")
                print(f"[EXECUTION SUCCESS] Closed focused window via Alt+F4")
                return {"status": "success", "target": "focused", "method": "alt_f4"}
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

        try:
            print(f"[WINDOW CONTROL] MINIMIZE_APP -> {{'app': {app_name!r}, 'target': {target!r}}}")
            affected = minimize_window(app_name)
            if affected <= 0:
                return {"status": "error", "reason": "window_not_found"}
            return {"status": "success", "affected_windows": affected, "method": "win32"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def maximize(
        self, app_name: str | None = None, target: str = "focused"
    ) -> dict:
        """Maximize window on Windows."""
        print(f"\n========== [EXECUTION START] ==========")
        print(f"[MAXIMIZE] app_name={app_name}, target={target}")

        try:
            print(f"[WINDOW CONTROL] MAXIMIZE_APP -> {{'app': {app_name!r}, 'target': {target!r}}}")
            affected = maximize_window(app_name)
            if affected <= 0:
                return {"status": "error", "reason": "window_not_found"}
            return {"status": "success", "affected_windows": affected, "method": "win32"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def restore(
        self, app_name: str | None = None, target: str = "focused"
    ) -> dict:
        """Restore window on Windows."""
        print(f"\n========== [EXECUTION START] ==========")
        print(f"[RESTORE] app_name={app_name}, target={target}")

        try:
            print(f"[WINDOW CONTROL] RESTORE_APP -> {{'app': {app_name!r}, 'target': {target!r}}}")
            affected = restore_window(app_name)
            if affected <= 0:
                return {"status": "error", "reason": "window_not_found"}
            return {"status": "success", "affected_windows": affected, "method": "win32"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    # =========================================================================
    # TEXT CONTROL SHORTCUTS (PATCH 5)
    # =========================================================================

    async def copy_text(self) -> dict:
        """Copy selected text using Ctrl+C."""
        print(f"\n========== [EXECUTION START] ==========")
        print(f"[COPY_TEXT]")
        
        pyautogui = get_pyautogui()
        if pyautogui is None:
            return {"status": "error", "reason": "pyautogui_not_available"}
        
        try:
            pyautogui.hotkey("ctrl", "c")
            print(f"[EXECUTION SUCCESS] Copied text")
            return {"status": "success", "action": "copy"}
        except Exception as e:
            print(f"[EXECUTION ERROR] {e}")
            return {"status": "error", "error": str(e)}

    async def paste_text(self) -> dict:
        """Paste text using Ctrl+V."""
        print(f"\n========== [EXECUTION START] ==========")
        print(f"[PASTE_TEXT]")
        
        pyautogui = get_pyautogui()
        if pyautogui is None:
            return {"status": "error", "reason": "pyautogui_not_available"}
        
        try:
            pyautogui.hotkey("ctrl", "v")
            print(f"[EXECUTION SUCCESS] Pasted text")
            return {"status": "success", "action": "paste"}
        except Exception as e:
            print(f"[EXECUTION ERROR] {e}")
            return {"status": "error", "error": str(e)}

    async def cut_text(self) -> dict:
        """Cut selected text using Ctrl+X."""
        print(f"\n========== [EXECUTION START] ==========")
        print(f"[CUT_TEXT]")
        
        pyautogui = get_pyautogui()
        if pyautogui is None:
            return {"status": "error", "reason": "pyautogui_not_available"}
        
        try:
            pyautogui.hotkey("ctrl", "x")
            print(f"[EXECUTION SUCCESS] Cut text")
            return {"status": "success", "action": "cut"}
        except Exception as e:
            print(f"[EXECUTION ERROR] {e}")
            return {"status": "error", "error": str(e)}

    async def select_all(self) -> dict:
        """Select all using Ctrl+A."""
        print(f"\n========== [EXECUTION START] ==========")
        print(f"[SELECT_ALL]")
        
        pyautogui = get_pyautogui()
        if pyautogui is None:
            return {"status": "error", "reason": "pyautogui_not_available"}
        
        try:
            pyautogui.hotkey("ctrl", "a")
            print(f"[EXECUTION SUCCESS] Selected all")
            return {"status": "success", "action": "select_all"}
        except Exception as e:
            print(f"[EXECUTION ERROR] {e}")
            return {"status": "error", "error": str(e)}

    async def undo(self) -> dict:
        """Undo using Ctrl+Z."""
        print(f"\n========== [EXECUTION START] ==========")
        print(f"[UNDO]")
        
        pyautogui = get_pyautogui()
        if pyautogui is None:
            return {"status": "error", "reason": "pyautogui_not_available"}
        
        try:
            pyautogui.hotkey("ctrl", "z")
            print(f"[EXECUTION SUCCESS] Undo")
            return {"status": "success", "action": "undo"}
        except Exception as e:
            print(f"[EXECUTION ERROR] {e}")
            return {"status": "error", "error": str(e)}

    async def redo(self) -> dict:
        """Redo using Ctrl+Y."""
        print(f"\n========== [EXECUTION START] ==========")
        print(f"[REDO]")
        
        pyautogui = get_pyautogui()
        if pyautogui is None:
            return {"status": "error", "reason": "pyautogui_not_available"}
        
        try:
            pyautogui.hotkey("ctrl", "y")
            print(f"[EXECUTION SUCCESS] Redo")
            return {"status": "success", "action": "redo"}
        except Exception as e:
            print(f"[EXECUTION ERROR] {e}")
            return {"status": "error", "error": str(e)}

    # =========================================================================
    # VOLUME CONTROL (PATCH 4)
    # =========================================================================

    async def volume_up(self, amount: float = 0.1) -> dict:
        """Increase system volume."""
        print(f"\n========== [EXECUTION START] ==========")
        print(f"[VOLUME_UP] amount={amount}")
        
        try:
            new_level = adjust_volume(amount)
            print(f"[EXECUTION SUCCESS] Volume increased to {new_level:.0%}")
            return {"status": "success", "volume": new_level, "action": "volume_up"}
        except Exception as e:
            print(f"[EXECUTION ERROR] {e}")
            return {"status": "error", "error": str(e)}

    async def volume_down(self, amount: float = 0.1) -> dict:
        """Decrease system volume."""
        print(f"\n========== [EXECUTION START] ==========")
        print(f"[VOLUME_DOWN] amount={amount}")
        
        try:
            new_level = adjust_volume(-amount)
            print(f"[EXECUTION SUCCESS] Volume decreased to {new_level:.0%}")
            return {"status": "success", "volume": new_level, "action": "volume_down"}
        except Exception as e:
            print(f"[EXECUTION ERROR] {e}")
            return {"status": "error", "error": str(e)}

    async def volume_mute(self) -> dict:
        """Mute system audio."""
        print(f"\n========== [EXECUTION START] ==========")
        print(f"[VOLUME_MUTE]")
        
        try:
            mute()
            print("[EXECUTION SUCCESS] Volume muted")
            return {"status": "success", "action": "muted"}
        except Exception as e:
            print(f"[EXECUTION ERROR] {e}")
            return {"status": "error", "error": str(e)}

    async def volume_unmute(self) -> dict:
        """Unmute system audio."""
        print(f"\n========== [EXECUTION START] ==========")
        print("[VOLUME_UNMUTE]")

        try:
            unmute()
            print("[EXECUTION SUCCESS] Volume unmuted")
            return {"status": "success", "action": "unmuted"}
        except Exception as e:
            print(f"[EXECUTION ERROR] {e}")
            return {"status": "error", "error": str(e)}
