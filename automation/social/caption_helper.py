"""
Caption Helper: Guarantees that the mandatory 'Apply Now' CTA link is placed
at the VERY START (Line 1) of social media post captions for Facebook, Instagram,
and Telegram preview cards.
"""
import re

LOAN_SOLUTIONS_APPLY_URL = "https://loansolutions.everythingrental.in/application"


def ensure_apply_now_at_start(
    caption: str,
    apply_url: str = LOAN_SOLUTIONS_APPLY_URL,
    is_loan: bool = True
) -> str:
    """
    Ensures that '👉 Apply Now: {apply_url}' is strictly placed at the VERY START (Line 1)
    of the caption. Strips any duplicate or trailing Apply Now links from the rest of the text.
    """
    if not caption:
        return f"👉 Apply Now: {apply_url}" if is_loan else ""

    if not is_loan:
        return caption.strip()

    target_url = apply_url or LOAN_SOLUTIONS_APPLY_URL
    cta_line = f"👉 Apply Now: {target_url}"

    # Strip existing variations of Apply Now anywhere in the text
    cleaned = caption
    patterns_to_remove = [
        r"👉\s*Apply\s+Now\s*:\s*https?://\S+",
        r"📝\s*Apply\s+Now\s*:\s*https?://\S+",
        r"Apply\s+Now\s*:\s*https?://\S+",
        re.escape(target_url),
    ]

    for pat in patterns_to_remove:
        cleaned = re.sub(pat, "", cleaned, flags=re.IGNORECASE)

    # Clean up excess whitespace and blank lines
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()

    # Prepend CTA line at the very top (Line 1)
    if cleaned:
        return f"{cta_line}\n\n{cleaned}"
    else:
        return cta_line
