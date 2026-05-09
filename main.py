#!/usr/bin/env python3
# =============================================================================
# main.py — OSINT Email Intelligence Tool
# =============================================================================
# Usage:
#   python main.py
#   python main.py --email user@example.com
#   python main.py --email user@example.com --output report.json
# =============================================================================

import argparse
import json
import sys
import os
import time
from datetime import datetime, timezone

# Ensure the project root is on the path so modules resolve correctly.
sys.path.insert(0, os.path.dirname(__file__))

from modules.validator   import validate_email
from modules.breach      import check_breaches
from modules.domain      import get_domain_info
from modules.search      import search_public_footprint
from modules.correlation import correlate


# ---------------------------------------------------------------------------
# ANSI colour helpers (gracefully disabled on Windows / non-TTY)
# ---------------------------------------------------------------------------

_USE_COLOUR = sys.stdout.isatty() and os.name != "nt"

def _c(text: str, code: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _USE_COLOUR else text

def green(t):  return _c(t, "32")
def yellow(t): return _c(t, "33")
def red(t):    return _c(t, "31")
def cyan(t):   return _c(t, "36")
def bold(t):   return _c(t, "1")
def dim(t):    return _c(t, "2")



# ---------------------------------------------------------------------------
# Banner
# ---------------------------------------------------------------------------

BANNER = r"""
 ██████╗ ███████╗██╗███╗   ██╗████████╗   █████╗ ██╗      █████╗  █████╗
██╔═══██╗██╔════╝██║████╗  ██║╚══██╔══╝  ██╔══██╗██║     ██╔═ ██╗██╔══██╗
██║   ██║███████╗██║██╔██╗ ██║   ██║     ███████║██║     ██║  ╚═╝███████║  
██║   ██║╚════██║██║██║╚██╗██║   ██║     ██╔══██║██║     ██║  ██╗██╔══██║ 
╚██████╔╝███████║██║██║ ╚████║   ██║     ██║  ██║███████╗╚█████╔╝██║  ██║
 ╚═════╝ ╚══════╝╚═╝╚═╝  ╚═══╝   ╚═╝     ╚═╝  ╚═╝╚══════╝ ╚════╝ ╚═╝  ╚═╝ 
  Email Intelligence Tool  v1.0
  Legal OSINT — Public Data Only
"""



# ---------------------------------------------------------------------------
# Step printer
# ---------------------------------------------------------------------------

def _step(label: str, status: str = ""):
    pad = 40 - len(label)
    line = f"  {bold(label)}" + " " * pad
    if status:
        line += status
    print(line)


def _divider():
    print(dim("  " + "─" * 60))


# ---------------------------------------------------------------------------
# Core pipeline
# ---------------------------------------------------------------------------

def run_analysis(email: str, verbose: bool = True) -> dict:
    """
    Execute the full OSINT pipeline and return a structured report dict.
    """
    if verbose:
        print(cyan(BANNER))
        print(dim(f"  Started : {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}"))
        print(dim(f"  Target  : {email}"))
        print()
        _divider()

    # ── Step 1: Validate ─────────────────────────────────────────────────────
    if verbose:
        print(f"\n{bold('[ 1/5 ] Validating email …')}")
    validation = validate_email(email)

    if not validation["valid"]:
        if verbose:
            print(red(f"  ✗ {validation['error']}"))
        return {"error": validation["error"], "email": email}

    username   = validation["username"]
    domain     = validation["domain"]
    variations = validation["variations"]

    if verbose:
        _step("Format", green("✓ valid"))
        _step("Username", cyan(username))
        _step("Domain", cyan(domain))
        _step("Variations", ", ".join(variations))

    # ── Step 2: Breach check ─────────────────────────────────────────────────
    if verbose:
        print(f"\n{bold('[ 2/5 ] Checking breach databases …')}")
    breach_data = check_breaches(email)

    if verbose:
        if breach_data["error"]:
            _step("Status", yellow(f"⚠ {breach_data['error']}"))
        elif breach_data["breached"]:
            _step("Breached", red(f"✗ YES — {breach_data['breach_count']} breach(es)"))
            for b in breach_data["breaches"]:
                print(f"    {dim('•')} {b}")
        else:
            _step("Breached", green("✓ Not found in known breaches"))

    time.sleep(0.3)   # be polite to APIs

    # ── Step 3: Domain intelligence ──────────────────────────────────────────
    if verbose:
        print(f"\n{bold('[ 3/5 ] Gathering domain intelligence …')}")
    domain_info = get_domain_info(domain)

    if verbose:
        if domain_info["error"]:
            _step("WHOIS", yellow(f"⚠ {domain_info['error']}"))
        else:
            _step("Registrar",      domain_info["registrar"]       or dim("n/a"))
            _step("Created",        domain_info["creation_date"]   or dim("n/a"))
            _step("Expires",        domain_info["expiration_date"] or dim("n/a"))
            _step("IP address",     domain_info["ip_address"]      or dim("n/a"))
            _step("Organisation",   domain_info["org"]             or dim("n/a"))
            _step("Country",        domain_info["country"]         or dim("n/a"))

    # ── Step 4: Public footprint search ──────────────────────────────────────
    if verbose:
        print(f"\n{bold('[ 4/5 ] Searching public footprint …')}")
    footprint = search_public_footprint(email, username, variations)

    if verbose:
        sources = ", ".join(footprint["sources_checked"])
        _step("Sources queried", sources)
        if footprint["error"]:
            _step("Warnings", yellow(footprint["error"]))
        _step("URLs found", str(len(footprint["public_urls"])))
        for url in footprint["public_urls"]:
            print(f"    {dim('•')} {url}")

    time.sleep(0.3)

    # ── Step 5: Correlation ───────────────────────────────────────────────────
    if verbose:
        print(f"\n{bold('[ 5/5 ] Computing identity correlation …')}")
    correlation = correlate(
        username,
        variations,
        footprint["public_urls"],
        breach_data,
        domain_info,
    )

    if verbose:
        conf = correlation["confidence"]
        colour = {"LOW": yellow, "MEDIUM": yellow, "HIGH": red}.get(conf, green)
        _step("Confidence", colour(conf))
        _step("Score",      str(correlation["score"]))
        _step("Matched URLs", str(len(correlation["matched_urls"])))
        for url in correlation["matched_urls"]:
            print(f"    {dim('•')} {url}")
        if verbose:
            print()
            print(dim("  Score breakdown:"))
            for k, v in correlation["factors"].items():
                print(dim(f"    {k}: {v}"))

    # ── Assemble final report ────────────────────────────────────────────────
    report = {
        "meta": {
            "tool":      "OSINT Email Intelligence Tool v1.0",
            "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
        "email":      validation["email"],
        "validation": {
            "valid":      validation["valid"],
            "username":   username,
            "domain":     domain,
            "variations": variations,
        },
        "breach_data": {
            "breached":     breach_data["breached"],
            "breach_count": breach_data["breach_count"],
            "breaches":     breach_data["breaches"],
            "error":        breach_data["error"],
        },
        "domain_info": {
            "registrar":       domain_info["registrar"],
            "creation_date":   domain_info["creation_date"],
            "expiration_date": domain_info["expiration_date"],
            "updated_date":    domain_info["updated_date"],
            "ip_address":      domain_info["ip_address"],
            "name_servers":    domain_info["name_servers"],
            "org":             domain_info["org"],
            "country":         domain_info["country"],
            "error":           domain_info["error"],
        },
        "digital_footprint": {
            "public_urls":        footprint["public_urls"],
            "possible_usernames": footprint["possible_usernames"],
            "sources_checked":    footprint["sources_checked"],
        },
        "correlation": {
            "confidence":   correlation["confidence"],
            "score":        correlation["score"],
            "matches":      correlation["matched_urls"],
            "factors":      correlation["factors"],
        },
    }

    return report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="osint-email",
        description="OSINT Email Intelligence Tool — legal public-data profiling",
    )
    parser.add_argument(
        "--email", "-e",
        help="Email address to analyse (prompted if omitted)",
    )
    parser.add_argument(
        "--output", "-o",
        help="Write JSON report to this file path (optional)",
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress progress output; print only final JSON",
    )
    return parser.parse_args()


def main():
    args = _parse_args()

    email = args.email
    if not email:
        try:
            email = input(bold("  Enter email address to analyse: ")).strip()
        except (KeyboardInterrupt, EOFError):
            print("\n  Aborted.")
            sys.exit(0)

    if not email:
        print(red("  No email provided. Exiting."))
        sys.exit(1)

    report = run_analysis(email, verbose=not args.quiet)

    # ── Print final JSON ─────────────────────────────────────────────────────
    json_output = json.dumps(report, indent=2, ensure_ascii=False)

    if args.quiet:
        print(json_output)
    else:
        _divider()
        print(f"\n{bold('  ══ FINAL REPORT (JSON) ══')}\n")
        print(json_output)

    # ── Optionally write to file ─────────────────────────────────────────────
    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as fh:
                fh.write(json_output)
            print(f"\n{green('  ✓')} Report saved to {bold(args.output)}")
        except OSError as exc:
            print(red(f"\n  ✗ Could not write file: {exc}"), file=sys.stderr)


if __name__ == "__main__":
    main()
