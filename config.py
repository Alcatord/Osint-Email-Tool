# =============================================================================
# config.py — OSINT Email Intelligence Tool Configuration
# =============================================================================
# Replace placeholder values with your actual API keys before running.
# Never commit real API keys to version control.
# =============================================================================

# --- HaveIBeenPwned ---
# Get your key at: https://haveibeenpwned.com/API/Key
HIBP_API_KEY = "YOUR_HIBP_API_KEY"
HIBP_API_URL = "https://haveibeenpwned.com/api/v3/breachedaccount"
HIBP_USER_AGENT = "OSINT-Email-Intelligence-Tool/1.0"

# --- SerpAPI (optional) ---
# Get your key at: https://serpapi.com/
# Leave empty ("") to fall back to DuckDuckGo HTML search.
SERP_API_KEY = ""
SERP_API_URL = "https://serpapi.com/search.json"

# --- GitHub Public API ---
# Optional: provide a personal access token for higher rate limits.
# Leave empty ("") to use unauthenticated (60 req/hour).
GITHUB_TOKEN = ""
GITHUB_API_URL = "https://api.github.com/search/users"

# --- General HTTP settings ---
REQUEST_TIMEOUT = 10          # seconds per request
MAX_SEARCH_RESULTS = 10       # max public URLs to return

# --- Correlation thresholds ---
CORRELATION_LOW_MAX    = 2
CORRELATION_MEDIUM_MAX = 5
# 6+ matches → HIGH
