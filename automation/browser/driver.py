"""
Chrome WebDriver setup using undetected-chromedriver.
Manages browser instances with saved profiles per platform.
"""
import time
import random
import logging
from pathlib import Path

logger = logging.getLogger("automation.driver")

try:
    import undetected_chromedriver as uc
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    HAS_SELENIUM = True
except ImportError:
    HAS_SELENIUM = False
    logger.warning("Selenium/undetected-chromedriver not installed. Run: pip install undetected-chromedriver selenium")

from config import PLATFORM_PROFILES, PLATFORM_URLS, CHROME_OPTIONS, TIMEOUTS, HUMAN_DELAY


def get_chrome_version_main():
    """Detect installed Chrome major version on Windows."""
    try:
        import winreg
        for root in [winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE]:
            try:
                key = winreg.OpenKey(root, r"Software\Google\Chrome\BLBeacon")
                val, _ = winreg.QueryValueEx(key, "version")
                return int(val.split(".")[0])
            except Exception:
                continue
    except Exception:
        pass
    return None


def is_debugging_port_open(port=9222):
    """Check if Chrome is running with remote debugging port active."""
    import socket
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.3)
            return s.connect_ex(('127.0.0.1', port)) == 0
    except Exception:
        return False


def ensure_debugging_browser():
    """Ensure Chrome is running with remote debugging enabled on port 9222."""
    if is_debugging_port_open(9222):
        return True

    import subprocess
    import os
    chrome_candidates = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe"),
    ]
    chrome_exe = next((c for c in chrome_candidates if os.path.exists(c)), None)
    if not chrome_exe:
        return False

    shared_profile = Path(__file__).parent.parent / "chrome_profiles" / "shared_browser"
    shared_profile.mkdir(parents=True, exist_ok=True)

    args = [
        chrome_exe,
        "--remote-debugging-port=9222",
        f"--user-data-dir={shared_profile}",
        "--no-first-run",
        "--no-default-browser-check",
    ]
    try:
        subprocess.Popen(args)
        for _ in range(10):
            time.sleep(0.5)
            if is_debugging_port_open(9222):
                logger.info("Successfully launched Chrome with remote debugging on port 9222!")
                return True
    except Exception as e:
        logger.warning(f"Could not auto-launch debugging Chrome: {e}")
    return False


class BrowserDriver:
    """Manages Chrome browser instances with persistent profiles or attached user browser."""

    def __init__(self):
        self.drivers = {}  # platform -> driver instance

    def get_driver(self, platform):
        """Get or create a Chrome driver. Prioritizes connecting to user's open browser if port 9222 is active."""
        if not HAS_SELENIUM:
            raise RuntimeError("Selenium is not installed. Run: pip install undetected-chromedriver selenium")

        # ── 1. If remote debugging port 9222 is active or can be activated, connect to user's browser ──
        if not is_debugging_port_open(9222):
            ensure_debugging_browser()

        if is_debugging_port_open(9222):
            shared_driver = self.drivers.get("_shared_debug_driver")
            if shared_driver:
                try:
                    shared_driver.title
                    self.drivers[platform] = shared_driver
                    return shared_driver
                except Exception:
                    self.drivers.pop("_shared_debug_driver", None)

            logger.info("Found active Chrome on port 9222! Attaching bot to user's existing browser window...")
            try:
                from selenium import webdriver
                from selenium.webdriver.chrome.options import Options as SeleniumOptions

                options = SeleniumOptions()
                options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
                driver = webdriver.Chrome(options=options)
                driver._is_shared = True
                self.drivers["_shared_debug_driver"] = driver
                self.drivers[platform] = driver
                logger.info(f"Successfully attached to user's browser! Window title: {driver.title}")
                return driver
            except Exception as e:
                logger.warning(f"Could not attach to port 9222 ({e}). Falling back to standalone profile.")

        # ── 2. Fallback: Standalone undetected-chromedriver with dedicated profile ──
        if platform in self.drivers:
            try:
                self.drivers[platform].title
                return self.drivers[platform]
            except Exception:
                del self.drivers[platform]

        profile_dir = PLATFORM_PROFILES.get(platform)
        if not profile_dir:
            raise ValueError(f"Unknown platform: {platform}")

        # If shared_browser contains full cookies and platform profile doesn't, prefer shared_browser
        shared_profile = profile_dir.parent / "shared_browser"
        shared_cookie = shared_profile / "Default" / "Network" / "Cookies"
        platform_cookie = profile_dir / "Default" / "Network" / "Cookies"
        if shared_cookie.exists() and (not platform_cookie.exists() or platform_cookie.stat().st_size < 30000):
            profile_dir = shared_profile

        profile_dir.mkdir(parents=True, exist_ok=True)
        default_dir = profile_dir / "Default"
        default_dir.mkdir(parents=True, exist_ok=True)

        # Clean any stale locks that could prevent Chrome from starting
        for p in [profile_dir, default_dir]:
            for item in p.glob("*"):
                name_lower = item.name.lower()
                if "singleton" in name_lower or name_lower == "lock" or name_lower.endswith(".lock"):
                    try:
                        if item.is_file():
                            item.unlink()
                    except Exception:
                        pass

        # Ensure Local State doesn't show profile picker
        local_state_file = profile_dir / "Local State"
        if local_state_file.exists():
            try:
                import json
                with open(local_state_file, "r", encoding="utf-8") as f:
                    ls_data = json.load(f)
                dirty = False
                if "profile" in ls_data:
                    if ls_data["profile"].get("picker_shown") is not False:
                        ls_data["profile"]["picker_shown"] = False
                        dirty = True
                    info_cache = ls_data["profile"].get("info_cache", {})
                    if len(info_cache) > 1:
                        def_info = info_cache.get("Default", {"name": "Default"})
                        ls_data["profile"]["info_cache"] = {"Default": def_info}
                        ls_data["profile"]["last_used"] = "Default"
                        dirty = True
                if dirty:
                    with open(local_state_file, "w", encoding="utf-8") as f:
                        json.dump(ls_data, f, indent=2)
            except Exception as e:
                logger.debug(f"Local State check: {e}")

        logger.info(f"Creating Chrome driver for {platform} with profile: {profile_dir}")

        driver = None

        # Use standard Selenium 4 Chrome (fast, reliable, no hanging uc processes)
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options as SeleniumOptions

        sel_opts = SeleniumOptions()
        sel_opts.add_argument(f"--user-data-dir={profile_dir}")
        sel_opts.add_argument(f"--window-size={CHROME_OPTIONS['window_size'][0]},{CHROME_OPTIONS['window_size'][1]}")
        sel_opts.add_argument("--remote-allow-origins=*")
        sel_opts.add_argument("--disable-blink-features=AutomationControlled")
        sel_opts.add_argument("--no-first-run")
        sel_opts.add_argument("--no-default-browser-check")
        sel_opts.add_experimental_option("excludeSwitches", ["enable-automation"])
        sel_opts.add_experimental_option("useAutomationExtension", False)

        try:
            driver = webdriver.Chrome(options=sel_opts)
            logger.info(f"Initialized standard Selenium Chrome driver for {platform}")
        except Exception as e_sel:
            logger.warning(f"Initial Selenium start notice: {e_sel}. Cleaning stale locks and retrying...")
            for p in [profile_dir, default_dir]:
                for item in p.glob("*"):
                    name_lower = item.name.lower()
                    if "singleton" in name_lower or "lock" in name_lower:
                        try:
                            if item.is_file():
                                item.unlink()
                        except Exception:
                            pass
            driver = webdriver.Chrome(options=sel_opts)
            logger.info(f"Successfully started Chrome driver on retry for {platform}")

        driver._is_shared = False
        driver.set_page_load_timeout(TIMEOUTS["page_load"])

        self.drivers[platform] = driver
        return driver

    def refresh_and_ensure_fresh(self, driver, platform_name="Webpage", timeout=20):
        """
        Refreshes the current webpage and ensures all content is fresh, visible,
        and fully loaded before any interactions take place.
        """
        try:
            curr_url = driver.current_url
            logger.info(f"🔄 Refreshing {platform_name} page first ({curr_url}) to ensure fresh content and clean state...")
            driver.refresh()
            time.sleep(1.5)

            # 1. Wait for document.readyState == 'complete'
            WebDriverWait(driver, timeout).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )

            # 2. Wait for <body> to be present and visible
            WebDriverWait(driver, timeout).until(
                lambda d: d.find_element(By.TAG_NAME, "body").is_displayed()
            )

            # 3. Extra settle time for SPAs (React/Angular/Vue feeds, chat history, Facebook/Instagram/ChatGPT/Gemini DOM)
            time.sleep(2.5)

            # 4. Quick micro-scroll to activate dynamic viewport rendering if lazy-loaded
            try:
                driver.execute_script("window.scrollBy(0, 80);")
                time.sleep(0.3)
                driver.execute_script("window.scrollBy(0, -80);")
                time.sleep(0.4)
            except Exception:
                pass

            logger.info(f"✅ {platform_name} refreshed successfully. All fresh content is now visible and ready for actions!")
            return True
        except Exception as e:
            logger.warning(f"Refresh and wait note on {platform_name}: {e}")
            time.sleep(2.0)
            return False

    def navigate(self, platform, url=None, refresh_first=True):
        """Navigate to a URL or the platform's default URL. Respects existing user tabs if attached. Refreshes first by default."""
        import urllib.parse
        driver = self.get_driver(platform)
        target_url = url or PLATFORM_URLS.get(platform, "https://google.com")
        logger.info(f"Navigating {platform} to {target_url} (refresh_first={refresh_first})")

        if getattr(driver, "_is_shared", False):
            # Working inside user's active browser: check if domain is already open in a tab
            try:
                target_netloc = urllib.parse.urlparse(target_url).netloc.lower()
                found = False
                for handle in driver.window_handles:
                    driver.switch_to.window(handle)
                    current_netloc = urllib.parse.urlparse(driver.current_url).netloc.lower()
                    if target_netloc and (target_netloc in current_netloc or current_netloc in target_netloc):
                        found = True
                        cur_clean = driver.current_url.rstrip('/')
                        tgt_clean = target_url.rstrip('/')
                        if cur_clean != tgt_clean:
                            driver.get(target_url)
                        elif refresh_first:
                            refresh_and_wait(driver, platform)
                        break

                if not found:
                    # Open in a new tab so user's app/dashboard page remains intact
                    driver.switch_to.new_window('tab')
                    driver.get(target_url)
            except Exception as e:
                logger.warning(f"Shared tab navigation note: {e}")
                driver.get(target_url)
        else:
            driver.get(target_url)

        if refresh_first:
            self.refresh_and_ensure_fresh(driver, platform_name=platform.capitalize())
        else:
            self.human_wait("page")
        return driver

    def close(self, platform):
        """Close browser instance or release tab if shared."""
        if platform in self.drivers:
            driver = self.drivers[platform]
            if getattr(driver, "_is_shared", False):
                # Don't quit user's entire browser!
                try:
                    if len(driver.window_handles) > 1:
                        driver.close()
                        driver.switch_to.window(driver.window_handles[0])
                except Exception:
                    pass
            else:
                try:
                    driver.quit()
                except Exception:
                    pass
            self.drivers.pop(platform, None)

    def close_all(self):
        """Close standalone browser instances without killing user's attached browser."""
        for platform in list(self.drivers.keys()):
            if platform != "_shared_debug_driver":
                self.close(platform)

    # ── Human-like interaction helpers ──

    @staticmethod
    def human_wait(wait_type="action"):
        """Wait a random human-like amount of time."""
        delay_range = HUMAN_DELAY.get(wait_type, (0.5, 2.0))
        time.sleep(random.uniform(*delay_range))

    @staticmethod
    def human_type(element, text):
        """Type text character by character with human-like delays."""
        for char in text:
            element.send_keys(char)
            time.sleep(random.uniform(*HUMAN_DELAY["typing"]))

    def wait_for_element(self, driver, by, value, timeout=None):
        """Wait for an element to be present and return it."""
        timeout = timeout or TIMEOUTS["element_wait"]
        return WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((by, value))
        )

    def wait_for_clickable(self, driver, by, value, timeout=None):
        """Wait for an element to be clickable and return it."""
        timeout = timeout or TIMEOUTS["element_wait"]
        return WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((by, value))
        )

    def safe_click(self, driver, element):
        """Click an element with human-like behavior."""
        self.human_wait("action")
        try:
            element.click()
        except Exception:
            driver.execute_script("arguments[0].click();", element)

    def scroll_to_element(self, driver, element):
        """Scroll element into view."""
        driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
        self.human_wait("action")


# Singleton instance
browser = BrowserDriver()


def refresh_and_ensure_fresh(driver, platform_name="Webpage", timeout=20):
    """Module-level helper to refresh a page and ensure all fresh content is visible."""
    return browser.refresh_and_ensure_fresh(driver, platform_name=platform_name, timeout=timeout)
