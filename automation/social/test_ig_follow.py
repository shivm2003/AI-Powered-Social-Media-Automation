"""
Instagram Follow Verification & Candidate Inspector.
Follows the test template established by test_fb_links.py.
"""
import sys
import time
from pathlib import Path

# Ensure UTF-8 output on Windows console
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

BASE_DIR = Path(__file__).parent.parent.parent
sys.path.append(str(BASE_DIR / "automation"))

from browser.driver import browser
from selenium.webdriver.common.by import By
from social.instagram_follow import send_instagram_follow_requests, extract_ig_profile_info

test_loc = sys.argv[1] if len(sys.argv) > 1 else "Mumbai"
test_count = int(sys.argv[2]) if len(sys.argv) > 2 else 2

print(f"=== Starting Instagram Follow Template Test for Location: '{test_loc}' (Target: {test_count}) ===")

# Run through the standard growth follow template
result = send_instagram_follow_requests(
    location=test_loc,
    target_count=test_count,
    safety_delay=8,
    on_progress=lambda sent, target, details: print(f"  [LIVE PROGRESS] Followed {sent}/{target}: {details.get('user')}")
)

print("\n=== Instagram Follow Test Complete ===")
print("Status:", result.get("status"))
print("Sent Count:", result.get("sent"))
print("Logs:")
for log in result.get("logs", []):
    print("  ->", log)
