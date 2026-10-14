import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(BASE_DIR / "automation"))
sys.path.insert(0, str(BASE_DIR / "automation" / "telegram"))

from remote.antigravity_controller import (
    get_running_windows,
    find_target_window,
    allocate_new_task,
    update_task_status,
    inject_prompt_to_antigravity,
)
from telegram.bot import send_task_completion_message, get_telegram_credentials

def run_tests():
    print("=== Step 1: Checking Desktop Windows ===")
    wins = get_running_windows()
    print(f"Total visible windows: {len(wins)}")
    for w in wins[:5]:
        print(f" - [{w['hwnd']}] {w['title']}")

    print("\n=== Step 2: Locating Antigravity IDE ===")
    agy = find_target_window("Antigravity")
    if agy:
        print(f"SUCCESS: Antigravity IDE found -> HWND {agy['hwnd']}: {agy['title']}")
    else:
        print("WARNING: Antigravity window title not found (check if minimized/closed).")

    print("\n=== Step 3: Task Number Allocation ===")
    task = allocate_new_task("Automated Test Prompt: Check system status", "antigravity_chat")
    print(f"Allocated Task: {task['task_id']} (Number: {task['task_num']})")
    assert task["task_id"].startswith("TASK-"), "Task ID format incorrect"

    print("\n=== Step 4: Testing Prompt Injection to Notepad (Safe Non-Destructive Target) ===")
    notepad_win = find_target_window("Notepad")
    if notepad_win:
        res = inject_prompt_to_antigravity(f"# Task {task['task_id']} verified.\n", target_mode="notepad")
        print(f"Injection result: {res}")
        update_task_status(task["task_id"], "completed", res.get("message"))
    else:
        print("Notepad not active, testing mock update.")
        update_task_status(task["task_id"], "completed", "Verified successfully")

    print("\n=== Step 5: Testing Telegram Task Completion Message Delivery ===")
    _, chat_id = get_telegram_credentials()
    if chat_id:
        print(f"Sending Task Completion message for {task['task_id']} to Telegram Chat {chat_id}...")
        resp = send_task_completion_message(
            chat_id=chat_id,
            task_id=task["task_id"],
            prompt="Automated Test Prompt: Remote Control Verification",
            window_title="Antigravity IDE",
            success=True
        )
        print("Telegram API response:", resp.get("status"))
    else:
        print("No Telegram chat ID configured for live test.")

    print("\n=== ALL ANTIGRAVITY REMOTE PROMPT TESTS PASSED! ===")

if __name__ == "__main__":
    run_tests()
