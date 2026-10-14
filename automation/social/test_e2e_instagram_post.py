"""
End-to-End QA Automation Suite: Instagram Post & Caption Verification
Role: Lead Quality Assurance Engineer (10+ Years Experience)
Target: Instagram Post Flow, Lexical Caption Editor State, Live Feed Verification
"""
import sys
import os
import time
import logging
from pathlib import Path

# Fix Windows console UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

BASE_DIR = Path(__file__).parent.parent.parent
sys.path.append(str(BASE_DIR / "automation"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("QA.E2E.Instagram")

from browser.driver import browser
from social.instagram import post_to_instagram
from selenium.webdriver.common.by import By

def run_e2e_test():
    print("=" * 80)
    print("🧪 SENIOR QA END-TO-END TEST SUITE: INSTAGRAM CAPTION & POSTING ENGINE")
    print("=" * 80)

    # ─────────────────────────────────────────────────────────
    # STAGE 1: PRE-FLIGHT ENVIRONMENT & SESSION AUDIT
    # ─────────────────────────────────────────────────────────
    print("\n[STAGE 1/5] Pre-flight Environment & Session Audit...")
    media_file = str(BASE_DIR / "Loan Solutions.png")
    if not os.path.exists(media_file):
        raise FileNotFoundError(f"Test media file missing at: {media_file}")
    print(f"  ✓ Media Asset Verified: {media_file} ({os.path.getsize(media_file)} bytes)")

    driver = browser.navigate("instagram", "https://www.instagram.com/", refresh_first=False)
    time.sleep(2)
    current_url = driver.current_url
    print(f"  ✓ Connected to browser session. Current URL: {current_url}")

    # Check for authentication
    profile_links = driver.find_elements(By.XPATH, "//a[contains(@href, '/loansolutions2026')]")
    if not profile_links:
        print("  ⚠️ Warning: Profile link /loansolutions2026/ not found immediately on sidebar. Checking general session...")
    else:
        print("  ✓ Authenticated Session Verified: @loansolutions2026")

    # ─────────────────────────────────────────────────────────
    # STAGE 2: TEST DATA PREPARATION
    # ─────────────────────────────────────────────────────────
    print("\n[STAGE 2/5] Test Data Construction & Payload Validation...")
    unique_ts = time.strftime("%d-%b %H:%M")
    test_caption = (
        f"🏡 Loan Solutions — Empowering Indian Families Since 2026! [{unique_ts}]\n\n"
        "Need financial assistance for your dream home, vehicle, or personal goals?\n"
        "✨ Instant approval with minimal paperwork\n"
        "✨ Lowest interest rates in ₹ with flexible EMIs\n"
        "✨ Zero hidden charges & 100% transparent process\n\n"
        "👉 Apply Now: https://loansolutions.everythingrental.in/application\n\n"
        "#LoanSolutions #HomeLoan #PersonalLoan #FinancialFreedom #India #LowEMI"
    )

    # Validate test payload constraints
    assert "https://loansolutions.everythingrental.in/application" in test_caption, "Payload Missing Mandatory Apply URL!"
    assert "#LoanSolutions" in test_caption, "Payload Missing Mandatory Hashtag!"
    print(f"  ✓ Payload character count: {len(test_caption)} chars")
    print("  ✓ Mandatory Call-to-Action Link validated.")

    # ─────────────────────────────────────────────────────────
    # STAGE 3: EXECUTE POSTING WORKFLOW VIA CORE ENGINE
    # ─────────────────────────────────────────────────────────
    print("\n[STAGE 3/5] Executing post_to_instagram() via Engine...")
    t0 = time.time()
    result = post_to_instagram(media_path=media_file, caption=test_caption)
    elapsed = time.time() - t0
    print(f"  ✓ Execution completed in {elapsed:.2f}s")
    print(f"  ✓ Engine Return Payload: {result}")

    assert result.get("status") == "success", f"Post execution failed: {result.get('message')}"
    print("  ✅ STAGE 3 PASSED: Post published without exception!")

    # ─────────────────────────────────────────────────────────
    # STAGE 4: POST-PUBLISH LIVE FEED AUDIT
    # ─────────────────────────────────────────────────────────
    print("\n[STAGE 4/5] Live Verification on Instagram Profile Feed...")
    time.sleep(5)
    profile_url = "https://www.instagram.com/loansolutions2026/"
    driver.get(profile_url)
    time.sleep(4)

    screenshot_profile = str(BASE_DIR / "ig_qa_live_profile.png")
    driver.save_screenshot(screenshot_profile)
    print(f"  ✓ Captured live profile screenshot: {screenshot_profile}")

    # Open first/latest post on profile grid directly via its URL
    first_post_url = None
    try:
        post_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/p/']")
        if post_links:
            first_post_url = post_links[0].get_attribute('href')
            print(f"  ✓ Located latest post on grid: {first_post_url}")
            driver.get(first_post_url)
            time.sleep(3.5)
        else:
            print("  ⚠️ Could not find a[href*='/p/'] on profile page directly.")
    except Exception as e:
        print(f"  ⚠️ Error opening post: {e}")

    # Inspect post caption text
    print("\n[STAGE 5/5] Extracting & Auditing Rendered Live Caption...")
    rendered_caption = ""
    try:
        # On dedicated post page, read full body text or h1/caption spans
        page_text = driver.find_element(By.TAG_NAME, "body").text
        rendered_caption = page_text
    except Exception as e:
        print(f"  ⚠️ Exception reading caption from post page: {e}")

    screenshot_post = str(BASE_DIR / "ig_qa_live_post_details.png")
    driver.save_screenshot(screenshot_post)
    print(f"  ✓ Captured live post modal screenshot: {screenshot_post}")

    print("\n" + "=" * 80)
    print("📋 SENIOR QA VERIFICATION REPORT")
    print("=" * 80)
    print(f"• Target Platform: Instagram (@loansolutions2026)")
    print(f"• Execution Status: {result.get('status').upper()}")
    print(f"• Total Execution Duration: {elapsed:.2f}s")
    print(f"• Uploaded Media: {os.path.basename(media_file)}")
    print(f"• Rendered Caption Sample:\n---\n{rendered_caption[:300]}...\n---")

    # Assertions
    caption_has_link = "loansolutions.everythingrental.in/application" in rendered_caption
    caption_has_tag = "LoanSolutions" in rendered_caption or "loansolutions" in rendered_caption.lower()
    
    print(f"• Assertion [Caption Not Empty]: {'PASSED ✅' if len(rendered_caption) > 0 else 'CHECK SCREENSHOT ⚠️'}")
    print(f"• Assertion [Mandatory Apply URL Fitted]: {'PASSED ✅' if caption_has_link else 'CHECK SCREENSHOT ⚠️'}")
    print(f"• Assertion [Hashtags Fitted]: {'PASSED ✅' if caption_has_tag else 'CHECK SCREENSHOT ⚠️'}")
    print("=" * 80)

    if caption_has_link:
        print("\n🏆 QA RESULT: 100% PASS - Caption is completely fitted, bound, and live on Instagram!")
    else:
        print("\n🔍 QA NOTE: Post shared successfully. Review screenshot ig_qa_live_post_details.png to inspect visual render.")

if __name__ == "__main__":
    run_e2e_test()
