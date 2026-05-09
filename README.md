 ██████╗ ███████╗██╗███╗   ██╗████████╗   █████╗ ██╗      █████╗  █████╗
██╔═══██╗██╔════╝██║████╗  ██║╚══██╔══╝  ██╔══██╗██║     ██╔═ ██╗██╔══██╗
██║   ██║███████╗██║██╔██╗ ██║   ██║     ███████║██║     ██║  ╚═╝███████║  
██║   ██║╚════██║██║██║╚██╗██║   ██║     ██╔══██║██║     ██║  ██╗██╔══██║ 
╚██████╔╝███████║██║██║ ╚████║   ██║     ██║  ██║███████╗╚█████╔╝██║  ██║
 ╚═════╝ ╚══════╝╚═╝╚═╝  ╚═══╝   ╚═╝     ╚═╝  ╚═╝╚══════╝ ╚════╝ ╚═╝  ╚═╝ 



# OSINT Email Intelligence Tool

A lightweight, modular Python tool that builds a **legal public digital footprint** of any email address using only open, publicly available data sources.

---

## Features

| Module | What it does |
|---|---|
| `validator.py` | RFC-5321 email validation, username extraction, alias generation |
| `breach.py` | HaveIBeenPwned v3 API — breach history |
| `domain.py` | WHOIS lookup + IP resolution |
| `search.py` | SerpAPI → DuckDuckGo → GitHub public search |
| `correlation.py` | Cross-reference artefacts, produce LOW / MEDIUM / HIGH confidence score |

---

## Project Structure

```
osint_email_tool/
├── main.py            ← CLI entry point / orchestrator
├── config.py          ← API keys & tuneable settings
├── requirements.txt
└── modules/
    ├── validator.py
    ├── breach.py
    ├── domain.py
    ├── search.py
    └── correlation.py
```

---

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure API keys in config.py
#    • HIBP_API_KEY  — https://haveibeenpwned.com/API/Key  (required for breach check)
#    • SERP_API_KEY  — https://serpapi.com/               (optional, DuckDuckGo used as fallback)
#    • GITHUB_TOKEN  — GitHub personal access token       (optional, increases rate limit)

# 3. Run
python main.py                              # interactive prompt
python main.py --email user@example.com     # direct input
python main.py --email user@example.com --output report.json   # save report
python main.py --email user@example.com --quiet                # JSON only
```

---

## Output Format

```json
{
  "meta": { "tool": "...", "generated": "..." },
  "email": "user@example.com",
  "validation": {
    "valid": true,
    "username": "user",
    "domain": "example.com",
    "variations": ["user", "u.ser", "usr"]
  },
  "breach_data": {
    "breached": true,
    "breach_count": 3,
    "breaches": ["Adobe", "LinkedIn", "Dropbox"],
    "error": ""
  },
  "domain_info": {
    "registrar": "...",
    "creation_date": "...",
    "expiration_date": "...",
    "ip_address": "93.184.216.34",
    "org": "...",
    "country": "US",
    "error": ""
  },
  "digital_footprint": {
    "public_urls": ["https://github.com/user", "..."],
    "possible_usernames": ["user", "u_ser"],
    "sources_checked": ["DuckDuckGo", "GitHub"]
  },
  "correlation": {
    "confidence": "MEDIUM",
    "score": 4,
    "matches": ["https://github.com/user"],
    "factors": {
      "url_matches": 1,
      "breach_bonus": 1,
      "domain_bonus": 1,
      "github_bonus": 1
    }
  }
}
```

---

## Confidence Score

| Band | Score | Meaning |
|---|---|---|
| LOW | 0–2 | Few or no corroborating signals |
| MEDIUM | 3–5 | Moderate public presence confirmed |
| HIGH | 6+ | Strong, multi-source corroboration |

Score is built from:
- **URL username matches** — public URLs containing a recognised username variant
- **Breach bonus** — +1 per 3 breaches (max +3)
- **Domain bonus** — +1 for domains registered before 2015
- **GitHub bonus** — +1 if a GitHub profile is found

---

## Legal & Ethical Rules

- Only public, legally accessible data is queried.
- No authentication bypass, no scraping private profiles.
- Respects API rate limits (deliberate delays between requests).
- No storage of third-party data — results are printed/saved locally only.
- Intended for **security research, account recovery, and threat intelligence** on data you are authorised to investigate.

---

## API Keys

| Key | Where to get it | Required? |
|---|---|---|
| `HIBP_API_KEY` | https://haveibeenpwned.com/API/Key | Yes (breach check) |
| `SERP_API_KEY` | https://serpapi.com | No (DuckDuckGo fallback) |
| `GITHUB_TOKEN` | GitHub → Settings → Developer settings | No (unauthenticated: 60 req/hr) |
