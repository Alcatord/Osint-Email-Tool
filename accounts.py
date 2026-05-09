# =============================================================================
# modules/accounts.py — Linked Accounts & Public Profile Discovery
# =============================================================================
# Sources used (all public, no auth bypass):
#   1. Gravatar       — avatar + profile linked to email hash
#   2. GitHub API     — search users by email (public only)
#   3. Keybase API    — public key/identity lookup
#   4. Hunter.io API  — professional profile enrichment (optional key)
#   5. Targeted search queries per platform (LinkedIn, Reddit, Medium, etc.)
# =============================================================================

import hashlib
import re
import sys
import os

import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config

# ---------------------------------------------------------------------------
# Platform search templates
# The {username} and {email} placeholders are filled at runtime.
# These generate DuckDuckGo/SerpAPI search queries, NOT direct scrapes.
# ---------------------------------------------------------------------------
PLATFORM_QUERIES = [
    ('LinkedIn',   'site:linkedin.com/in "{username}"'),
    ('Twitter/X',  'site:twitter.com "{username}"'),
    ('Reddit',     'site:reddit.com/user "{username}"'),
    ('Medium',     'site:medium.com "@{username}"'),
    ('Dev.to',     'site:dev.to "{username}"'),
    ('HackerNews', 'site:news.ycombinator.com/user?id={username}'),
    ('Pinterest',  'site:pinterest.com "{username}"'),
    ('YouTube',    'site:youtube.com "@{username}"'),
    ('Behance',    'site:behance.net "{username}"'),
    ('Dribbble',   'site:dribbble.com "{username}"'),
    ('Stackoverflow', 'site:stackoverflow.com/users "{username}"'),
    ('Gitlab',     'site:gitlab.com "{username}"'),
    ('NPM',        'site:npmjs.com/~{username}'),
    ('Pastebin',   'site:pastebin.com/u/{username}'),
]


def discover_accounts(email: str, username: str, variations: list) -> dict:
    """
    Discover publicly linked accounts for a given email/username.

    Returns
    -------
    dict with keys:
        gravatar        (dict)  — Gravatar profile info
        github_profiles (list)  — GitHub user profiles found
        keybase         (dict)  — Keybase identity info
        hunter          (dict)  — Hunter.io enrichment (if key set)
        platform_hits   (list)  — list of {platform, query, url} dicts
        all_found_urls  (list)  — flat deduplicated list of all URLs
        error           (str)
    """
    results = {
        "gravatar":        {},
        "github_profiles": [],
        "keybase":         {},
        "hunter":          {},
        "platform_hits":   [],
        "all_found_urls":  [],
        "error":           "",
    }
    errors = []

    # ── 1. Gravatar ───────────────────────────────────────────────────────────
    gravatar_result, g_err = _check_gravatar(email)
    if g_err:
        errors.append(f"Gravatar: {g_err}")
    else:
        results["gravatar"] = gravatar_result
        if gravatar_result.get("profile_url"):
            results["all_found_urls"].append(gravatar_result["profile_url"])

    # ── 2. GitHub (by email) ──────────────────────────────────────────────────
    gh_profiles, gh_err = _github_by_email(email, username, variations)
    if gh_err:
        errors.append(f"GitHub: {gh_err}")
    results["github_profiles"] = gh_profiles
    results["all_found_urls"].extend([p["url"] for p in gh_profiles if p.get("url")])

    # ── 3. Keybase ────────────────────────────────────────────────────────────
    kb_result, kb_err = _check_keybase(username, variations)
    if kb_err:
        errors.append(f"Keybase: {kb_err}")
    else:
        results["keybase"] = kb_result
        if kb_result.get("profile_url"):
            results["all_found_urls"].append(kb_result["profile_url"])

    # ── 4. Hunter.io (optional) ───────────────────────────────────────────────
    if hasattr(config, "HUNTER_API_KEY") and config.HUNTER_API_KEY:
        hunter_result, h_err = _check_hunter(email)
        if h_err:
            errors.append(f"Hunter.io: {h_err}")
        else:
            results["hunter"] = hunter_result

    # ── 5. Platform search queries ────────────────────────────────────────────
    platform_hits = _build_platform_queries(username, variations)
    results["platform_hits"] = platform_hits
    # Run actual search for each platform via DuckDuckGo
    for hit in platform_hits:
        urls = _ddg_search(hit["query"])
        hit["found_urls"] = urls
        results["all_found_urls"].extend(urls)

    # Deduplicate
    seen: set = set()
    deduped = []
    for u in results["all_found_urls"]:
        if u and u not in seen:
            seen.add(u)
            deduped.append(u)
    results["all_found_urls"] = deduped

    if errors:
        results["error"] = " | ".join(errors)

    return results


# ---------------------------------------------------------------------------
# Gravatar
# ---------------------------------------------------------------------------

def _check_gravatar(email: str) -> tuple[dict, str]:
    """
    Query Gravatar's public JSON profile endpoint.
    Uses an MD5 hash of the email (Gravatar's public identifier).
    """
    email_hash = hashlib.md5(email.strip().lower().encode()).hexdigest()
    avatar_url  = f"https://www.gravatar.com/avatar/{email_hash}?d=404&s=200"
    profile_url = f"https://www.gravatar.com/{email_hash}.json"

    result = {
        "email_hash":   email_hash,
        "avatar_url":   "",
        "profile_url":  "",
        "display_name": "",
        "about":        "",
        "accounts":     [],    # linked social accounts declared in Gravatar
        "found":        False,
    }

    try:
        # Check avatar exists (404 = no Gravatar)
        avatar_resp = requests.get(
            avatar_url, timeout=config.REQUEST_TIMEOUT, allow_redirects=True
        )
        if avatar_resp.status_code == 404:
            return result, ""

        result["avatar_url"] = f"https://www.gravatar.com/avatar/{email_hash}?s=200"
        result["found"] = True

        # Fetch JSON profile
        profile_resp = requests.get(
            profile_url, timeout=config.REQUEST_TIMEOUT
        )
        if profile_resp.status_code == 200:
            data    = profile_resp.json()
            entry   = data.get("entry", [{}])[0]
            result["profile_url"]  = f"https://gravatar.com/{email_hash}"
            result["display_name"] = entry.get("displayName", "")
            result["about"]        = entry.get("aboutMe", "")
            # Linked accounts (Twitter, GitHub, etc.) declared by user
            result["accounts"] = [
                {
                    "name":     acc.get("name", ""),
                    "shortname": acc.get("shortname", ""),
                    "url":      acc.get("url", ""),
                }
                for acc in entry.get("accounts", [])
            ]

        return result, ""

    except requests.exceptions.RequestException as exc:
        return result, str(exc)
    except (ValueError, KeyError):
        return result, "Failed to parse Gravatar profile."


# ---------------------------------------------------------------------------
# GitHub — search by email
# ---------------------------------------------------------------------------

def _github_by_email(
    email: str, username: str, variations: list
) -> tuple[list, str]:
    """
    GitHub's search API lets you search users by email (public index only).
    Falls back to username search if email search yields nothing.
    """
    headers = {"Accept": "application/vnd.github+json"}
    if hasattr(config, "GITHUB_TOKEN") and config.GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {config.GITHUB_TOKEN}"

    profiles = []
    errors   = []

    # Strategy 1: search by full email
    queries = [f"{email} in:email"] + [
        f"{v} in:login" for v in ([username] + list(variations))[:3]
    ]

    for q in queries:
        try:
            resp = requests.get(
                config.GITHUB_API_URL,
                params={"q": q, "per_page": 5},
                headers=headers,
                timeout=config.REQUEST_TIMEOUT,
            )
            if resp.status_code == 403:
                errors.append("Rate limit exceeded")
                break
            resp.raise_for_status()
            items = resp.json().get("items", [])
            for item in items:
                profile = {
                    "login":      item.get("login", ""),
                    "url":        item.get("html_url", ""),
                    "avatar":     item.get("avatar_url", ""),
                    "type":       item.get("type", ""),
                    "site_admin": item.get("site_admin", False),
                }
                # Avoid duplicates
                if profile["url"] and profile not in profiles:
                    profiles.append(profile)
        except requests.exceptions.RequestException as exc:
            errors.append(str(exc))
            break

    return profiles, " | ".join(errors) if errors and not profiles else ""


# ---------------------------------------------------------------------------
# Keybase
# ---------------------------------------------------------------------------

def _check_keybase(username: str, variations: list) -> tuple[dict, str]:
    """
    Query Keybase's public lookup API.
    Keybase links GitHub, Twitter, Reddit, HN, etc. identities publicly.
    """
    result = {
        "found":        False,
        "username":     "",
        "profile_url":  "",
        "proofs":       [],   # linked identities
    }

    candidates = list(dict.fromkeys([username] + list(variations)))[:3]

    for candidate in candidates:
        try:
            resp = requests.get(
                f"https://keybase.io/_/api/1.0/user/lookup.json",
                params={"username": candidate},
                timeout=config.REQUEST_TIMEOUT,
            )
            if resp.status_code != 200:
                continue
            data   = resp.json()
            status = data.get("status", {}).get("code", -1)
            if status != 0:
                continue

            them = data.get("them")
            if not them:
                continue

            result["found"]       = True
            result["username"]    = them.get("basics", {}).get("username", candidate)
            result["profile_url"] = f"https://keybase.io/{result['username']}"

            # Proof summary (linked social accounts)
            proofs = them.get("proofs_summary", {}).get("all", [])
            result["proofs"] = [
                {
                    "proof_type": p.get("proof_type", ""),
                    "nametag":    p.get("nametag", ""),
                    "human_url":  p.get("human_url", ""),
                    "state":      p.get("state", 0),
                }
                for p in proofs
            ]
            return result, ""

        except requests.exceptions.RequestException as exc:
            return result, str(exc)
        except (ValueError, KeyError):
            continue

    return result, ""


# ---------------------------------------------------------------------------
# Hunter.io (optional)
# ---------------------------------------------------------------------------

def _check_hunter(email: str) -> tuple[dict, str]:
    """
    Query Hunter.io email finder API for professional enrichment.
    Returns company/title data linked to the email.
    """
    try:
        resp = requests.get(
            "https://api.hunter.io/v2/email-verifier",
            params={"email": email, "api_key": config.HUNTER_API_KEY},
            timeout=config.REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json().get("data", {})
        return {
            "status":       data.get("status", ""),
            "result":       data.get("result", ""),
            "score":        data.get("score", 0),
            "regexp":       data.get("regexp", False),
            "gibberish":    data.get("gibberish", False),
            "disposable":   data.get("disposable", False),
            "webmail":      data.get("webmail", False),
            "mx_records":   data.get("mx_records", False),
            "smtp_server":  data.get("smtp_server", False),
            "smtp_check":   data.get("smtp_check", False),
        }, ""
    except requests.exceptions.RequestException as exc:
        return {}, str(exc)
    except ValueError:
        return {}, "Failed to parse Hunter.io response."


# ---------------------------------------------------------------------------
# Platform targeted search
# ---------------------------------------------------------------------------

def _build_platform_queries(username: str, variations: list) -> list:
    """Build targeted site: search queries for each social platform."""
    # Use the two most likely usernames to avoid too many requests
    primary    = username
    secondary  = variations[0] if variations else username

    hits = []
    for platform, template in PLATFORM_QUERIES:
        for u in _dedupe([primary, secondary]):
            query = template.replace("{username}", u).replace("{email}", u)
            hits.append({
                "platform":   platform,
                "username":   u,
                "query":      query,
                "found_urls": [],
            })
    return hits


_DDG_URL_RE = re.compile(
    r'href="(https?://(?!duckduckgo\.com)[^"]{10,})"',
    re.IGNORECASE,
)

def _ddg_search(query: str) -> list:
    """Run a single DuckDuckGo HTML search and return found URLs."""
    try:
        resp = requests.get(
            "https://html.duckduckgo.com/html/",
            params={"q": query, "kl": "wt-wt"},
            headers={"User-Agent": "Mozilla/5.0 (compatible; OSINT-Tool/1.0)"},
            timeout=config.REQUEST_TIMEOUT,
        )
        if resp.status_code != 200:
            return []
        urls = _DDG_URL_RE.findall(resp.text)
        return [u for u in urls if "duckduckgo" not in u][:3]
    except requests.exceptions.RequestException:
        return []


def _dedupe(lst: list) -> list:
    seen: set = set()
    result = []
    for item in lst:
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result