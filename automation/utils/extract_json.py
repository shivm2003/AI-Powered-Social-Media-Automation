"""
JSON Extraction Utility for LLM and Video Script Responses.
Robustly parses JSON objects from LLM outputs containing Markdown blocks, extra text, or trailing quotes.
"""
import re
import json
import logging

logger = logging.getLogger("automation.utils.extract_json")


def extract_json_or_fallback(raw_text: str, default_data=None) -> dict:
    """
    Tries to extract a JSON object from raw response text.
    Handles ```json ... ``` fences, raw JSON, or substring { ... }.
    Returns default_data if parsing fails.
    """
    if not raw_text or not isinstance(raw_text, str):
        return default_data if default_data is not None else {}

    text = raw_text.strip()

    # 1. Direct JSON parse
    try:
        return json.loads(text)
    except Exception:
        pass

    # 2. Extract from markdown code blocks: ```json ... ``` or ``` ... ```
    fence_matches = re.findall(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
    for block in fence_matches:
        try:
            return json.loads(block.strip())
        except Exception:
            pass

    # 3. Find first '{' and last '}'
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        candidate = text[first_brace : last_brace + 1]
        try:
            return json.loads(candidate)
        except Exception:
            # Try cleaning common trailing comma issues
            cleaned = re.sub(r",\s*([\]}])", r"\1", candidate)
            try:
                return json.loads(cleaned)
            except Exception:
                pass

    return default_data if default_data is not None else {}
