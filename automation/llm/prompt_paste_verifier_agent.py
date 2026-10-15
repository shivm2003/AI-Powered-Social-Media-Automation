"""
Prompt Paste Verifier Agent for ChatGPT & Google Gemini
======================================================
An intelligent agent that:
1. Inspects the active composer in ChatGPT or Google Gemini.
2. Verifies whether the prompt was pasted properly (checks text presence, length,
   similarity ratio, mandatory anchors like Indian Rupee ₹, CTA links, hashtags,
   and send button activation).
3. If not properly pasted (empty, truncated, corrupted, or synthetic state un-triggered),
   the agent actively assists and pastes the prompt using a battle-tested multi-strategy
   pipeline (OS clipboard + native ActionChains Ctrl+V, Synthetic DataTransfer events,
   Quill/ProseMirror framework state synchronizers).
4. Confirms verification and prepares the prompt for reliable dispatch.
"""
import os
import sys
import time
import logging
import difflib
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, asdict

# Ensure UTF-8 output on Windows
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

try:
    import pyperclip
except ImportError:
    pyperclip = None

logger = logging.getLogger("automation.llm.prompt_paste_verifier")
if not logger.handlers:
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(logging.Formatter("[%(asctime)s][%(name)s][%(levelname)s] %(message)s"))
    logger.addHandler(ch)
    logger.setLevel(logging.INFO)


@dataclass
class PromptVerificationResult:
    is_valid: bool
    status: str  # 'PROPERLY_PASTED', 'EMPTY', 'PARTIAL', 'CORRUPTED', 'SEND_BLOCKED', 'ERROR'
    platform: str
    expected_length: int
    actual_length: int
    similarity_ratio: float
    missing_tokens: List[str]
    send_button_ready: bool
    method_used: str = "initial_check"
    details: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class PromptPasteVerifierAgent:
    """
    Dedicated AI Agent for verifying and remediating prompt entry across
    ChatGPT and Google Gemini web interfaces.
    """

    def __init__(self, driver=None, default_min_similarity: float = 0.90):
        self.driver = driver
        self.default_min_similarity = default_min_similarity

    def set_driver(self, driver):
        self.driver = driver

    def detect_platform(self, driver=None) -> str:
        """Detects whether active tab is ChatGPT or Gemini."""
        d = driver or self.driver
        if not d:
            return "unknown"
        url = (d.current_url or "").lower()
        if "gemini.google.com" in url:
            return "gemini"
        if "chatgpt.com" in url or "openai.com" in url:
            return "chatgpt"
        return "unknown"

    def locate_editor(self, driver=None, platform: str = None):
        """
        Locates the exact, currently active contenteditable/textarea composer element.
        Filters out historical chat messages, sidebars, and hidden clipboard divs.
        """
        from selenium.webdriver.common.by import By

        d = driver or self.driver
        if not d:
            raise RuntimeError("WebDriver instance is required to locate editor.")

        plat = platform or self.detect_platform(d)

        if plat == "gemini":
            selectors = [
                "rich-textarea div.ql-editor[contenteditable='true']",
                "rich-textarea div[contenteditable='true']:not(.ql-clipboard)",
                "div.ql-editor.textarea[contenteditable='true']",
                "div.ql-editor[contenteditable='true']",
                "rich-textarea p",
                "textarea[aria-label*='prompt' i]",
            ]
        elif plat == "chatgpt":
            selectors = [
                "div[contenteditable='true'][aria-label*='Ask' i]",
                "div[contenteditable='true'][aria-label*='Message' i]",
                "[class*='composer'] div[contenteditable='true']",
                "div[contenteditable='true'][data-placeholder*='Ask' i]",
                "div[contenteditable='true'][data-placeholder*='Message' i]",
                "#prompt-textarea",
                "div[contenteditable='true'].ProseMirror:not([aria-label*='writing' i]):not(.content-xaiQhS)",
                "textarea[data-id='root']",
                "div[contenteditable='true']",
            ]
        else:
            selectors = [
                "rich-textarea div[contenteditable='true']",
                "div[contenteditable='true'][aria-label*='Ask' i]",
                "#prompt-textarea",
                "div.ql-editor[contenteditable='true']",
                "div[contenteditable='true']",
                "textarea",
            ]

        for sel in selectors:
            try:
                candidates = d.find_elements(By.CSS_SELECTOR, sel)
                valid_candidates = []
                for el in candidates:
                    # Check geometry: must be visible, have realistic editor dimensions, and not be historical writing blocks
                    rect = d.execute_script("""
                        const el = arguments[0];
                        const r = el.getBoundingClientRect();
                        const isHidden = (el.offsetParent === null && window.getComputedStyle(el).position !== 'fixed');
                        const aria = (el.getAttribute('aria-label') || '').toLowerCase();
                        const isWritingBlock = aria.includes('start writing') || aria.includes('writing block');
                        return {
                            x: r.x,
                            y: r.y,
                            w: r.width,
                            h: r.height,
                            visible: !isHidden && r.width >= 50 && r.height >= 15 && !isWritingBlock
                        };
                    """, el)
                    if rect and rect.get("visible"):
                        valid_candidates.append((rect.get("y", 0), el))

                if valid_candidates:
                    # Sort by Y position descending (bottom-most in viewport is the active composer)
                    valid_candidates.sort(key=lambda item: item[0], reverse=True)
                    return valid_candidates[0][1]
            except Exception:
                continue

        return None

    def read_editor_content(self, driver=None, platform: str = None) -> str:
        """Extracts current raw text from the active editor."""
        d = driver or self.driver
        plat = platform or self.detect_platform(d)
        editor = self.locate_editor(d, plat)
        if not editor:
            return ""

        try:
            val = d.execute_script("""
                const el = arguments[0];
                if (!el) return '';
                if (el.tagName === 'TEXTAREA' || el.tagName === 'INPUT') {
                    return el.value || '';
                }
                const txt = el.innerText || el.textContent || '';
                // If only newline or whitespace
                if (!txt.trim()) return '';
                return txt;
            """, editor)
            return (val or "").strip()
        except Exception as e:
            logger.warning(f"Error reading editor content: {e}")
            return ""

    def inspect_send_button(self, driver=None, platform: str = None) -> Tuple[bool, Optional[str]]:
        """
        Inspects if the platform's send/submit button is available and active (ready to click).
        Returns (is_ready, details_str).
        """
        d = driver or self.driver
        plat = platform or self.detect_platform(d)

        btn_info = d.execute_script("""
            const plat = arguments[0];
            const btns = Array.from(document.querySelectorAll('button, [role="button"]'));
            
            let sendBtn = null;
            if (plat === 'gemini') {
                sendBtn = btns.find(b => {
                    const aria = (b.getAttribute('aria-label') || '').toLowerCase().trim();
                    const txt = (b.innerText || '').toLowerCase().trim();
                    const cls = (b.className || '').toLowerCase();
                    return aria === 'send' || aria.includes('send') || aria.includes('submit') || txt === 'send' || cls.includes('send-button');
                });
            } else if (plat === 'chatgpt') {
                sendBtn = btns.find(b => {
                    const testid = (b.getAttribute('data-testid') || '').toLowerCase();
                    const aria = (b.getAttribute('aria-label') || '').toLowerCase().trim();
                    const cls = (b.className || '').toLowerCase();
                    return aria === 'send' || aria.startsWith('send') || testid === 'send-button' || testid.includes('send') || cls.includes('size-token-button-composer');
                });
            } else {
                sendBtn = btns.find(b => {
                    const aria = (b.getAttribute('aria-label') || '').toLowerCase().trim();
                    const testid = (b.getAttribute('data-testid') || '').toLowerCase();
                    return aria === 'send' || aria.includes('send') || testid.includes('send');
                });
            }

            if (!sendBtn) {
                return { found: false, ready: false, reason: 'Send button element not found in DOM' };
            }

            const rect = sendBtn.getBoundingClientRect();
            const isVisible = rect.width > 5 && rect.height > 5;
            const isDisabled = sendBtn.disabled || sendBtn.getAttribute('aria-disabled') === 'true';

            return {
                found: true,
                ready: isVisible && !isDisabled,
                aria: sendBtn.getAttribute('aria-label'),
                testid: sendBtn.getAttribute('data-testid'),
                disabled: isDisabled,
                visible: isVisible,
                reason: !isVisible ? 'Hidden or zero-sized' : (isDisabled ? 'Button disabled attribute present' : 'Active and clickable')
            };
        """, plat)

        if not btn_info:
            return False, "Could not query send button"

        is_ready = btn_info.get("ready", False)
        reason = btn_info.get("reason", "")
        return is_ready, reason

    def verify_prompt(
        self,
        driver=None,
        expected_prompt: str = "",
        platform: str = None,
        min_similarity: Optional[float] = None,
        required_substrings: Optional[List[str]] = None,
    ) -> PromptVerificationResult:
        """
        Verifies whether the prompt currently inside the editor matches expected criteria.
        Checks:
        1. Emptiness / null
        2. SequenceMatcher similarity ratio
        3. Mandatory token presence (e.g. ₹, links, hashtags, task titles)
        4. Send button availability
        """
        d = driver or self.driver
        plat = platform or self.detect_platform(d)
        min_sim = min_similarity if min_similarity is not None else self.default_min_similarity

        actual_text = self.read_editor_content(d, plat)
        actual_len = len(actual_text)
        expected_len = len(expected_prompt)

        # Missing token check
        missing_tokens = []
        if required_substrings:
            for req in required_substrings:
                if req not in actual_text:
                    missing_tokens.append(req)

        # Standard check for Indian Rupee if expected
        if "₹" in expected_prompt and "₹" not in actual_text:
            missing_tokens.append("₹")
        # Standard check for application link if expected
        if "https://loansolutions.everythingrental.in/application" in expected_prompt and \
           "https://loansolutions.everythingrental.in/application" not in actual_text:
            missing_tokens.append("https://loansolutions.everythingrental.in/application")

        # Similarity calculation
        if expected_len == 0:
            sim_ratio = 1.0 if actual_len == 0 else 0.0
        else:
            # Normalize whitespace for fair comparison
            norm_expected = " ".join(expected_prompt.split())
            norm_actual = " ".join(actual_text.split())
            sim_ratio = difflib.SequenceMatcher(None, norm_expected, norm_actual).ratio()

        send_ready, send_details = self.inspect_send_button(d, plat)

        # Determine overall verification status
        if actual_len == 0:
            status = "EMPTY"
            is_valid = False
            details = "Editor is completely empty or blank placeholder is active."
        elif sim_ratio < 0.50:
            status = "CORRUPTED"
            is_valid = False
            details = f"Content similarity ({sim_ratio*100:.1f}%) is far below expected threshold ({min_sim*100:.1f}%)."
        elif sim_ratio < min_sim or missing_tokens:
            status = "PARTIAL"
            is_valid = False
            details = f"Content similarity is {sim_ratio*100:.1f}% (<{min_sim*100:.1f}%) or missing critical tokens: {missing_tokens}"
        elif not send_ready:
            # Note: on Gemini, the send button may become ready after focus or space; we flag it
            status = "SEND_BLOCKED"
            is_valid = False
            details = f"Text matched ({sim_ratio*100:.1f}%) but Send button is not ready: {send_details}"
        else:
            status = "PROPERLY_PASTED"
            is_valid = True
            details = f"Prompt verified successfully ({sim_ratio*100:.1f}% match, {actual_len} chars, Send ready)."

        return PromptVerificationResult(
            is_valid=is_valid,
            status=status,
            platform=plat,
            expected_length=expected_len,
            actual_length=actual_len,
            similarity_ratio=round(sim_ratio, 4),
            missing_tokens=missing_tokens,
            send_button_ready=send_ready,
            details=details,
        )

    def clear_editor(self, driver=None, platform: str = None) -> bool:
        """Cleans out any existing text in the editor safely."""
        from selenium.webdriver.common.keys import Keys
        from selenium.webdriver.common.action_chains import ActionChains

        d = driver or self.driver
        plat = platform or self.detect_platform(d)
        editor = self.locate_editor(d, plat)
        if not editor:
            return False

        try:
            try:
                editor.click()
            except Exception:
                d.execute_script("arguments[0].focus(); arguments[0].click();", editor)
            time.sleep(0.2)
            # Select all and delete via ActionChains
            ActionChains(d).key_down(Keys.CONTROL).send_keys('a').key_up(Keys.CONTROL).send_keys(Keys.BACKSPACE).perform()
            time.sleep(0.2)

            # JavaScript DOM fallback reset without TrustedHTML violation
            d.execute_script("""
                const el = arguments[0];
                if (!el) return;
                if (el.tagName === 'TEXTAREA' || el.tagName === 'INPUT') {
                    el.value = '';
                } else {
                    el.textContent = '';
                    if (el.classList) el.classList.add('ql-blank');
                }
                el.dispatchEvent(new Event('input', { bubbles: true }));
                el.dispatchEvent(new Event('change', { bubbles: true }));
            """, editor)
            time.sleep(0.2)
            return True
        except Exception as e:
            logger.warning(f"Notice during clear_editor: {e}")
            return False

    def copy_to_system_clipboard(self, text: str) -> bool:
        """Copies text reliably to system clipboard via pyperclip or PowerShell."""
        import subprocess

        # 1. Try pyperclip
        if pyperclip:
            try:
                pyperclip.copy(text)
                time.sleep(0.1)
                return True
            except Exception:
                pass

        # 2. Try PowerShell Set-Clipboard
        try:
            p = subprocess.Popen(
                ["powershell", "-NoProfile", "-Command", "$input | Set-Clipboard"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8"
            )
            p.communicate(input=text)
            return p.returncode == 0
        except Exception as e:
            logger.warning(f"Could not copy to Windows clipboard: {e}")
            return False

    def help_paste_prompt(
        self,
        driver=None,
        prompt: str = "",
        platform: str = None,
        required_substrings: Optional[List[str]] = None,
    ) -> PromptVerificationResult:
        """
        Active assistance pipeline:
        Uses a cascading multi-strategy paste workflow to ensure the prompt
        is properly inserted and recognized by ChatGPT or Gemini's internal state.
        """
        from selenium.webdriver.common.keys import Keys
        from selenium.webdriver.common.action_chains import ActionChains

        d = driver or self.driver
        plat = platform or self.detect_platform(d)
        logger.info(f"🤖 [PromptPasteVerifierAgent] Initiating paste assistance on '{plat}' ({len(prompt)} chars)...")

        editor = self.locate_editor(d, plat)
        if not editor:
            raise RuntimeError(f"Cannot assist pasting: active editor on '{plat}' could not be located.")

        # --- Strategy 1: System Clipboard + ActionChains Native Ctrl+V (Gold Standard) ---
        logger.info("  👉 Strategy 1: Executing Native OS Clipboard + Keystroke Paste (Ctrl+V)...")
        self.copy_to_system_clipboard(prompt)
        time.sleep(0.2)

        try:
            d.execute_script("arguments[0].scrollIntoView({block: 'center'});", editor)
            time.sleep(0.2)
            editor.click()
            time.sleep(0.2)

            # Clear first
            ActionChains(d).key_down(Keys.CONTROL).send_keys('a').key_up(Keys.CONTROL).send_keys(Keys.BACKSPACE).perform()
            time.sleep(0.2)

            # Paste
            ActionChains(d).key_down(Keys.CONTROL).send_keys('v').key_up(Keys.CONTROL).perform()
            time.sleep(0.8)

            # Verification 1
            res1 = self.verify_prompt(d, prompt, plat, required_substrings=required_substrings)
            if res1.is_valid:
                res1.method_used = "Strategy 1: OS Clipboard + ActionChains Ctrl+V"
                logger.info(f"✅ [PromptPasteVerifierAgent] Strategy 1 SUCCEEDED! ({res1.similarity_ratio*100:.1f}% match)")
                return res1
            else:
                logger.warning(f"  ⚠️ Strategy 1 partial result ({res1.status}): {res1.details}")
        except Exception as e_s1:
            logger.warning(f"  Strategy 1 exception: {e_s1}")

        # --- Strategy 2: Synthetic DataTransfer & ClipboardEvent Paste ---
        logger.info("  👉 Strategy 2: Dispatched Synthetic ClipboardEvent with text/plain DataTransfer...")
        try:
            editor = self.locate_editor(d, plat)
            d.execute_script("""
                const el = arguments[0];
                const text = arguments[1];
                el.focus();
                
                const dt = new DataTransfer();
                dt.setData('text/plain', text);
                
                const pasteEvt = new ClipboardEvent('paste', {
                    bubbles: true,
                    cancelable: true,
                    clipboardData: dt
                });
                
                el.dispatchEvent(pasteEvt);
                el.dispatchEvent(new Event('input', { bubbles: true }));
                el.dispatchEvent(new Event('change', { bubbles: true }));
            """, editor, prompt)
            time.sleep(0.8)

            res2 = self.verify_prompt(d, prompt, plat, required_substrings=required_substrings)
            if res2.is_valid:
                res2.method_used = "Strategy 2: Synthetic ClipboardEvent"
                logger.info(f"✅ [PromptPasteVerifierAgent] Strategy 2 SUCCEEDED! ({res2.similarity_ratio*100:.1f}% match)")
                return res2
            else:
                logger.warning(f"  ⚠️ Strategy 2 result ({res2.status}): {res2.details}")
        except Exception as e_s2:
            logger.warning(f"  Strategy 2 exception: {e_s2}")

        # --- Strategy 3: Selection Range + execCommand('insertText') / beforeinput ---
        logger.info("  👉 Strategy 3: Selection Range with execCommand & beforeinput...")
        try:
            editor = self.locate_editor(d, plat)
            d.execute_script("""
                const el = arguments[0];
                const text = arguments[1];
                el.focus();
                
                const sel = window.getSelection();
                const range = document.createRange();
                range.selectNodeContents(el);
                sel.removeAllRanges();
                sel.addRange(range);
                
                // Try execCommand
                const success = document.execCommand('insertText', false, text);
                if (!success) {
                    // Try dispatching InputEvent
                    const inpEvt = new InputEvent('beforeinput', {
                        bubbles: true,
                        cancelable: true,
                        inputType: 'insertFromPaste',
                        data: text
                    });
                    el.dispatchEvent(inpEvt);
                }
                el.dispatchEvent(new Event('input', { bubbles: true }));
            """, editor, prompt)
            time.sleep(0.8)

            res3 = self.verify_prompt(d, prompt, plat, required_substrings=required_substrings)
            if res3.is_valid:
                res3.method_used = "Strategy 3: Selection Range + execCommand"
                logger.info(f"✅ [PromptPasteVerifierAgent] Strategy 3 SUCCEEDED! ({res3.similarity_ratio*100:.1f}% match)")
                return res3
            else:
                logger.warning(f"  ⚠️ Strategy 3 result ({res3.status}): {res3.details}")
        except Exception as e_s3:
            logger.warning(f"  Strategy 3 exception: {e_s3}")

        # --- Strategy 4: Framework-Specific Structural Node Injector ---
        logger.info(f"  👉 Strategy 4: Framework-Specific Node Injector for '{plat}'...")
        try:
            editor = self.locate_editor(d, plat)
            if plat == "gemini":
                # Gemini Quill: split lines into <p> tags and remove ql-blank
                d.execute_script("""
                    const el = arguments[0];
                    const text = arguments[1];
                    el.focus();
                    el.classList.remove('ql-blank');
                    
                    const lines = text.split('\\n');
                    el.innerHTML = lines.map(line => `<p>${line.length ? line : '<br>'}</p>`).join('');
                    
                    el.dispatchEvent(new Event('input', { bubbles: true }));
                    el.dispatchEvent(new Event('change', { bubbles: true }));
                    el.dispatchEvent(new Event('blur', { bubbles: true }));
                    el.focus();
                """, editor, prompt)
            elif plat == "chatgpt":
                # ChatGPT ProseMirror: split lines into <p> tags
                d.execute_script("""
                    const el = arguments[0];
                    const text = arguments[1];
                    el.focus();
                    
                    const lines = text.split('\\n');
                    el.innerHTML = lines.map(line => `<p>${line.length ? line : '<br>'}</p>`).join('');
                    
                    el.dispatchEvent(new Event('input', { bubbles: true }));
                    el.dispatchEvent(new Event('change', { bubbles: true }));
                    el.dispatchEvent(new Event('compositionend', { bubbles: true }));
                """, editor, prompt)

            # Type a space and backspace to trigger synthetic input listener
            time.sleep(0.3)
            ActionChains(d).send_keys(" ").send_keys(Keys.BACKSPACE).perform()
            time.sleep(0.8)

            res4 = self.verify_prompt(d, prompt, plat, required_substrings=required_substrings)
            if res4.is_valid:
                res4.method_used = "Strategy 4: Framework Node Injector"
                logger.info(f"✅ [PromptPasteVerifierAgent] Strategy 4 SUCCEEDED! ({res4.similarity_ratio*100:.1f}% match)")
                return res4
            else:
                logger.warning(f"  ⚠️ Strategy 4 result ({res4.status}): {res4.details}")
        except Exception as e_s4:
            logger.warning(f"  Strategy 4 exception: {e_s4}")

        # Final check & return
        final_res = self.verify_prompt(d, prompt, plat, required_substrings=required_substrings)
        final_res.method_used = "All strategies attempted"
        return final_res

    def ensure_properly_pasted(
        self,
        driver=None,
        prompt: str = "",
        platform: str = None,
        required_substrings: Optional[List[str]] = None,
    ) -> PromptVerificationResult:
        """
        Master method:
        1. Verifies if current prompt is already properly pasted.
        2. If YES: returns immediate success.
        3. If NO: runs help_paste_prompt() pipeline.
        4. If still not valid, highlights the editor with visual glowing cues
           and keeps system clipboard primed for instant 1-click human paste.
        """
        d = driver or self.driver
        plat = platform or self.detect_platform(d)

        logger.info(f"🔍 [PromptPasteVerifierAgent] Verifying prompt on '{plat}'...")
        initial_check = self.verify_prompt(d, prompt, plat, required_substrings=required_substrings)
        if initial_check.is_valid:
            logger.info(f"✨ [PromptPasteVerifierAgent] Prompt is ALREADY properly pasted ({initial_check.actual_length} chars, Send ready)!")
            return initial_check

        logger.info(f"⚡ [PromptPasteVerifierAgent] Prompt NOT properly pasted ({initial_check.status}: {initial_check.details}). Engaging paste assistance...")
        result = self.help_paste_prompt(d, prompt, plat, required_substrings=required_substrings)

        if not result.is_valid:
            # Assistive fallback: prime clipboard and highlight editor visually
            self.copy_to_system_clipboard(prompt)
            editor = self.locate_editor(d, plat)
            if editor:
                try:
                    d.execute_script("""
                        const el = arguments[0];
                        el.style.outline = '4px solid #10B981';
                        el.style.boxShadow = '0 0 20px rgba(16, 185, 129, 0.6)';
                        el.focus();
                    """, editor)
                except Exception:
                    pass
            logger.warning(f"⚠️ [PromptPasteVerifierAgent] Automation paste could not reach 100% verification ({result.status}). Clipboard primed with prompt and editor highlighted.")

        return result

    def click_send(self, driver=None, platform: str = None) -> bool:
        """Finds the platform's active send button and executes the click dispatch."""
        from selenium.webdriver.common.keys import Keys

        d = driver or self.driver
        plat = platform or self.detect_platform(d)
        editor = self.locate_editor(d, plat)

        clicked = d.execute_script("""
            const plat = arguments[0];
            const btns = Array.from(document.querySelectorAll('button, [role="button"]'));
            let sendBtn = null;
            if (plat === 'gemini') {
                sendBtn = btns.find(b => {
                    const aria = (b.getAttribute('aria-label') || '').toLowerCase().trim();
                    const txt = (b.innerText || '').toLowerCase().trim();
                    const cls = (b.className || '').toLowerCase();
                    return (aria === 'send' || aria.includes('send') || aria.includes('submit') || txt === 'send' || cls.includes('send-button')) && !b.disabled && b.getAttribute('aria-disabled') !== 'true';
                });
            } else if (plat === 'chatgpt') {
                sendBtn = btns.find(b => {
                    const testid = (b.getAttribute('data-testid') || '').toLowerCase();
                    const aria = (b.getAttribute('aria-label') || '').toLowerCase().trim();
                    const cls = (b.className || '').toLowerCase();
                    return (aria === 'send' || aria.startsWith('send') || testid === 'send-button' || testid.includes('send') || cls.includes('size-token-button-composer')) && !b.disabled && b.getAttribute('aria-disabled') !== 'true';
                });
            } else {
                sendBtn = btns.find(b => {
                    const aria = (b.getAttribute('aria-label') || '').toLowerCase().trim();
                    return (aria === 'send' || aria.includes('send')) && !b.disabled;
                });
            }

            if (sendBtn) {
                sendBtn.click();
                return true;
            }
            return false;
        """, plat)

        if clicked:
            logger.info(f"🚀 [PromptPasteVerifierAgent] Clicked Send button successfully on '{plat}'!")
            return True

        # Enter key fallback on editor
        if editor:
            try:
                editor.send_keys(Keys.ENTER)
                logger.info(f"🚀 [PromptPasteVerifierAgent] Dispatched ENTER key fallback on '{plat}'!")
                return True
            except Exception as e_enter:
                logger.warning(f"Send fallback error: {e_enter}")

        return False


# Singleton instance for direct import
prompt_verifier_agent = PromptPasteVerifierAgent()


if __name__ == "__main__":
    import argparse
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options

    parser = argparse.ArgumentParser(description="Prompt Paste Verifier Agent CLI")
    parser.add_argument("--platform", choices=["gemini", "chatgpt", "auto"], default="auto")
    parser.add_argument("--verify-only", action="store_true", help="Only verify current editor without modifying")
    parser.add_argument("--test", action="store_true", help="Run a full paste & verify test on the active window")
    args = parser.parse_args()

    opts = Options()
    opts.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    try:
        driver = webdriver.Chrome(options=opts)
    except Exception as e:
        print(f"Error connecting to Chrome on 9222: {e}")
        sys.exit(1)

    agent = PromptPasteVerifierAgent(driver)

    sample_prompt = (
        "--- TASK 1: CLEAN VISUAL ARTWORK (IMAGE GENERATION) ---\n"
        "Generate a clean, high-converting commercial marketing image for 'Loan Solutions'.\n"
        "A warm, authentic Indian middle-class family sitting happily in their living room with subtle glowing ₹ symbol.\n\n"
        "--- TASK 2: SOCIAL MEDIA POST ---\n"
        "Headline: Aapka Sapna, Hamara Saath! ✨\n"
        "Caption: Low EMI loans starting now.\n"
        "👉 Apply Now: https://loansolutions.everythingrental.in/application\n"
        "#LoanSolutions #HomeLoanIndia #FinancialFreedom"
    )

    print("=" * 60)
    print("PROMPT PASTE VERIFIER AGENT CLI")
    print("=" * 60)

    for i, h in enumerate(driver.window_handles):
        driver.switch_to.window(h)
        plat = agent.detect_platform(driver)
        if plat in ["gemini", "chatgpt"]:
            print(f"\n[Tab {i}] Detected Platform: {plat.upper()} ({driver.title})")
            if args.verify_only:
                res = agent.verify_prompt(driver, sample_prompt, platform=plat)
                print(f"Verification Result: {res.status} (Valid: {res.is_valid}, Ratio: {res.similarity_ratio*100:.1f}%)")
                print(f"Details: {res.details}")
            else:
                res = agent.ensure_properly_pasted(driver, sample_prompt, platform=plat)
                print(f"Result: {res.status} | Method: {res.method_used}")
                print(f"Similarity: {res.similarity_ratio*100:.1f}% | Send Ready: {res.send_button_ready}")
                print(f"Details: {res.details}")
                # Clean up after test
                time.sleep(1)
                agent.clear_editor(driver, platform=plat)
                print("Editor cleared after test.")
