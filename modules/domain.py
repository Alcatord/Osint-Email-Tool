# =============================================================================
# modules/domain.py — Domain WHOIS Intelligence
# =============================================================================

import sys
import os
import socket
import re

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config

try:
    import whois as python_whois   # python-whois library
    _WHOIS_AVAILABLE = True
except ImportError:
    _WHOIS_AVAILABLE = False


def get_domain_info(domain: str) -> dict:
    """
    Retrieve WHOIS data and resolve the IP address for a domain.

    Parameters
    ----------
    domain : str
        The domain extracted from the email address.

    Returns
    -------
    dict with keys:
        domain          (str)  — the queried domain
        registrar       (str)  — registrar name
        creation_date   (str)  — domain registration date (ISO-like)
        expiration_date (str)  — domain expiry date (ISO-like)
        updated_date    (str)  — last updated date (ISO-like)
        name_servers    (list) — list of name server hostnames
        ip_address      (str)  — resolved IPv4/IPv6 address (empty if unresolvable)
        country         (str)  — registrant country (if available)
        org             (str)  — registrant organisation (if available)
        error           (str)  — non-empty if an error occurred
    """
    result = _empty_result(domain)

    # ── IP resolution (always attempted, independent of whois) ───────────────
    result["ip_address"] = _resolve_ip(domain)

    # ── WHOIS lookup ─────────────────────────────────────────────────────────
    if not _WHOIS_AVAILABLE:
        result["error"] = (
            "python-whois is not installed. "
            "Run: pip install python-whois"
        )
        return result

    try:
        w = python_whois.whois(domain)

        result["registrar"]       = _safe_str(w.registrar)
        result["creation_date"]   = _safe_date(w.creation_date)
        result["expiration_date"] = _safe_date(w.expiration_date)
        result["updated_date"]    = _safe_date(w.updated_date)
        result["name_servers"]    = _safe_list(w.name_servers)
        result["country"]         = _safe_str(w.country)
        result["org"]             = _safe_str(w.org)

    except Exception as exc:
        result["error"] = f"WHOIS lookup failed: {exc}"

    return result


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _resolve_ip(domain: str) -> str:
    """Return the first resolved IP address for *domain*, or empty string."""
    try:
        return socket.gethostbyname(domain)
    except (socket.gaierror, OSError):
        return ""


def _safe_str(value) -> str:
    """Convert a whois field to a clean string."""
    if value is None:
        return ""
    if isinstance(value, list):
        value = value[0] if value else ""
    return str(value).strip()


def _safe_date(value) -> str:
    """Convert a whois date field (datetime or list) to an ISO string."""
    if value is None:
        return ""
    if isinstance(value, list):
        value = value[0] if value else None
    if value is None:
        return ""
    try:
        return value.isoformat()
    except AttributeError:
        return str(value).strip()


def _safe_list(value) -> list:
    """Convert a whois list field to a clean list of lowercase strings."""
    if not value:
        return []
    if isinstance(value, str):
        return [value.lower().strip()]
    return [str(v).lower().strip() for v in value if v]


def _empty_result(domain: str) -> dict:
    return {
        "domain":          domain,
        "registrar":       "",
        "creation_date":   "",
        "expiration_date": "",
        "updated_date":    "",
        "name_servers":    [],
        "ip_address":      "",
        "country":         "",
        "org":             "",
        "error":           "",
    }
