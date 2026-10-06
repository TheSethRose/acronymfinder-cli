#!/usr/bin/env python3
"""af - search AcronymFinder.com from the terminal.

Usage:
  ./af.py NASA
  ./af.py NASA --limit 10
  ./af.py NASA --json
  ./af.py FBI --json --limit 5 > out.json

Direct HTTP often hits a Cloudflare challenge. When that happens
the tool falls back to Chrome Bridge (host Chrome Beta) which
renders the page like a real browser.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import urllib.parse

import requests
from bs4 import BeautifulSoup

BASE = "https://www.acronymfinder.com"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"

BRIDGE = "/opt/chrome-bridge/bin/chrome-bridge.mjs"
BRIDGE_ENV = {
    "CHROME_BRIDGE_HOME": "/chrome-bridge-runtime",
    "AGENT": "kali-agent",
    "BROWSER": "chrome-beta",
}


def fetch_direct(acronym):
    url = f"{BASE}/{urllib.parse.quote(acronym.upper())}.html"
    r = requests.get(url, headers={"User-Agent": UA}, timeout=20)
    return url, r.text


def is_blocked(html):
    if not html:
        return True
    t = html.lower()
    return ("just a moment" in t and "cloudflare" in t) or ("enable javascript and cookies" in t)


def fetch_via_bridge(url):
    env = dict(os.environ)
    env.update(BRIDGE_ENV)
    # make a fresh tab, navigate, then dump rendered HTML
    subprocess.run([BRIDGE, "new-tab", "--url", "about:blank"],
                   capture_output=True, text=True, env=env, timeout=30)
    nav = subprocess.run([BRIDGE, "navigate", "--url", url, "--wait", "networkidle", "--timeout", "30000"],
                         capture_output=True, text=True, env=env, timeout=60)
    if nav.returncode != 0 and "tab" in nav.stderr.lower():
        # try without explicit tab selection (uses active tab)
        pass
    ev = subprocess.run([BRIDGE, "eval", "--expr", "document.documentElement.outerHTML"],
                        capture_output=True, text=True, env=env, timeout=30)
    if ev.returncode != 0:
        raise RuntimeError(f"chrome-bridge eval failed: {ev.stderr[:500]}")
    out = ev.stdout.strip()
    # bridge prints JSON or raw string; unwrap if needed
    try:
        data = json.loads(out)
        if isinstance(data, dict):
            for k in ("result", "value", "html", "data"):
                if k in data and isinstance(data[k], str) and len(data[k]) > 500:
                    return data[k]
            return out
        if isinstance(data, str):
            return data
    except Exception:
        pass
    return out


def parse(html, acronym):
    soup = BeautifulSoup(html, "lxml")
    text = soup.get_text(" ", strip=True)
    m = re.search(r"returned\s+(\d+)\s+meanings?|no exact matches", text, re.I)
    total = None
    if m:
        total = None if "no exact" in m.group(0).lower() else int(m.group(1))

    results = []
    # AcronymFinder renders Rank | Abbr | Meaning in a table
    for table in soup.find_all("table"):
        headers = [th.get_text(strip=True).lower() for th in table.find_all("th")]
        if not any("meaning" in h for h in headers):
            continue
        for row in table.find_all("tr"):
            cells = row.find_all(["td", "th"])
            if len(cells) < 2:
                continue
            # skip header row
            if cells[0].name == "th":
                continue
            abbr = cells[0].get_text(" ", strip=True)
            meaning = cells[1].get_text(" ", strip=True) if len(cells) > 1 else ""
            if not abbr or not meaning:
                continue
            if abbr.lower() in ("rank abbr.", "rank", "abbr.", "page/link"):
                continue
            link = None
            a = cells[0].find("a", href=True) or (cells[1].find("a", href=True) if len(cells) > 1 else None)
            if a:
                link = urllib.parse.urljoin(BASE, a["href"])
            results.append({"abbr": abbr, "meaning": meaning, "link": link})
        if results:
            break

    # fallback: markdown-style pipe rows sometimes survive as text
    if not results:
        for line in text.split("\n"):
            mm = re.match(r"\s*([A-Z0-9&.\-]{2,12})\s+(.{4,200})\s*", line)
            if mm:
                results.append({"abbr": mm.group(1), "meaning": mm.group(2), "link": None})

    # dedupe, keep order
    seen = set()
    clean = []
    for r in results:
        key = (r["abbr"], r["meaning"])
        if key in seen:
            continue
        seen.add(key)
        clean.append(r)
    return total, clean


def main():
    ap = argparse.ArgumentParser(description="Search AcronymFinder.com")
    ap.add_argument("acronym", help="acronym to look up, e.g. NASA")
    ap.add_argument("--limit", type=int, default=20, help="max meanings to show (default 20)")
    ap.add_argument("--json", action="store_true", help="output JSON")
    ap.add_argument("--all", action="store_true", help="show all meanings, ignore --limit")
    ap.add_argument("--no-bridge", action="store_true", help="do not fall back to real browser")
    args = ap.parse_args()

    acro = args.acronym.strip().upper()
    if not re.match(r"^[A-Z0-9&.\-]{1,20}$", acro):
        print(f"bad acronym: {args.acronym!r} (letters/numbers only, max 20)", file=sys.stderr)
        sys.exit(2)

    url = f"{BASE}/{urllib.parse.quote(acro)}.html"
    html = None
    method = "direct"
    try:
        url, html = fetch_direct(acro)
    except Exception as e:
        print(f"direct fetch failed: {e}", file=sys.stderr)
        html = ""

    if is_blocked(html):
        if args.no_bridge:
            print("blocked by bot check (Cloudflare). Retry later or drop --no-bridge.", file=sys.stderr)
            sys.exit(3)
        print("direct blocked, retrying via real browser...", file=sys.stderr)
        try:
            html = fetch_via_bridge(url)
            method = "browser"
        except Exception as e:
            print(f"browser fetch failed: {e}", file=sys.stderr)
            sys.exit(3)

    if is_blocked(html):
        print("still blocked by bot check. Try again in a minute.", file=sys.stderr)
        sys.exit(3)

    total, results = parse(html, acro)
    if args.all:
        shown = results
    else:
        shown = results[: args.limit]

    if args.json:
        print(json.dumps({
            "acronym": acro,
            "url": url,
            "method": method,
            "total_reported": total,
            "returned": len(shown),
            "results": shown,
        }, indent=2))
    else:
        head = f"{acro} — {total} meanings" if total else acro
        print(f"{head} ({url}) [{method}]")
        print("-" * len(head))
        if not shown:
            print("No meanings parsed.")
        for i, r in enumerate(shown, 1):
            print(f"{i}. {r['abbr']} = {r['meaning']}")
            if r.get("link"):
                print(f"   {r['link']}")


if __name__ == "__main__":
    main()
