# =============================================================================
# modules/validator.py — Email Validation & Username Analysis
# =============================================================================

import re


# RFC-5321-inspired pattern — covers the vast majority of real-world emails.
_EMAIL_REGEX = re.compile(
    r"^(?P<username>[a-zA-Z0-9._%+\-]+)"
    r"@"
    r"(?P<domain>[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})$"
)


def validate_email(email: str) -> dict:
    """
    Validate an email address and extract structural components.

    Returns
    -------
    dict with keys:
        valid         (bool)   — whether the format is valid
        email         (str)    — normalised lowercase email
        username      (str)    — local-part of the address
        domain        (str)    — domain part of the address
        variations    (list)   — plausible username aliases
        error         (str)    — human-readable message if invalid, else ""
    """
    email = email.strip().lower()

    match = _EMAIL_REGEX.match(email)
    if not match:
        return {
            "valid": False,
            "email": email,
            "username": "",
            "domain": "",
            "variations": [],
            "error": "Invalid email format.",
        }

    username = match.group("username")
    domain   = match.group("domain")

    return {
        "valid": True,
        "email": email,
        "username": username,
        "domain": domain,
        "variations": _generate_variations(username),
        "error": "",
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _generate_variations(username: str) -> list:
    """
    Generate plausible username aliases from a base username.

    Strategies
    ----------
    1. dot_removed   — strip all dots  (john.doe → johndoe)
    2. underscore    — replace dots/hyphens with underscores (john.doe → john_doe)
    3. initial_based — first character + remainder after separator
                       (john.doe → jdoe, john_doe → jdoe)
    4. no_numbers    — strip trailing digits  (john42 → john)
    5. original      — always included for completeness
    """
    variations: list[str] = []
    seen: set[str] = set()

    def add(v: str):
        v = v.strip("._-")   # tidy leading/trailing separators
        if v and v not in seen and v != username:
            seen.add(v)
            variations.append(v)

    # 1. Original (always first)
    variations.append(username)
    seen.add(username)

    # 2. Dot removed
    add(username.replace(".", ""))

    # 3. Dots/hyphens → underscores
    add(re.sub(r"[.\-]", "_", username))

    # 4. Initial-based (first char + everything after the first separator)
    sep_match = re.search(r"[._\-](.+)", username)
    if sep_match:
        initial_variant = username[0] + sep_match.group(1).replace(".", "").replace("-", "")
        add(initial_variant)

    # 5. Strip trailing digits
    no_digits = re.sub(r"\d+$", "", username)
    add(no_digits)

    # 6. Underscore → dot
    add(username.replace("_", "."))

    return variations
