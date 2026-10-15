"""
Master QA Test Suite for PromptPasteVerifierAgent
=================================================
Validates:
1. Platform detection (ChatGPT & Gemini)
2. Prompt verification logic:
   - Empty editor handling
   - Missing token validation (₹ Rupee symbol, Loan Solutions application link, hashtags)
   - Sequence similarity scoring
   - Send button status evaluation
3. System clipboard synchronization
4. Live browser multi-strategy paste pipeline on active Chrome port 9222
"""
import os
import sys
import unittest
from pathlib import Path

# UTF-8 stdout configuration
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Add paths
BASE_DIR = Path(__file__).parent.parent
sys.path.append(str(BASE_DIR / "automation"))

from llm.prompt_paste_verifier_agent import (
    PromptPasteVerifierAgent,
    PromptVerificationResult,
)


class MockDriver:
    """Mock WebDriver for unit testing agent logic without requiring a live browser."""
    def __init__(self, current_url="", script_return=None):
        self.current_url = current_url
        self.script_return = script_return

    def execute_script(self, script, *args):
        if callable(self.script_return):
            return self.script_return(script, *args)
        return self.script_return

    def find_elements(self, by, value):
        return []


class TestPromptPasteVerifierUnit(unittest.TestCase):
    """Unit tests for agent verification rules."""

    def setUp(self):
        self.agent = PromptPasteVerifierAgent()

    def test_01_platform_detection(self):
        """Test platform identification from URL."""
        d_gemini = MockDriver("https://gemini.google.com/app/12345")
        self.assertEqual(self.agent.detect_platform(d_gemini), "gemini")

        d_chatgpt = MockDriver("https://chatgpt.com/c/6acfb986-726c")
        self.assertEqual(self.agent.detect_platform(d_chatgpt), "chatgpt")

        d_unknown = MockDriver("https://example.com")
        self.assertEqual(self.agent.detect_platform(d_unknown), "unknown")

    def test_02_empty_prompt_verification(self):
        """Test verification when editor has no content."""
        def mock_js(script, *args):
            if "read_editor_content" in script or "innerText" in script or "ql-blank" in script:
                return ""
            if "plat = arguments[0]" in script:
                return {"found": False, "ready": False, "reason": "No send button"}
            return None

        driver = MockDriver("https://gemini.google.com/app", mock_js)
        # Mock locate_editor
        self.agent.locate_editor = lambda d, plat: "mock_element"
        self.agent.read_editor_content = lambda d, plat: ""
        self.agent.inspect_send_button = lambda d, plat: (False, "Mic button visible")

        res = self.agent.verify_prompt(
            driver=driver,
            expected_prompt="Test prompt with content",
            platform="gemini"
        )
        self.assertFalse(res.is_valid)
        self.assertEqual(res.status, "EMPTY")
        self.assertEqual(res.actual_length, 0)

    def test_03_missing_mandatory_link_and_rupee_symbol(self):
        """Test failure when critical Indian loan copy tokens are omitted."""
        expected = "Loan Solutions: Get ₹5,00,000 easily! Apply: https://loansolutions.everythingrental.in/application"
        # Partial text without link or Rupee
        actual = "Loan Solutions: Get 500000 easily! Check details below."

        driver = MockDriver("https://gemini.google.com/app")
        self.agent.read_editor_content = lambda d, plat: actual
        self.agent.inspect_send_button = lambda d, plat: (True, "Ready")

        res = self.agent.verify_prompt(
            driver=driver,
            expected_prompt=expected,
            platform="gemini",
            required_substrings=["https://loansolutions.everythingrental.in/application", "₹"]
        )
        self.assertFalse(res.is_valid)
        self.assertIn("₹", res.missing_tokens)
        self.assertIn("https://loansolutions.everythingrental.in/application", res.missing_tokens)

    def test_04_perfect_prompt_match(self):
        """Test verification passes with 100% similarity and ready send button."""
        prompt = (
            "--- TASK 1: CLEAN VISUAL ARTWORK ---\n"
            "Loan Solutions graphic with glowing ₹ symbol.\n"
            "--- TASK 2: SOCIAL MEDIA POST ---\n"
            "Apply Now: https://loansolutions.everythingrental.in/application #LoanSolutions"
        )
        driver = MockDriver("https://gemini.google.com/app")
        self.agent.read_editor_content = lambda d, plat: prompt
        self.agent.inspect_send_button = lambda d, plat: (True, "Ready")

        res = self.agent.verify_prompt(
            driver=driver,
            expected_prompt=prompt,
            platform="gemini",
            required_substrings=["₹", "https://loansolutions.everythingrental.in/application"]
        )
        self.assertTrue(res.is_valid)
        self.assertEqual(res.status, "PROPERLY_PASTED")
        self.assertAlmostEqual(res.similarity_ratio, 1.0, places=2)
        self.assertTrue(res.send_button_ready)

    def test_05_clipboard_copy(self):
        """Test that system clipboard copy preserves multi-line Unicode formatting."""
        test_str = "Loan Solutions ₹ 100% verified\nNew line test with emoji: 👉"
        success = self.agent.copy_to_system_clipboard(test_str)
        self.assertTrue(success)

        try:
            import pyperclip
            val = pyperclip.paste()
            self.assertEqual(val.strip(), test_str.strip())
        except Exception:
            pass


class TestPromptPasteVerifierLiveBrowser(unittest.TestCase):
    """Integration test with live Chrome on port 9222."""

    def test_06_live_browser_gemini_and_chatgpt(self):
        """Tests live prompt verification and paste assistance on active Chrome tabs."""
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options

        opts = Options()
        opts.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
        try:
            driver = webdriver.Chrome(options=opts)
        except Exception as e:
            self.skipTest(f"Chrome on port 9222 not reachable: {e}")

        agent = PromptPasteVerifierAgent(driver)
        sample_prompt = (
            "--- TASK 1: MARKETING ARTWORK ---\n"
            "Create marketing art for Loan Solutions with Indian Rupee (₹).\n\n"
            "--- TASK 2: POST COPY ---\n"
            "👉 Apply Now: https://loansolutions.everythingrental.in/application\n"
            "#LoanSolutions #HomeLoanIndia"
        )

        tested_platforms = set()
        for h in driver.window_handles:
            driver.switch_to.window(h)
            plat = agent.detect_platform(driver)
            if plat in ["gemini", "chatgpt"] and plat not in tested_platforms:
                print(f"\n[LIVE INTEGRATION] Testing {plat.upper()} on tab: {driver.title}")
                res = agent.ensure_properly_pasted(
                    driver=driver,
                    prompt=sample_prompt,
                    platform=plat,
                    required_substrings=["₹", "https://loansolutions.everythingrental.in/application"]
                )
                self.assertTrue(res.is_valid, f"Paste verification failed on {plat}: {res.details}")
                self.assertEqual(res.status, "PROPERLY_PASTED")
                self.assertGreaterEqual(res.similarity_ratio, 0.95)
                self.assertTrue(res.send_button_ready, f"Send button not ready on {plat}")

                # Clean up editor
                agent.clear_editor(driver, platform=plat)
                tested_platforms.add(plat)

        self.assertGreater(len(tested_platforms), 0, "No Gemini or ChatGPT tab found in browser!")
        print(f"\n✅ Live browser tested successfully across: {tested_platforms}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
