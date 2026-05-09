# =============================================================================
# modules/breach.py — HaveIBeenPwned Breach Intelligence
# =============================================================================

import requests
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config


def check_breaches(email: str) -> dict:
    """
    Query the HaveIBeenPwned v3 API for known data breaches.

    Parameters
    ----------
    email : str
        The email address to check.

    Returns
    -------
    dict with keys:
        breached      (bool)  — True if the email appears in any breach
        breach_count  (int)   — number of breaches found
        breaches      (list)  — breach names (str list)
        error         (str)   — non-empty string if an error occurred
    """
    if not config.HIBP_API_KEY or config.HIBP_API_KEY == "YOUR_HIBP_API_KEY":
        return _error_result("HIBP API key not configured. Set HIBP_API_KEY in config.py.")

    headers = {
        "hibp-api-key": config.HIBP_API_KEY,
        "User-Agent":   config.HIBP_USER_AGENT,
    }
    url = f"{config.HIBP_API_URL}/{requests.utils.quote(email)}"
    params = {"truncateResponse": "false"}

    try:
        response = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=config.REQUEST_TIMEOUT,
        )

        # 404 → clean (no breach found)
        if response.status_code == 404:
            return {
                "breached":     False,
                "breach_count": 0,
                "breaches":     [],
                "error":        "",
            }

        # 401 → bad API key
        if response.status_code == 401:
            return _error_result("HIBP API key is invalid or unauthorised.")

        # 429 → rate limited
        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After", "unknown")
            return _error_result(
                f"HIBP rate limit exceeded. Retry after {retry_after} seconds."
            )

        response.raise_for_status()

        breaches = response.json()
        breach_names = [b.get("Name", "Unknown") for b in breaches]

        return {
            "breached":     True,
            "breach_count": len(breach_names),
            "breaches":     breach_names,
            "error":        "",
        }

    except requests.exceptions.ConnectionError:
        return _error_result("Network error: could not reach HIBP API.")
    except requests.exceptions.Timeout:
        return _error_result("Request timed out while contacting HIBP API.")
    except requests.exceptions.RequestException as exc:
        return _error_result(f"Unexpected HTTP error: {exc}")
    except ValueError:
        return _error_result("Failed to parse HIBP API response.")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _error_result(message: str) -> dict:
    return {
        "breached":     False,
        "breach_count": 0,
        "breaches":     [],
        "error":        message,
    }
