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
    is_loan: bool = True,
    contact_number: str = None
) -> str:
    """
    Ensures that '👉 Apply Now: {apply_url}' and optional '📞 Call / WhatsApp: {contact_number}'
    are strictly placed at the VERY START (Lines 1-2) of the caption.
    Strips any duplicate or trailing Apply Now and phone lines from the rest of the text.
    """
    phone = contact_number or ("8112570656" if is_loan else None)
    target_url = apply_url or LOAN_SOLUTIONS_APPLY_URL

    header_lines = []
    if is_loan:
        header_lines.append(f"👉 Apply Now: {target_url}")
    if phone:
        header_lines.append(f"📞 Call / WhatsApp: +91 {phone}")
    cta_block = "\n".join(header_lines)

    if not caption:
        return cta_block

    cleaned = caption
    patterns_to_remove = [
        r"👉\s*Apply\s+Now\s*:\s*https?://\S+",
        r"📝\s*Apply\s+Now\s*:\s*https?://\S+",
        r"Apply\s+Now\s*:\s*https?://\S+",
        re.escape(target_url),
    ]
    if phone:
        patterns_to_remove.extend([
            rf"📞\s*Call\s*/\s*WhatsApp\s*:\s*\+?91[\s-]*{phone}",
            rf"📞\s*Call\s*/\s*WhatsApp\s*:\s*{phone}",
            rf"Call\s*/\s*WhatsApp\s*:\s*{phone}",
            rf"Call\s*:\s*{phone}",
            rf"WhatsApp\s*:\s*{phone}",
            re.escape(phone),
        ])

    for pat in patterns_to_remove:
        cleaned = re.sub(pat, "", cleaned, flags=re.IGNORECASE)

    # Clean up excess whitespace and blank lines
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()

    if cleaned:
        return f"{cta_block}\n\n{cleaned}" if cta_block else cleaned
    else:
        return cta_block
