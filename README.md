# AcronymFinder CLI

Search AcronymFinder.com from the terminal. Single-file Python CLI with no build step.

```bash
.venv/bin/python af.py NASA
.venv/bin/python af.py NASA --json --limit 5
```

## Requirements

- Python 3.13 (tested) with `venv`
- Dependencies in `requirements.txt`: `requests`, `beautifulsoup4`, `lxml`
- Optional: [chrome-bridge](https://github.com/) with host Chrome Beta at `/opt/chrome-bridge/bin/chrome-bridge.mjs` — only needed when Cloudflare blocks direct HTTP

## Setup

A venv is required (system python currently lacks `typing_extensions`, so `bs4` fails there):

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Use

```bash
.venv/bin/python af.py NASA
.venv/bin/python af.py NASA --limit 10
.venv/bin/python af.py NASA --json > nasa.json
.venv/bin/python af.py FBI --json --limit 5
.venv/bin/python af.py NASA --all
.venv/bin/python af.py NASA --no-bridge   # skip real browser fallback
```

Or make it executable with the venv on PATH:

```bash
chmod +x af.py
./af.py NASA --limit 3
```

### Options

| Flag | Default | Description |
|------|---------|-------------|
| `acronym` | — | Acronym to look up (letters/numbers, max 20 chars, e.g. `NASA`) |
| `--limit N` | 20 | Max meanings to show |
| `--all` | off | Show all meanings, ignore `--limit` |
| `--json` | off | Output JSON (`acronym`, `url`, `method`, `total_reported`, `returned`, `results`) |
| `--no-bridge` | off | Do not fall back to real browser |

Example JSON output:

```json
{
  "acronym": "NASA",
  "url": "https://www.acronymfinder.com/NASA.html",
  "method": "direct",
  "total_reported": 48,
  "returned": 2,
  "results": [
    {
      "abbr": "NASA",
      "meaning": "National Aeronautics and Space Administration (USA)",
      "link": "https://www.acronymfinder.com/..."
    }
  ]
}
```

## How it works

1. Direct fetch of `https://www.acronymfinder.com/{ACRONYM}.html` with `requests`
2. Cloudflare bot-check detection (`Just a moment` / `Enable JavaScript and cookies`)
3. If blocked, falls back to Chrome Bridge (host Chrome Beta) to render the page like a real browser
4. Parses the Rank / Abbr / Meaning table with BeautifulSoup + lxml
5. Prints a numbered list or JSON with `--json`

## Notes

- Respect the site. Single lookups only, no bulk scraping.
- If both paths get blocked, wait a minute and retry (exit code 3).
- Exit codes: `0` success, `2` bad acronym input, `3` blocked / browser fetch failed.
- Unknown acronyms may return a junk fallback row instead of "No meanings parsed" — known limitation in `parse()`.
