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
        "--disable-background-timer-throttling",
        "--disable-backgrounding-occluded-windows",
        "--disable-renderer-backgrounding",
        "--disable-features=CalculateNativeWinOcclusion,IntensiveWakeUpThrottling,AutomaticTabDiscarding,FreezingOnBatterySaver",
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


import threading
from contextlib import contextmanager

class BrowserDriver:
    """Manages Chrome browser instances with persistent profiles or attached user browser."""

    def __init__(self):
        self.drivers = {}  # platform -> driver instance
        self.lock = threading.RLock()  # Thread-safe reentrant lock across concurrent tasks
        self.platform_tabs = {}  # platform -> window_handle for tab isolation
        self._watchdog_started = False
        self._start_health_watchdog()

    def _start_health_watchdog(self):
        """Starts a background daemon thread that checks idle tabs periodically to auto-heal blank white screens."""
        if self._watchdog_started:
            return
        self._watchdog_started = True

        def _watchdog_loop():
            while True:
                time.sleep(35)
                try:
                    # Non-blocking lock check: Only check health if no bot task is currently holding the lock
                    acquired = self.lock.acquire(blocking=False)
                    if not acquired:
                        continue
                    try:
                        shared_driver = self.drivers.get("_shared_debug_driver")
                        if not shared_driver:
                            continue
                        try:
                            handles = shared_driver.window_handles
                        except Exception:
                            continue

                        for platform, handle in list(self.platform_tabs.items()):
                            if handle in handles:
                                try:
                                    shared_driver.switch_to.window(handle)
                                    if self.is_blank_or_unrendered(shared_driver):
                                        logger.warning(f"⚡ Background Watchdog: {platform.capitalize()} tab was blank white! Auto-refreshing...")
                                        self.ensure_healthy_page(shared_driver, platform)
                                except Exception:
                                    pass
                    finally:
                        self.lock.release()
                except Exception:
                    pass

        t = threading.Thread(target=_watchdog_loop, daemon=True, name="ManvxiTabHealthWatchdog")
        t.start()

    def is_blank_or_unrendered(self, driver) -> bool:
        """
        Detects if the webpage is currently in an unrendered blank white state,
        crashed React shell, empty body, or disconnected DOM state.
        """
        try:
            res = driver.execute_script("""
                if (!document || !document.body) return { blank: true, reason: 'no_body' };

                // 1. Chrome error / crash page detection
                var title = (document.title || '').trim().toLowerCase();
                if (document.getElementById('main-frame-error') || title.includes('aw, snap') || title.includes('error')) {
                    return { blank: true, reason: 'chrome_error_or_crash' };
                }

                var text = (document.body.innerText || '').trim();
                var divs = document.querySelectorAll('div').length;
                var interactives = document.querySelectorAll('button, a, input, [role="button"]').length;
                var hasMain = !!document.querySelector('main, [role="main"], [data-pagelet], #facebook, #react-root, section, article');

                // 2. Completely empty or zero interactives and zero text
                if (interactives === 0 && text.length < 30) {
                    return { blank: true, reason: 'zero_interactives_no_text', divs: divs, interactives: interactives, text_len: text.length };
                }

                // 3. Blank white screen: low divs, near-zero interactives, almost no text
                if (divs < 30 && interactives < 2 && text.length < 50) {
                    return { blank: true, reason: 'empty_dom', divs: divs, interactives: interactives, text_len: text.length };
                }

                // 4. Meta applications (Facebook / Instagram): missing main app container with minimal text
                var href = window.location.href.toLowerCase();
                var isMetaApp = href.includes('facebook.com') || href.includes('instagram.com');
                if (isMetaApp && !hasMain && interactives < 5 && text.length < 80) {
                    return { blank: true, reason: 'missing_meta_main_container', divs: divs, interactives: interactives };
                }

                // 5. Unmounted React root or empty mount container
                var root = document.getElementById('react-root') || document.querySelector('[data-reactroot]') || document.querySelector("div[id^='mount_0_']");
                if (root && root.children.length === 0 && divs < 20) {
                    return { blank: true, reason: 'empty_root_children' };
                }

                return { blank: false, divs: divs, interactives: interactives, text_len: text.length };
            """)
            if isinstance(res, dict) and res.get("blank"):
                return True
            return False
        except Exception as e:
            logger.debug(f"Blank check exception (page likely unresponsive or crashed): {e}")
            return True

    def ensure_healthy_page(self, driver, platform: str, target_url: str = None) -> bool:
        """
        Auto-recovers from blank white screen or frozen background tab.
        If blank white is detected, executes clean refresh, rehydrates the DOM,
        and waits for interactive elements to appear.
        Also installs an in-browser watchdog to auto-refresh if the tab ever blanks out.
        """
        try:
            # 1. Wake up window and fire visibility events in case React is sleeping
            try:
                driver.execute_script("window.focus(); document.dispatchEvent(new Event('visibilitychange'));")
            except Exception:
                pass

            # 2. Check if page is currently in a blank white screen state
            if self.is_blank_or_unrendered(driver):
                curr_u = getattr(driver, "current_url", "unknown")
                logger.warning(f"⚠️ Blank white screen detected on {platform.capitalize()} ({curr_u})! Auto-refreshing and rehydrating...")
                try:
                    if target_url and "http" in target_url:
                        driver.get(target_url)
                    else:
                        driver.refresh()

                    # Settle and poll until healthy render
                    time.sleep(2.0)
                    for attempt in range(10):
                        if not self.is_blank_or_unrendered(driver):
                            logger.info(f"✅ {platform.capitalize()} auto-recovered successfully from blank white screen! DOM active & hydrated.")
                            break
                        time.sleep(0.8)
                except Exception as e_ref:
                    logger.warning(f"Auto-recovery refresh error: {e_ref}")

            # 3. Inject lightweight client-side watchdog to auto-refresh if tab blanks out while idle
            try:
                driver.execute_script("""
                    if (!window.__manvxi_blank_guard_installed) {
                        window.__manvxi_blank_guard_installed = true;
                        window.__blank_tick_count = 0;
                        setInterval(function() {
                            try {
                                if (!document || !document.body) return;
                                var text = (document.body.innerText || '').trim();
                                var interactives = document.querySelectorAll('button, a, input, [role="button"]').length;
                                var hasMain = !!document.querySelector('main, [role="main"], [data-pagelet], #facebook, #react-root, section');

                                // Blank condition: virtually no text and no interactives
                                if (interactives === 0 && text.length < 20 && !hasMain) {
                                    window.__blank_tick_count = (window.__blank_tick_count || 0) + 1;
                                    // If blank for 2 consecutive checks (approx 10s), auto-refresh
                                    if (window.__blank_tick_count >= 2) {
                                        console.warn('[Manvxi Guard] Blank white screen detected in tab! Auto-reloading page...');
                                        window.__blank_tick_count = 0;
                                        location.reload();
                                    }
                                } else {
                                    window.__blank_tick_count = 0;
                                }
                            } catch(e) {}
                        }, 5000);
                    }
                """)
            except Exception:
                pass

        except Exception as e:
            logger.debug(f"ensure_healthy_page note: {e}")
        return True

    @contextmanager
    def tab_focus(self, platform: str, url: str = None, refresh_first: bool = False):
        """
        Thread-safe context manager that acquires the browser lock and ensures
        the active tab is isolated to the requested platform.
        Auto-detects and recovers from blank white screens before yielding.
        Releases the lock on exit so concurrent tasks can interleave safely without collisions.
        """
        with self.lock:
            driver = self.get_driver(platform)
            if getattr(driver, "_is_shared", False):
                self.switch_to_platform_tab(platform, target_url=url, driver=driver)
            elif url and driver.current_url.rstrip('/') != url.rstrip('/'):
                driver.get(url)
                if refresh_first:
                    self.refresh_and_ensure_fresh(driver, platform_name=platform.capitalize())

            # Self-healing check: Verify page isn't in blank white screen state
            self.ensure_healthy_page(driver, platform, target_url=url)

            yield driver

    tab_context = tab_focus

    def switch_to_platform_tab(self, platform: str, target_url: str = None, driver = None):
        """Switches to the designated tab for platform, creating one if not present, and ensures it is rendered."""
        with self.lock:
            driver = driver or self.get_driver(platform)
            target_url = target_url or PLATFORM_URLS.get(platform, "https://google.com")
            import urllib.parse
            target_netloc = urllib.parse.urlparse(target_url).netloc.lower()

            # 1. Check if we already have a saved window handle that is still open
            saved_handle = self.platform_tabs.get(platform)
            if saved_handle and saved_handle in driver.window_handles:
                try:
                    driver.switch_to.window(saved_handle)
                    current_netloc = urllib.parse.urlparse(driver.current_url).netloc.lower()
                    if target_netloc and (target_netloc in current_netloc or current_netloc in target_netloc):
                        if target_url and target_url != PLATFORM_URLS.get(platform, "https://google.com"):
                            cur_clean = driver.current_url.rstrip('/')
                            tgt_clean = target_url.rstrip('/')
                            if cur_clean != tgt_clean and not cur_clean.startswith(tgt_clean):
                                driver.get(target_url)
                        # Wake up and auto-heal blank screen
                        self.ensure_healthy_page(driver, platform, target_url=target_url)
                        return driver
                except Exception:
                    pass

            # 2. Search existing window handles for a tab matching the target domain
            for handle in driver.window_handles:
                try:
                    driver.switch_to.window(handle)
                    current_netloc = urllib.parse.urlparse(driver.current_url).netloc.lower()
                    if target_netloc and (target_netloc in current_netloc or current_netloc in target_netloc):
                        self.platform_tabs[platform] = handle
                        if target_url and target_url != PLATFORM_URLS.get(platform, "https://google.com"):
                            cur_clean = driver.current_url.rstrip('/')
                            tgt_clean = target_url.rstrip('/')
                            if cur_clean != tgt_clean and not cur_clean.startswith(tgt_clean):
                                driver.get(target_url)
                        # Wake up and auto-heal blank screen
                        self.ensure_healthy_page(driver, platform, target_url=target_url)
                        return driver
                except Exception:
                    continue

            # 3. If no matching tab exists, create a new tab and record its handle
            try:
                driver.switch_to.new_window('tab')
                driver.get(target_url)
                self.platform_tabs[platform] = driver.current_window_handle
                time.sleep(1.0)
            except Exception as e_new:
                logger.warning(f"Could not open new tab for {platform}: {e_new}")
                driver.get(target_url)
                self.platform_tabs[platform] = driver.current_window_handle

            self.ensure_healthy_page(driver, platform, target_url=target_url)
            return driver

    def get_driver(self, platform):
        """Get or create a Chrome driver. Prioritizes connecting to user's open browser if port 9222 is active."""
        with self.lock:
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
        # Anti-tab-freezing, prevent background tab discarding and sleeping
        sel_opts.add_argument("--disable-background-timer-throttling")
        sel_opts.add_argument("--disable-backgrounding-occluded-windows")
        sel_opts.add_argument("--disable-renderer-backgrounding")
        sel_opts.add_argument("--disable-features=CalculateNativeWinOcclusion,IntensiveWakeUpThrottling,AutomaticTabDiscarding,FreezingOnBatterySaver")
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
        with self.lock:
            import urllib.parse
            driver = self.get_driver(platform)
            target_url = url or PLATFORM_URLS.get(platform, "https://google.com")
            logger.info(f"Navigating {platform} to {target_url} (refresh_first={refresh_first})")

            if getattr(driver, "_is_shared", False):
                self.switch_to_platform_tab(platform, target_url=target_url, driver=driver)
                cur_clean = driver.current_url.rstrip('/')
                tgt_clean = target_url.rstrip('/')
                if cur_clean != tgt_clean:
                    driver.get(target_url)
                elif refresh_first:
                    self.refresh_and_ensure_fresh(driver, platform_name=platform.capitalize())
            else:
                driver.get(target_url)

            if refresh_first and not getattr(driver, "_is_shared", False):
                self.refresh_and_ensure_fresh(driver, platform_name=platform.capitalize())
            else:
                self.human_wait("page")
            self.ensure_healthy_page(driver, platform, target_url=target_url)
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
        with self.lock:
            timeout = timeout or TIMEOUTS["element_wait"]
            return WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )

    def wait_for_clickable(self, driver, by, value, timeout=None):
        """Wait for an element to be clickable and return it."""
        with self.lock:
            timeout = timeout or TIMEOUTS["element_wait"]
            return WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable((by, value))
            )

    def safe_click(self, driver, element):
        """Click an element with human-like behavior."""
        with self.lock:
            self.human_wait("action")
            try:
                element.click()
            except Exception:
                driver.execute_script("arguments[0].click();", element)

    def scroll_to_element(self, driver, element):
        """Scroll element into view."""
        with self.lock:
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
            self.human_wait("action")


# Singleton instance
browser = BrowserDriver()


def refresh_and_ensure_fresh(driver, platform_name="Webpage", timeout=20):
    """Module-level helper to refresh a page and ensure all fresh content is visible."""
    return browser.refresh_and_ensure_fresh(driver, platform_name=platform_name, timeout=timeout)
