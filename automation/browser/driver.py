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


class BrowserDriver:
    """Manages Chrome browser instances with persistent profiles."""

    def __init__(self):
        self.drivers = {}  # platform -> driver instance

    def get_driver(self, platform):
        """Get or create a Chrome driver for a specific platform."""
        if not HAS_SELENIUM:
            raise RuntimeError("Selenium is not installed. Run: pip install undetected-chromedriver selenium")

        if platform in self.drivers:
            try:
                # Check if driver is still alive
                self.drivers[platform].title
                return self.drivers[platform]
            except Exception:
                del self.drivers[platform]

        profile_dir = PLATFORM_PROFILES.get(platform)
        if not profile_dir:
            raise ValueError(f"Unknown platform: {platform}")

        profile_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Creating Chrome driver for {platform} with profile: {profile_dir}")

        options = uc.ChromeOptions()
        options.add_argument(f"--user-data-dir={profile_dir}")
        options.add_argument(f"--window-size={CHROME_OPTIONS['window_size'][0]},{CHROME_OPTIONS['window_size'][1]}")

        # Anti-detection settings
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--no-first-run")
        options.add_argument("--no-service-autorun")
        options.add_argument("--password-store=basic")

        version_main = get_chrome_version_main()
        if version_main:
            driver = uc.Chrome(options=options, version_main=version_main)
        else:
            driver = uc.Chrome(options=options)

        driver.set_page_load_timeout(TIMEOUTS["page_load"])

        self.drivers[platform] = driver
        return driver

    def navigate(self, platform, url=None):
        """Navigate to a URL or the platform's default URL."""
        driver = self.get_driver(platform)
        target_url = url or PLATFORM_URLS.get(platform, "https://google.com")
        logger.info(f"Navigating {platform} to {target_url}")
        driver.get(target_url)
        self.human_wait("page")
        return driver

    def close(self, platform):
        """Close a specific browser instance."""
        if platform in self.drivers:
            try:
                self.drivers[platform].quit()
            except Exception:
                pass
            del self.drivers[platform]

    def close_all(self):
        """Close all browser instances."""
        for platform in list(self.drivers.keys()):
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
