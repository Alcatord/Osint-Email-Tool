# =============================================================================
# modules/correlation.py — Identity Correlation & Confidence Scoring
# =============================================================================

import re
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config


def correlate(
    username: str,
    variations: list,
    public_urls: list,
    breach_data: dict,
    domain_info: dict,
) -> dict:
    """
    Cross-reference discovered artefacts to produce a confidence score.

    Scoring factors
    ---------------
    1. URL match       — each URL that contains a known username variant (+1 each)
    2. Breach bonus    — email found in breaches (+1 per 3 breaches, max +3)
    3. Domain age      — established domain (creation year < 2015) → +1
    4. GitHub presence — any GitHub URL found → +1

    Confidence bands (after summing factors)
    ----------------------------------------
    0–2  → LOW
    3–5  → MEDIUM
    6+   → HIGH

    Parameters
    ----------
    username   : str   — primary username
    variations : list  — username aliases
    public_urls: list  — URLs returned by search module
    breach_data: dict  — output of breach.check_breaches()
    domain_info: dict  — output of domain.get_domain_info()

    Returns
    -------
    dict with keys:
        confidence   (str)  — LOW | MEDIUM | HIGH
        score        (int)  — raw numeric score
        matched_urls (list) — URLs that contain a recognisable username variant
        factors      (dict) — breakdown of score contributions
        summary      (str)  — human-readable explanation
    """
    all_variants = _build_variant_set(username, variations)
    matched_urls: list[str] = []
    score = 0

    # ── Factor 1: URL username matches ───────────────────────────────────────
    for url in public_urls:
        if _url_matches_variant(url, all_variants):
            matched_urls.append(url)

    url_score = len(matched_urls)
    score += url_score

    # ── Factor 2: Breach presence ─────────────────────────────────────────────
    breach_count  = breach_data.get("breach_count", 0)
    breach_bonus  = min(breach_count // 3, 3)   # +1 per 3 breaches, cap at 3
    score        += breach_bonus

    # ── Factor 3: Established domain ─────────────────────────────────────────
    domain_bonus  = _domain_age_bonus(domain_info.get("creation_date", ""))
    score        += domain_bonus

    # ── Factor 4: GitHub profile found ───────────────────────────────────────
    github_bonus = 1 if any("github.com" in u for u in public_urls) else 0
    score       += github_bonus

    # ── Confidence band ───────────────────────────────────────────────────────
    if score <= config.CORRELATION_LOW_MAX:
        confidence = "LOW"
    elif score <= config.CORRELATION_MEDIUM_MAX:
        confidence = "MEDIUM"
    else:
        confidence = "HIGH"

    factors = {
        "url_matches":    url_score,
        "breach_bonus":   breach_bonus,
        "domain_bonus":   domain_bonus,
        "github_bonus":   github_bonus,
    }

    return {
        "confidence":   confidence,
        "score":        score,
        "matched_urls": matched_urls,
        "factors":      factors,
        "summary":      _build_summary(confidence, score, factors),
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_variant_set(username: str, variations: list) -> set:
    """
    Build a set of normalised username tokens for substring matching.
    Includes both raw and separator-stripped forms.
    """
    tokens: set[str] = set()
    for v in [username] + list(variations):
        if v:
            tokens.add(v.lower())
            # separator-free form for robust URL matching
            stripped = re.sub(r"[._\-]", "", v.lower())
            if stripped:
                tokens.add(stripped)
    return tokens


def _url_matches_variant(url: str, variants: set) -> bool:
    """Return True if *url* contains any variant token as a path segment."""
    url_lower = url.lower()
    for variant in variants:
        # Require variant to appear as a distinct path element
        # e.g. /johndoe or /john.doe — not just a substring of a long token
        pattern = r"(?:/|=|\?|&|#|\.)?" + re.escape(variant) + r"(?:/|$|\?|&|#|\.)"
        if re.search(pattern, url_lower):
            return True
    return False


def _domain_age_bonus(creation_date: str) -> int:
    """
    Return +1 if the domain was created before 2015 (established domain),
    0 otherwise.
    """
    year_match = re.search(r"(\d{4})", creation_date)
    if year_match:
        year = int(year_match.group(1))
        if 1990 <= year < 2015:
            return 1
    return 0


def _build_summary(confidence: str, score: int, factors: dict) -> str:
    lines = [
        f"Confidence level: {confidence} (score: {score})",
        f"  • URL matches:    {factors['url_matches']}",
        f"  • Breach bonus:   {factors['breach_bonus']}",
        f"  • Domain bonus:   {factors['domain_bonus']}",
        f"  • GitHub bonus:   {factors['github_bonus']}",
    ]
    return "\n".join(lines)
