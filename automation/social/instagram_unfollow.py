"""
Instagram Unfollow Automator.
Safely inspects accounts currently followed by the logged-in user and automates unfollowing
with human-paced delays and Instagram native confirmation handling.
"""
import sys
import os
import time
import random
import logging
from pathlib import Path

# Ensure UTF-8 output on Windows
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
        sys.stderr.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
    except Exception:
        pass

BASE_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(BASE_DIR / "automation"))

from browser.driver import browser
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains

logger = logging.getLogger("automation.social.instagram_unfollow")
BASE_DIR = Path(__file__).parent.parent.parent


def get_logged_in_username(driver) -> str:
    """Detects the logged-in Instagram username from the navigation bar or avatar."""
    try:
        # Check profile link in sidebar
        profile_links = driver.find_elements(
            By.XPATH,
            "//a[contains(@href, '/') and not(contains(@href, '/explore')) and not(contains(@href, '/reels')) and not(contains(@href, '/direct')) and not(contains(@href, '/stories'))]"
        )
        for pl in profile_links:
            txt = (pl.text or pl.get_attribute("innerText") or "").strip()
            aria = (pl.get_attribute("aria-label") or "").strip()
            href = pl.get_attribute("href") or ""
            if "profile" in txt.lower() or "profile" in aria.lower():
                parts = [p for p in href.rstrip("/").split("/") if p]
                if parts and parts[-1] not in ["accounts", "explore"]:
                    return parts[-1]

        # Check avatar images
        imgs = driver.find_elements(By.XPATH, "//img[contains(@alt, 'profile picture')]")
        for img in imgs:
            parent_a = img.find_elements(By.XPATH, "./ancestor::a")
            if parent_a:
                href = parent_a[0].get_attribute("href") or ""
                parts = [p for p in href.rstrip("/").split("/") if p]
                if parts:
                    return parts[-1]
    except Exception as e:
        logger.debug(f"Error detecting username: {e}")

    return "loansolutions2026"


def get_instagram_following_list(max_count: int = 50) -> dict:
    """
    Retrieves the list of accounts currently followed by the user.

    Returns:
        dict: {
            "status": "success",
            "username": str,
            "total_following": int,
            "accounts": [{"username": str, "name": str, "profile_url": str}]
        }
    """
    try:
        driver = browser.navigate("instagram", "https://www.instagram.com/", refresh_first=False)
        time.sleep(2)

        username = get_logged_in_username(driver)
        driver.get(f"https://www.instagram.com/{username}/")
        time.sleep(3)

        # Parse following count from profile header
        following_link = None
        links = driver.find_elements(By.XPATH, "//header//a[contains(., 'following')] | //main//a[contains(., 'following')]")
        total_following_num = 0
        if links:
            following_link = links[0]
            txt = following_link.text or ""
            import re
            m = re.search(r"(\d+[\d,]*)", txt)
            if m:
                total_following_num = int(m.group(1).replace(",", ""))

        if not following_link:
            return {
                "status": "error",
                "message": "Could not find following link on profile.",
                "total_following": 0,
                "accounts": []
            }

        # Click following link to open dialog
        driver.execute_script("arguments[0].click();", following_link)
        time.sleep(3)

        dialogs = driver.find_elements(By.XPATH, "//div[@role='dialog']")
        if not dialogs:
            return {
                "status": "error",
                "message": "Following modal dialog did not open.",
                "total_following": total_following_num,
                "accounts": []
            }

        dialog = dialogs[0]
        accounts = []
        seen_users = set()

        # Scroll modal to collect accounts
        scroll_attempts = 0
        while len(accounts) < max_count and scroll_attempts < 10:
            user_links = dialog.find_elements(By.XPATH, ".//a")
            for l in user_links:
                href = l.get_attribute("href") or ""
                txt = (l.text or l.get_attribute("innerText") or "").strip().split("\n")[0]
                if href and "instagram.com/" in href and not any(x in href for x in ["#", "/explore", "/direct", "/reels", "/p/"]):
                    parts = [p for p in href.rstrip("/").split("/") if p]
                    if len(parts) >= 3 and "instagram.com" in parts[-2]:
                        u_name = parts[-1]
                        if u_name not in seen_users and u_name != username:
                            seen_users.add(u_name)
                            accounts.append({
                                "username": u_name,
                                "name": txt or u_name,
                                "profile_url": href
                            })
                            if len(accounts) >= max_count:
                                break

            # Scroll dialog down
            try:
                driver.execute_script("arguments[0].scrollTop += 400;", dialog)
            except Exception:
                pass
            scroll_attempts += 1
            time.sleep(1.2)

        return {
            "status": "success",
            "username": username,
            "total_following": total_following_num or len(accounts),
            "accounts": accounts
        }

    except Exception as e:
        logger.error(f"Error fetching Instagram following list: {e}", exc_info=True)
        return {
            "status": "error",
            "message": str(e),
            "total_following": 0,
            "accounts": []
        }


def unfollow_instagram_accounts(
    target_count: int = 10,
    specific_users: list = None,
    safety_delay: int = 12,
    on_progress=None,
    stop_event=None,
    campaign_id: str = None
) -> dict:
    """
    Safely unfollows Instagram accounts with human-like delays and popup confirmation handling.

    Args:
        target_count: Number of accounts to unfollow (0 means all currently followed).
        specific_users: Optional list of usernames to unfollow.
        safety_delay: Delay in seconds between unfollows.
        on_progress: Optional callback function(unfollowed_count, target_count, details).
        stop_event: Optional threading.Event to abort.
        campaign_id: Optional ID to check file-based stop flags (data/stop_{campaign_id}.flag).

    Returns:
        dict: {
            "status": "completed" | "stopped" | "error",
            "unfollowed_count": int,
            "unfollowed_accounts": list,
            "logs": list
        }
    """
    logs = []
    unfollowed_accounts = []
    unfollowed_count = 0
    stop_flag_file = BASE_DIR / "data" / f"stop_{campaign_id}.flag" if campaign_id else None

    logger.info(f"Starting Instagram unfollow task (Target: {target_count or 'ALL'})...")
    logs.append(f"🚀 Initiated Instagram unfollow task (Target: {target_count or 'ALL'}).")

    try:
        driver = browser.navigate("instagram", "https://www.instagram.com/", refresh_first=False)
        time.sleep(2)

        username = get_logged_in_username(driver)
        driver.get(f"https://www.instagram.com/{username}/")
        time.sleep(3)

        # Open following dialog
        following_links = driver.find_elements(By.XPATH, "//header//a[contains(., 'following')] | //main//a[contains(., 'following')]")
        if not following_links:
            msg = "Could not find following link on Instagram profile."
            logs.append(f"⚠️ {msg}")
            return {"status": "error", "unfollowed_count": 0, "unfollowed_accounts": [], "logs": logs}

        driver.execute_script("arguments[0].click();", following_links[0])
        time.sleep(3)

        effective_target = target_count if target_count > 0 else 9999

        while unfollowed_count < effective_target:
            if (stop_event and stop_event.is_set()) or (stop_flag_file and stop_flag_file.exists()):
                logs.append("🛑 Unfollow task stopped by user request.")
                logger.info("Unfollow task halted via stop signal.")
                break

            dialogs = driver.find_elements(By.XPATH, "//div[@role='dialog']")
            if not dialogs:
                # Try re-opening following dialog
                driver.get(f"https://www.instagram.com/{username}/")
                time.sleep(2.5)
                f_links = driver.find_elements(By.XPATH, "//header//a[contains(., 'following')] | //main//a[contains(., 'following')]")
                if f_links:
                    driver.execute_script("arguments[0].click();", f_links[0])
                    time.sleep(2.5)
                    dialogs = driver.find_elements(By.XPATH, "//div[@role='dialog']")

            if not dialogs:
                logs.append("⚠️ Following dialog closed or unavailable.")
                break

            dialog = dialogs[0]

            # Find buttons with text 'Following'
            following_btns = dialog.find_elements(
                By.XPATH,
                ".//button[normalize-space()='Following' or text()='Following']"
            )

            if not following_btns:
                # Try scrolling dialog down to load more
                driver.execute_script("arguments[0].scrollTop += 500;", dialog)
                time.sleep(2)
                following_btns = dialog.find_elements(
                    By.XPATH,
                    ".//button[normalize-space()='Following' or text()='Following']"
                )

            if not following_btns:
                logs.append("🏁 No more accounts with 'Following' status found.")
                break

            btn = following_btns[0]

            # Extract username of the person being unfollowed
            u_name = "User"
            try:
                # Search parent container for user link
                parent_row = btn.find_element(By.XPATH, "./ancestor::div[contains(@class, 'x1dm5hii') or contains(@class, 'x1i10hfl')][1]")
                u_links = parent_row.find_elements(By.XPATH, ".//a")
                for ul in u_links:
                    href = ul.get_attribute("href") or ""
                    parts = [p for p in href.rstrip("/").split("/") if p]
                    if parts and parts[-1] != username:
                        u_name = parts[-1]
                        break
            except Exception:
                pass

            # If specific_users filter provided, check if in list
            if specific_users and u_name.lower() not in [u.lower() for u in specific_users]:
                # Scroll past this user
                driver.execute_script("arguments[0].scrollTop += 100;", dialog)
                continue

            # Click the Following button
            try:
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
                time.sleep(0.5)
                btn.click()
            except Exception:
                driver.execute_script("arguments[0].click();", btn)

            time.sleep(1.5)

            # Look for native Instagram confirmation dialog: "Unfollow" button
            confirm_btns = driver.find_elements(
                By.XPATH,
                "//button[normalize-space()='Unfollow' or text()='Unfollow']"
            )

            unfollowed_successfully = False
            if confirm_btns:
                try:
                    confirm_btns[0].click()
                    unfollowed_successfully = True
                except Exception as e_c:
                    driver.execute_script("arguments[0].click();", confirm_btns[0])
                    unfollowed_successfully = True
                time.sleep(1.5)
            else:
                # In case no confirmation dialog was needed (button toggled to 'Follow')
                btn_txt = (btn.text or "").strip().lower()
                if btn_txt == "follow":
                    unfollowed_successfully = True

            if unfollowed_successfully:
                unfollowed_count += 1
                unfollowed_accounts.append(u_name)
                log_entry = f"✅ Unfollowed #{unfollowed_count}: '@{u_name}'"
                logs.append(log_entry)
                logger.info(log_entry)

                if on_progress:
                    try:
                        on_progress(unfollowed_count, effective_target, {
                            "unfollowed": unfollowed_count,
                            "target": effective_target,
                            "user": u_name,
                            "accounts": unfollowed_accounts
                        })
                    except Exception as e_cb:
                        logger.debug(f"Unfollow progress callback note: {e_cb}")

                if unfollowed_count >= effective_target:
                    break

                # Randomized human delay
                delay = random.uniform(max(6.0, safety_delay * 0.75), max(10.0, safety_delay * 1.25))
                logger.info(f"Human delay pause: {delay:.1f}s before next unfollow ({unfollowed_count}/{effective_target})...")
                time.sleep(delay)
            else:
                logs.append(f"⚠️ Could not confirm unfollow for '@{u_name}'")
                time.sleep(2)

        status_label = "stopped" if ((stop_event and stop_event.is_set()) or (stop_flag_file and stop_flag_file.exists())) else "completed"
        logs.append(f"🏁 Instagram unfollow session finished. Total unfollowed: {unfollowed_count}.")

        return {
            "status": status_label,
            "unfollowed_count": unfollowed_count,
            "unfollowed_accounts": unfollowed_accounts,
            "logs": logs
        }

    except Exception as e:
        logger.error(f"Error in Instagram unfollow execution: {e}", exc_info=True)
        logs.append(f"⚠️ Error: {str(e)}")
        return {
            "status": "error",
            "unfollowed_count": unfollowed_count,
            "unfollowed_accounts": unfollowed_accounts,
            "error": str(e),
            "logs": logs
        }


if __name__ == "__main__":
    print("Testing get_instagram_following_list...")
    res = get_instagram_following_list(max_count=10)
    print("Result:", res)
