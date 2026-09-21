import re


def check_image_text(text: str) -> bool:
    """
    Basic security check for OCR-extracted text.

    Returns False if the OCR text contains
    obvious prompt-injection patterns.
    """

    suspicious_patterns = [
        r"ignore previous instructions",
        r"ignore all previous instructions",
        r"forget previous instructions",
        r"system prompt",
        r"reveal your instructions",
        r"developer message",
        r"jailbreak",
    ]

    text_lower = text.lower()

    for pattern in suspicious_patterns:
        if re.search(pattern, text_lower):
            return False

    return True