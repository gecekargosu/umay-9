"""
UMAY Post-it Hotkey — Windows Host Script
==========================================
Runs on Windows HOST (not in Docker).
Global hotkey: Ctrl+Shift+H → captures clipboard → creates Post-it via API.

Requirements (host):
    pip install keyboard requests

Usage:
    python scripts/postit_hotkey.py

The script:
1. Registers Ctrl+Shift+H as global hotkey
2. When triggered, reads clipboard text
3. Sends to UMAY API to create a Post-it
4. Shows tray icon (optional, requires pystray)
"""
from __future__ import annotations

import json
import sys
import time
import threading
from pathlib import Path

try:
    import requests
except ImportError:
    print("ERROR: 'requests' not installed. Run: pip install requests")
    sys.exit(1)

UMAY_API = "http://localhost:5001"
MAX_TEXT_LENGTH = 10000
HOTKEY = "ctrl+shift+h"


def get_clipboard_text() -> str:
    """Get current clipboard text content."""
    try:
        import subprocess
        # Windows: use powershell to get clipboard
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", "Get-Clipboard"],
            capture_output=True, text=True, timeout=5
        )
        text = result.stdout.strip()
        if len(text) > MAX_TEXT_LENGTH:
            text = text[:MAX_TEXT_LENGTH] + "\n... (truncated)"
        return text
    except Exception as e:
        print(f"Clipboard error: {e}")
        return ""


def get_active_window_title() -> str:
    """Try to get the active window title for source_app."""
    try:
        import subprocess
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "(Get-Process | Where-Object {$_.MainWindowTitle -ne ''} | "
             "Sort-Object StartTime -Descending | Select-Object -First 1).MainWindowTitle"],
            capture_output=True, text=True, timeout=5
        )
        return result.stdout.strip()[:100]
    except Exception:
        return ""


def create_postit(content: str, source_app: str = "") -> bool:
    """Create a Post-it via UMAY API."""
    try:
        # Auto-generate title from first line
        first_line = content.split("\n")[0][:80]
        resp = requests.post(
            f"{UMAY_API}/api/postits/quick",
            json={
                "content": content,
                "title": first_line,
                "source_app": source_app or None,
                "save_to_memory": False,
            },
            timeout=10,
        )
        if resp.status_code == 201:
            data = resp.json()
            postit = data.get("postit", {})
            print(f"✅ Post-it created: {postit.get('title', 'untitled')[:50]}")
            return True
        else:
            print(f"❌ API error: {resp.status_code} — {resp.text[:200]}")
            return False
    except requests.ConnectionError:
        print("❌ Cannot connect to UMAY API. Is the panel running?")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def on_hotkey():
    """Hotkey callback — capture clipboard and create Post-it."""
    print(f"\n{'='*50}")
    print(f"📌 Bunu Hatırlat — {time.strftime('%H:%M:%S')}")
    print(f"{'='*50}")

    text = get_clipboard_text()
    if not text:
        print("📋 Clipboard is empty or contains non-text data.")
        return

    print(f"📋 Clipboard: {text[:100]}{'...' if len(text) > 100 else ''}")

    source = get_active_window_title()
    if source:
        print(f"🪟 Source: {source}")

    success = create_postit(text, source_app=source)
    if success:
        print("✅ Post-it created successfully!")
    else:
        print("❌ Failed to create Post-it.")


def main():
    """Main entry point."""
    print("=" * 50)
    print("UMAY Post-it Hotkey")
    print(f"Hotkey: {HOTKEY.upper()}")
    print(f"API: {UMAY_API}")
    print("Press Ctrl+C to exit")
    print("=" * 50)

    # Check if API is reachable
    try:
        resp = requests.get(f"{UMAY_API}/api/health", timeout=5)
        if resp.ok:
            print("✅ UMAY API connected")
        else:
            print("⚠️ UMAY API responded but not healthy")
    except requests.ConnectionError:
        print("⚠️ UMAY API not reachable. Hotkey will still work when API comes online.")
    except Exception as e:
        print(f"⚠️ API check failed: {e}")

    # Try to use keyboard library
    try:
        import keyboard
        print(f"\n🔧 Registering hotkey: {HOTKEY}")
        keyboard.add_hotkey(HOTKEY, on_hotkey)
        print("✅ Hotkey registered. Waiting for trigger...")
        print("   Select text anywhere → Press Ctrl+Shift+H → Post-it created!")
        keyboard.wait()  # Block forever
    except ImportError:
        print("\n⚠️ 'keyboard' library not installed.")
        print("   Install with: pip install keyboard")
        print("   Falling back to polling mode (checking clipboard every 2s)...")
        _poll_mode()


def _poll_mode():
    """Fallback: poll clipboard for changes."""
    last_clipboard = ""
    while True:
        try:
            current = get_clipboard_text()
            if current and current != last_clipboard and len(current) > 5:
                print(f"\n📋 New clipboard content detected ({len(current)} chars)")
                print("   Creating Post-it automatically...")
                create_postit(current, source_app="clipboard-poll")
                last_clipboard = current
        except KeyboardInterrupt:
            print("\n👋 Exiting...")
            break
        except Exception:
            pass
        time.sleep(2)


if __name__ == "__main__":
    main()
