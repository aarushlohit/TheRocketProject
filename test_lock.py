"""Test script for lock screen execution.

This script directly tests the lock_screen functionality.
Run it to verify the screen actually locks.

WARNING: This will LOCK YOUR SCREEN when run!

Usage:
    python test_lock.py
"""

import platform
import subprocess
import ctypes
import sys


def test_lock_subprocess():
    """Test lock screen using subprocess."""
    print("\n[TEST] Testing subprocess.run method...")
    print(f"  Platform: {platform.system()}")
    
    if platform.system() != "Windows":
        print("  [SKIP] Not running on Windows")
        return False
    
    try:
        result = subprocess.run(
            ["rundll32.exe", "user32.dll,LockWorkStation"],
            check=True,
            shell=False,
            capture_output=True,
            timeout=5
        )
        print(f"  [SUCCESS] subprocess completed, returncode={result.returncode}")
        return True
    except Exception as e:
        print(f"  [FAILED] {e}")
        return False


def test_lock_ctypes():
    """Test lock screen using ctypes."""
    print("\n[TEST] Testing ctypes.windll method...")
    print(f"  Platform: {platform.system()}")
    
    if platform.system() != "Windows":
        print("  [SKIP] Not running on Windows")
        return False
    
    try:
        result = ctypes.windll.user32.LockWorkStation()
        if result:
            print(f"  [SUCCESS] LockWorkStation returned {result}")
            return True
        else:
            error_code = ctypes.get_last_error()
            print(f"  [FAILED] LockWorkStation returned 0, GetLastError={error_code}")
            return False
    except Exception as e:
        print(f"  [FAILED] {e}")
        return False


def main():
    print("=" * 50)
    print("LOCK SCREEN EXECUTION TEST")
    print("=" * 50)
    print(f"\nPlatform: {platform.system()}")
    print(f"Python: {sys.version}")
    
    if platform.system() != "Windows":
        print("\n[ERROR] This test must be run on Windows!")
        sys.exit(1)
    
    print("\n" + "=" * 50)
    print("WARNING: This will lock your screen!")
    print("=" * 50)
    
    response = input("\nProceed? (y/n): ").strip().lower()
    if response != 'y':
        print("Aborted.")
        sys.exit(0)
    
    # Try ctypes first (most reliable)
    print("\n[INFO] Using ctypes method (most reliable)...")
    success = test_lock_ctypes()
    
    if not success:
        print("\n[INFO] Trying subprocess fallback...")
        success = test_lock_subprocess()
    
    if success:
        print("\n" + "=" * 50)
        print("TEST PASSED: Screen should be locked now!")
        print("=" * 50)
    else:
        print("\n" + "=" * 50)
        print("TEST FAILED: Screen did not lock!")
        print("=" * 50)
        sys.exit(1)


if __name__ == "__main__":
    main()
