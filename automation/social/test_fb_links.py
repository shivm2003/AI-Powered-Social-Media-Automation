import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent
sys.path.append(str(BASE_DIR / "automation"))

from browser.driver import browser
from selenium.webdriver.common.by import By

driver = browser.navigate("facebook", "https://www.facebook.com/search/people/?q=New%20Delhi")
time.sleep(2)

xpaths = [
    "//div[@role='button'][contains(translate(@aria-label, 'AD', 'ad'), 'add friend') and not(@data-bot-sent='true')]",
    "//div[contains(translate(@aria-label, 'AD', 'ad'), 'add friend') and not(@data-bot-sent='true')]",
    "//span[contains(translate(text(), 'AD', 'ad'), 'add friend') and not(ancestor::div[@data-bot-sent='true'])]/ancestor::div[@role='button'][1]",
    "//span[contains(translate(text(), 'AD', 'ad'), 'add friend') and not(ancestor::div[@data-bot-sent='true'])]/ancestor::div[1]",
]

add_buttons = []
seen_ids = set()
for xp in xpaths:
    for cand in driver.find_elements(By.XPATH, xp):
        if cand.is_displayed() and cand.id not in seen_ids:
            seen_ids.add(cand.id)
            add_buttons.append(cand)

print(f"Total buttons: {len(add_buttons)}")

for i, btn in enumerate(add_buttons[:6]):
    print(f"\n--- Candidate {i+1} ---")
    for level in range(1, 10):
        try:
            card = btn.find_element(By.XPATH, f"./ancestor::div[{level}]")
            links = card.find_elements(By.CSS_SELECTOR, "a[role='link'], a[href*='facebook.com/'], a[href*='profile.php']")
            found_person_links = []
            for l in links:
                ltxt = l.text.strip().replace("\n", " ")
                lhref = l.get_attribute("href") or ""
                found_person_links.append((ltxt, lhref))
            if found_person_links:
                print(f"  Level {level}: {found_person_links[:4]}")
                break
        except Exception:
            pass
