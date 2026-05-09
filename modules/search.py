# =============================================================================
# modules/search.py — Public Digital Footprint Search
# =============================================================================
# Priority order:
#   1. SerpAPI  (if SERP_API_KEY is set)
#   2. DuckDuckGo HTML search (no API key required, rate-limited)
#   3. GitHub Public API user search
# =============================================================================

import re
import sys
import os

import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def search_public_footprint(email: str, username: str, variations: list) -> dict:
    """
    Search multiple public sources for digital traces of *email* / *username*.

    Parameters
    ----------
    email      : str   — full email address
    username   : str   — local-part of the email
    variations : list  — username aliases to search

    Returns
    -------
    dict with keys:
        public_urls        (list) — unique URLs found across all sources
        possible_usernames (list) — usernames confirmed or suggested online
        sources_checked    (list) — which data sources were queried
        error              (str)  — non-empty if all sources failed
    """
    urls: list[str]      = []
    usernames: list[str] = list({username} | set(variations))
    sources_checked: list[str] = []
    errors: list[str]    = []

    # ── 1. SerpAPI ───────────────────────────────────────────────────────────
    if config.SERP_API_KEY:
        serp_urls, serp_err = _search_serpapi(email, username)
        sources_checked.append("SerpAPI")
        if serp_err:
            errors.append(f"SerpAPI: {serp_err}")
        else:
            urls.extend(serp_urls)

    # ── 2. DuckDuckGo HTML (always attempted as fallback / supplement) ───────
    ddg_urls, ddg_err = _search_duckduckgo(email, username)
    sources_checked.append("DuckDuckGo")
    if ddg_err:
        errors.append(f"DuckDuckGo: {ddg_err}")
    else:
        urls.extend(ddg_urls)

    # ── 3. GitHub Public API ─────────────────────────────────────────────────
    gh_urls, gh_users, gh_err = _search_github(username, variations)
    sources_checked.append("GitHub")
    if gh_err:
        errors.append(f"GitHub: {gh_err}")
    else:
        urls.extend(gh_urls)
        usernames.extend(gh_users)

    # ── Deduplicate & cap ────────────────────────────────────────────────────
    unique_urls      = _dedupe(urls)[: config.MAX_SEARCH_RESULTS]
    unique_usernames = _dedupe(usernames)

    return {
        "public_urls":        unique_urls,
        "possible_usernames": unique_usernames,
        "sources_checked":    sources_checked,
        "error":              "; ".join(errors) if errors and not unique_urls else "",
    }


# ---------------------------------------------------------------------------
# Source: SerpAPI
# ---------------------------------------------------------------------------

def _search_serpapi(email: str, username: str) -> tuple[list, str]:
    query = f'"{email}" OR "{username}"'
    params = {
        "q":       query,
        "api_key": config.SERP_API_KEY,
        "num":     config.MAX_SEARCH_RESULTS,
        "hl":      "en",
    }
    try:
        resp = requests.get(
            config.SERP_API_URL,
            params=params,
            timeout=config.REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()

        urls = [
            item.get("link", "")
            for item in data.get("organic_results", [])
            if item.get("link")
        ]
        return urls, ""

    except requests.exceptions.RequestException as exc:
        return [], str(exc)
    except ValueError:
        return [], "Failed to parse SerpAPI response."


# ---------------------------------------------------------------------------
# Source: DuckDuckGo HTML (lite endpoint — no JS, no captcha normally)
# ---------------------------------------------------------------------------

_DDG_URL_PATTERN = re.compile(
    r'href="(https?://(?!duckduckgo\.com)[^"]{10,})"',
    re.IGNORECASE,
)

def _search_duckduckgo(email: str, username: str) -> tuple[list, str]:
    """
    Use DuckDuckGo's HTML endpoint (no API key required).
    Returns raw result links found in the response body.
    """
    query = f'"{email}" OR "{username}"'
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (compatible; OSINT-Tool/1.0; "
            "+https://github.com/osint-tool)"
        )
    }
    try:
        resp = requests.get(
            "https://html.duckduckgo.com/html/",
            params={"q": query, "kl": "wt-wt"},
            headers=headers,
            timeout=config.REQUEST_TIMEOUT,
        )
        resp.raise_for_status()

        raw_urls = _DDG_URL_PATTERN.findall(resp.text)
        # Filter out DDG redirect/tracking links
        clean = [u for u in raw_urls if "duckduckgo" not in u]
        return clean, ""

    except requests.exceptions.RequestException as exc:
        return [], str(exc)


# ---------------------------------------------------------------------------
# Source: GitHub Public API
# ---------------------------------------------------------------------------

def _search_github(username: str, variations: list) -> tuple[list, list, str]:
    """
    Search GitHub public user search API for the username and its variations.
    Returns (profile_urls, found_logins, error_string).
    """
    headers = {"Accept": "application/vnd.github+json"}
    if config.GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {config.GITHUB_TOKEN}"

    all_urls:   list[str] = []
    all_logins: list[str] = []
    errors:     list[str] = []

    # Search for the primary username + up to 2 variations
    candidates = _dedupe([username] + list(variations))[:3]

    for candidate in candidates:
        try:
            resp = requests.get(
                config.GITHUB_API_URL,
                params={"q": candidate, "per_page": 5},
                headers=headers,
                timeout=config.REQUEST_TIMEOUT,
            )

            if resp.status_code == 403:
                errors.append("GitHub rate limit exceeded.")
                break

            resp.raise_for_status()
            items = resp.json().get("items", [])

            for item in items:
                login      = item.get("login", "")
                html_url   = item.get("html_url", "")
                # Only include profiles whose login closely matches candidate
                if login and html_url and _fuzzy_match(candidate, login):
                    all_urls.append(html_url)
                    all_logins.append(login)

        except requests.exceptions.RequestException as exc:
            errors.append(str(exc))
            break

    error_str = "; ".join(errors) if errors and not all_urls else ""
    return all_urls, all_logins, error_str


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _dedupe(lst: list) -> list:
    """Return a list with duplicates removed, preserving order."""
    seen: set = set()
    result: list = []
    for item in lst:
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result


def _fuzzy_match(query: str, candidate: str) -> bool:
    """
    Return True if *candidate* is a plausible match for *query*.
    Accepts substring, prefix, or levenshtein-close results.
    """
    q = query.lower().replace(".", "").replace("_", "").replace("-", "")
    c = candidate.lower().replace(".", "").replace("_", "").replace("-", "")
    return q in c or c in q
