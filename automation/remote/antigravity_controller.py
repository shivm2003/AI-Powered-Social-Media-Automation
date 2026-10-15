"""
Antigravity IDE & Laptop Remote Prompt Controller.
Allows user to send prompts from Telegram directly into the running Antigravity IDE or active software on their laptop.
Allocates sequential task numbers and sends completion notifications.
"""
import os
import sys
import time
import json
import logging
import ctypes
from ctypes import wintypes
from pathlib import Path
import pyperclip
try:
    import pyautogui
    pyautogui.FAILSAFE = False
except ImportError:
    pyautogui = None

logger = logging.getLogger("automation.remote.antigravity_controller")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

BASE_DIR = Path(__file__).parent.parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
TASKS_FILE = DATA_DIR / "remote_tasks.json"

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

SW_RESTORE = 9
SW_SHOW = 5
SW_SHOWMAXIMIZED = 3


def attach_to_desktop() -> bool:
    """
    Connects current thread to interactive desktop WinSta0\\default.
    Required for background daemons to interact with GUI windows.
    """
    try:
        hwinsta0 = user32.OpenWindowStationW("WinSta0", False, 0x37F)
        if hwinsta0:
            user32.SetProcessWindowStation(hwinsta0)
            hdesk = user32.OpenDesktopW("default", 0, False, 0x1FF)
            if hdesk:
                user32.SetThreadDesktop(hdesk)
                return True
    except Exception as e:
        logger.warning(f"Desktop attachment note: {e}")
    return False


def get_running_windows() -> list:
    """Returns list of visible non-empty windows on the interactive desktop."""
    attach_to_desktop()
    windows = []

    def enum_cb(hwnd, _):
        if user32.IsWindowVisible(hwnd):
            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buff = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buff, length + 1)
                title = buff.value.strip()
                if title and title not in ["Program Manager", "Default IME", "MSCTFIME UI"]:
                    # Filter out purely internal windows
                    if not title.startswith("OleMainThread") and not title.startswith("GDI+"):
                        windows.append({"hwnd": hwnd, "title": title})
        return True

    try:
        hdesk = user32.OpenDesktopW("default", 0, False, 0x1FF)
        if hdesk:
            user32.EnumDesktopWindows(
                hdesk,
                ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)(enum_cb),
                0
            )
    except Exception as e:
        logger.error(f"Error enumerating desktop windows: {e}")

    return windows


def find_target_window(target_keyword: str = "Antigravity") -> dict:
    """Finds a matching window by keyword (case-insensitive)."""
    windows = get_running_windows()
    kw_lower = target_keyword.lower()

    # 1. Exact or partial keyword match
    for w in windows:
        if kw_lower in w["title"].lower():
            return w

    # 2. Fallbacks
    if "antigravity" in kw_lower:
        for w in windows:
            if any(term in w["title"].lower() for term in ["code", "cursor", "visual studio"]):
                return w

    # 3. If any window found and target was "active", return first candidate
    if target_keyword.lower() in ["active", "current"] and windows:
        return windows[0]

    return None


def focus_window(hwnd: int) -> bool:
    """
    Brings target HWND to the foreground and focuses it across threads/privileges.
    """
    attach_to_desktop()
    if not hwnd or not user32.IsWindow(hwnd):
        return False

    try:
        # Check if minimized and restore
        if user32.IsIconic(hwnd):
            user32.ShowWindow(hwnd, SW_RESTORE)
        else:
            user32.ShowWindow(hwnd, SW_SHOW)

        current_thread_id = kernel32.GetCurrentThreadId()
        target_thread_id = user32.GetWindowThreadProcessId(hwnd, None)

        # Attach input queue to bypass Windows focus stealing prevention
        if current_thread_id != target_thread_id:
            user32.AttachThreadInput(current_thread_id, target_thread_id, True)

        user32.BringWindowToTop(hwnd)
        user32.SetForegroundWindow(hwnd)

        # Detach input queue
        if current_thread_id != target_thread_id:
            user32.AttachThreadInput(current_thread_id, target_thread_id, False)

        time.sleep(0.3)
        return True
    except Exception as e:
        logger.error(f"Error focusing window {hwnd}: {e}")
        return False


def load_task_history() -> dict:
    """Loads tasks and current sequence counter."""
    if TASKS_FILE.exists():
        try:
            with open(TASKS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"counter": 100, "tasks": []}


def save_task_history(data: dict):
    """Saves task history."""
    try:
        with open(TASKS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.warning(f"Error saving task history: {e}")


def allocate_new_task(prompt: str, target_mode: str = "antigravity_chat") -> dict:
    """Allocates the next sequential Task Number (e.g. #TASK-101) and records it."""
    history = load_task_history()
    next_num = history.get("counter", 100) + 1
    history["counter"] = next_num

    task_id = f"TASK-{next_num}"
    task_record = {
        "task_id": task_id,
        "task_num": next_num,
        "prompt": prompt,
        "target_mode": target_mode,
        "status": "received",
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "timestamp": time.time(),
    }
    history.setdefault("tasks", []).append(task_record)
    # Keep last 50 tasks
    if len(history["tasks"]) > 50:
        history["tasks"] = history["tasks"][-50:]
    save_task_history(history)
    return task_record


def update_task_status(task_id: str, status: str, details: str = "") -> dict:
    """Updates status of a task."""
    history = load_task_history()
    updated = None
    for t in history.get("tasks", []):
        if t.get("task_id") == task_id:
            t["status"] = status
            t["details"] = details
            t["completed_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
            updated = t
            break
    save_task_history(history)
    return updated


def inject_prompt_to_antigravity(prompt: str, target_mode: str = "antigravity_chat") -> dict:
    """
    Pastes the prompt into Antigravity IDE (or targeted software) and submits it.
    Modes:
    - 'antigravity_chat': Focus Antigravity IDE -> Focus Chat (Ctrl+L) -> Paste (Ctrl+V) -> Enter
    - 'antigravity_inline': Focus Antigravity IDE -> Open Inline (Ctrl+I) -> Paste (Ctrl+V) -> Enter
    - 'active_window': Focus active window -> Paste (Ctrl+V) -> Enter
    """
    attach_to_desktop()

    # 1. Copy prompt to clipboard
    try:
        pyperclip.copy(prompt)
        time.sleep(0.1)
    except Exception as e:
        logger.error(f"Error setting clipboard: {e}")
        return {"success": False, "message": f"Clipboard copy failed: {e}"}

    # 2. Locate target window
    target_kw = "Antigravity"
    if "notepad" in target_mode.lower():
        target_kw = "Notepad"
    elif "chrome" in target_mode.lower():
        target_kw = "Chrome"
    elif target_mode == "active_window":
        target_kw = "active"

    win = find_target_window(target_kw)
    if not win:
        # Fallback to any active window if Antigravity not found
        win = find_target_window("active")
        if not win:
            return {"success": False, "message": f"Target software window matching '{target_kw}' not found."}

    hwnd = win["hwnd"]
    title = win["title"]
    logger.info(f"Target window located: HWND {hwnd} ('{title}')")

    # 3. Focus the window
    focused = focus_window(hwnd)
    if not focused:
        return {"success": False, "message": f"Could not bring window '{title}' to foreground."}

    time.sleep(0.4)

    # 4. Mode-specific hotkey navigation
    try:
        if target_mode == "antigravity_chat":
            # Press Ctrl+L to focus chat input prompt
            pyautogui.hotkey("ctrl", "l")
            time.sleep(0.35)
        elif target_mode == "antigravity_inline":
            # Press Ctrl+I to open inline prompt
            pyautogui.hotkey("ctrl", "i")
            time.sleep(0.4)

        # 5. Paste the prompt via Ctrl+V
        pyautogui.hotkey("ctrl", "v")
        time.sleep(0.25)

        # 6. Press Enter to submit
        pyautogui.press("enter")
        time.sleep(0.2)

        return {
            "success": True,
            "window_title": title,
            "hwnd": hwnd,
            "message": f"Successfully pasted and submitted prompt to '{title}'."
        }
    except Exception as e:
        logger.error(f"Keystroke simulation error: {e}")
        return {"success": False, "message": f"Keystroke simulation error: {e}"}
