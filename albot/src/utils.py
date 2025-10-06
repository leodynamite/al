from __future__ import annotations

import re


def normalize_phone_to_ru(phone_raw: str) -> str:
    digits = re.sub(r"\D+", "", phone_raw or "")
    if not digits:
        return ""
    # remove leading 8 or 7 for RU and enforce +7
    if digits.startswith("8") and len(digits) == 11:
        digits = "7" + digits[1:]
    elif digits.startswith("7") and len(digits) == 11:
        pass
    elif digits.startswith("9") and len(digits) == 10:
        digits = "7" + digits
    return "+" + digits if not digits.startswith("+") else digits


def mask_phone(phone: str) -> str:
    d = re.sub(r"\D+", "", phone or "")
    if len(d) < 6:
        return phone or ""
    return f"+{d[:1]}***{d[-4:]}"


def mask_email(email: str) -> str:
    if not email or "@" not in email:
        return email or ""
    name, domain = email.split("@", 1)
    if len(name) <= 2:
        masked = name[0] + "*"
    else:
        masked = name[0] + "***" + name[-1]
    return f"{masked}@{domain}"




