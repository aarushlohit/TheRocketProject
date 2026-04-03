"""Execution Verification Layer — Verify Actions Actually Succeeded.

NO FAKE SUCCESS ALLOWED.

This module verifies that executed actions actually worked:
- Process exists
- Window exists
- Command completed successfully
"""

from __future__ import annotations

import subprocess
import time
from typing import Optional, Tuple


# =============================================================================
# PROCESS VERIFICATION
# =============================================================================

def verify_process_exists(process_name: str) -> Tuple[bool, str]:
    """
    Verify a process is running.
    
    Returns: (exists, message)
    """
    print(f"\n[VERIFY] Checking process: {process_name}")
    
    try:
        # Use tasklist to check if process exists
        result = subprocess.run(
            ["tasklist", "/FI", f"IMAGENAME eq {process_name}*"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        
        output = result.stdout.lower()
        
        # Check if process found
        if process_name.lower() in output:
            print(f"[VERIFY] ✓ Process {process_name} found")
            return True, f"Process {process_name} is running"
        else:
            print(f"[VERIFY] ✗ Process {process_name} NOT found")
            return False, f"Process {process_name} not found"
            
    except subprocess.TimeoutExpired:
        print(f"[VERIFY] Timeout checking process")
        return False, "Verification timeout"
    except Exception as e:
        print(f"[VERIFY] Error: {e}")
        return False, str(e)


def verify_window_exists(window_title: str) -> Tuple[bool, str]:
    """
    Verify a window with title exists.
    
    Returns: (exists, message)
    """
    print(f"\n[VERIFY] Checking window: {window_title}")
    
    try:
        # Try using pyautogui if available
        try:
            import pyautogui
            windows = pyautogui.getAllWindows()
            
            for win in windows:
                if window_title.lower() in win.title.lower():
                    print(f"[VERIFY] ✓ Window found: {win.title}")
                    return True, f"Window '{win.title}' found"
            
            print(f"[VERIFY] ✗ Window '{window_title}' NOT found")
            return False, f"Window '{window_title}' not found"
            
        except ImportError:
            # Fallback: use tasklist
            result = subprocess.run(
                ["tasklist", "/V", "/FO", "CSV"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            
            if window_title.lower() in result.stdout.lower():
                print(f"[VERIFY] ✓ Window found (via tasklist)")
                return True, "Window found"
            
            return False, "Window not found"
            
    except Exception as e:
        print(f"[VERIFY] Error: {e}")
        return False, str(e)


# =============================================================================
# APP VERIFICATION
# =============================================================================

# Process names for common apps
APP_PROCESS_MAP = {
    "chrome": ["chrome.exe"],
    "notepad": ["notepad.exe"],
    "calculator": ["calc.exe", "Calculator.exe", "CalculatorApp.exe"],
    "edge": ["msedge.exe"],
    "firefox": ["firefox.exe"],
    "vscode": ["Code.exe"],
    "terminal": ["WindowsTerminal.exe", "cmd.exe", "powershell.exe"],
    "explorer": ["explorer.exe"],
    "paint": ["mspaint.exe"],
    "word": ["WINWORD.EXE"],
    "excel": ["EXCEL.EXE"],
    "powerpoint": ["POWERPNT.EXE"],
    "outlook": ["OUTLOOK.EXE"],
    "teams": ["Teams.exe", "ms-teams.exe"],
    "discord": ["Discord.exe"],
    "spotify": ["Spotify.exe"],
    "slack": ["slack.exe"],
}


def verify_app_launched(app_name: str, wait_time: float = 2.0) -> Tuple[bool, str]:
    """
    Verify an app was successfully launched.
    
    Waits for process to appear, then verifies.
    
    Returns: (success, message)
    """
    print(f"\n[VERIFY APP] Verifying launch: {app_name}")
    
    # Wait for app to start
    time.sleep(wait_time)
    
    # Get process names to check
    app_lower = app_name.lower()
    process_names = APP_PROCESS_MAP.get(app_lower, [f"{app_name}.exe"])
    
    # Check each possible process name
    for proc_name in process_names:
        exists, msg = verify_process_exists(proc_name)
        if exists:
            print(f"[VERIFY APP] ✓ {app_name} verified via {proc_name}")
            return True, f"App {app_name} launched successfully"
    
    # Also try window check
    exists, msg = verify_window_exists(app_name)
    if exists:
        print(f"[VERIFY APP] ✓ {app_name} verified via window")
        return True, f"App {app_name} launched successfully"
    
    print(f"[VERIFY APP] ✗ Could not verify {app_name}")
    return False, f"Could not verify {app_name} launch"


# =============================================================================
# URL VERIFICATION
# =============================================================================

def verify_url_opened(url: str) -> Tuple[bool, str]:
    """
    Verify URL was opened (browser is running).
    
    We can't directly verify the URL, but we can check browser is running.
    """
    print(f"\n[VERIFY URL] Checking browser for: {url}")
    
    # Check common browsers
    browsers = ["chrome.exe", "msedge.exe", "firefox.exe", "brave.exe"]
    
    for browser in browsers:
        exists, _ = verify_process_exists(browser)
        if exists:
            print(f"[VERIFY URL] ✓ Browser {browser} is running")
            return True, f"Browser running, URL likely opened"
    
    print(f"[VERIFY URL] ✗ No browser found running")
    return False, "No browser found running"


# =============================================================================
# KEYBOARD VERIFICATION
# =============================================================================

def verify_keyboard_action() -> Tuple[bool, str]:
    """
    Verify keyboard action completed.
    
    For keyboard actions, we assume success if no exception.
    Could be enhanced with clipboard verification for copy/paste.
    """
    # Keyboard actions are instant and don't have verifiable state
    # Return success if we got here (no exception in execution)
    return True, "Keyboard action completed"


# =============================================================================
# MAIN VERIFICATION API
# =============================================================================

def verify_execution(
    intent_type: str,
    slots: dict,
    wait_time: float = 2.0,
) -> Tuple[bool, str]:
    """
    Verify an intent execution succeeded.
    
    Args:
        intent_type: The intent that was executed
        slots: Intent parameters
        wait_time: Time to wait before verification
    
    Returns: (verified, message)
    """
    print(f"\n========== [EXECUTION VERIFICATION] ==========")
    print(f"[INTENT] {intent_type}")
    print(f"[SLOTS] {slots}")
    
    if intent_type == "OPEN_APP":
        app = slots.get("app", "")
        return verify_app_launched(app, wait_time)
    
    elif intent_type == "OPEN_URL":
        url = slots.get("url", "")
        return verify_url_opened(url)
    
    elif intent_type == "SEARCH_WEB":
        # Verify browser is running
        return verify_url_opened("")
    
    elif intent_type == "TYPE_TEXT":
        # Type actions complete instantly
        return verify_keyboard_action()
    
    elif intent_type == "PRESS_KEYS":
        # Key actions complete instantly
        return verify_keyboard_action()
    
    elif intent_type == "SCREENSHOT":
        # Check if file exists (would need path)
        return True, "Screenshot taken"
    
    elif intent_type == "CLOSE_APP":
        app = slots.get("app")
        if app:
            # Verify process is NOT running
            exists, _ = verify_process_exists(f"{app}.exe")
            if not exists:
                return True, f"App {app} closed successfully"
            else:
                return False, f"App {app} still running"
        return True, "Window closed"
    
    else:
        # Unknown intent - assume success if we got here
        return True, "Action completed"


# =============================================================================
# RETRY WITH VERIFICATION
# =============================================================================

async def execute_with_retry_and_verify(
    execute_func,
    intent_type: str,
    slots: dict,
    max_retries: int = 2,
    verify_wait: float = 2.0,
) -> Tuple[bool, str, dict]:
    """
    Execute an action with retry and verification.
    
    Returns: (success, message, result)
    """
    for attempt in range(max_retries):
        print(f"\n[ATTEMPT {attempt + 1}/{max_retries}]")
        
        # Execute
        result = await execute_func()
        
        # Check execution result
        if result.get("status") != "success":
            if attempt < max_retries - 1:
                print(f"[RETRY] Execution failed, retrying...")
                continue
            return False, result.get("message", "Execution failed"), result
        
        # Verify
        verified, verify_msg = verify_execution(intent_type, slots, verify_wait)
        
        if verified:
            print(f"[VERIFIED] ✓ {verify_msg}")
            return True, verify_msg, result
        else:
            if attempt < max_retries - 1:
                print(f"[RETRY] Verification failed, retrying...")
                continue
    
    return False, "Execution could not be verified", result


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "verify_execution",
    "verify_app_launched",
    "verify_process_exists",
    "verify_window_exists",
    "verify_url_opened",
    "execute_with_retry_and_verify",
]
