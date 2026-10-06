# AGENTS.md

## Project Overview
- Single-file Python CLI (`af.py`) that searches AcronymFinder.com from the terminal.
- Flow: direct `requests` fetch of `https://www.acronymfinder.com/{ACRONYM}.html` → Cloudflare check → optional Chrome Bridge fallback → `BeautifulSoup`/`lxml` parse of the Rank/Abbr/Meaning table → text or JSON output.
- No framework, no tests, no CI, no build step. Only deps: `requirements.txt` (`requests`, `beautifulsoup4`, `lxml`).

## Setup Commands
- Venv is required (system python is currently broken: `bs4` fails on missing `typing_extensions`):
  ```bash
  python3 -m venv .venv
  .venv/bin/pip install -r requirements.txt
  ```
- Run with the venv python:
  ```bash
  .venv/bin/python af.py --help
  .venv/bin/python af.py NASA --limit 3
  ```
- `af.py` has a shebang and is executable, but still needs the venv interpreter's deps — `./af.py` alone fails unless deps are installed for that interpreter.

## Test and Validation Commands
- No test suite, linter, typechecker, or CI in this repo.
- Validate changes with:
  ```bash
  .venv/bin/python af.py --help
  .venv/bin/python af.py NASA --limit 3
  .venv/bin/python af.py NASA --json --limit 2
  ```
- Invalid input must exit 2: `.venv/bin/python af.py "bad input!"`
- All of the above were verified working 2026-10-06 (direct fetch path, no bridge needed).

## Code Style
- Single file, stdlib-first (`argparse`, `json`, `re`, `urllib.parse`). Keep it that way; do not add a package layout or framework.
- Functions in `af.py`: `fetch_direct`, `is_blocked`, `fetch_via_bridge`, `parse`, `main`. Preserve their signatures unless there is a reason to change.
- Acronym input is normalized to uppercase and validated as `^[A-Z0-9&.\-]{1,20}$`.
- Output shapes: human-readable numbered list by default, JSON object (`acronym`, `url`, `method`, `total_reported`, `returned`, `results`) with `--json`.

## Architecture Notes
- `af.py` — everything (fetch, block detection, parse, CLI).
- `requirements.txt` — only three runtime deps; do not add unneeded deps.
- `BRIDGE` / `BRIDGE_ENV` in `af.py:28-33` point at a machine-local path (`/opt/chrome-bridge/bin/chrome-bridge.mjs`, `BROWSER=chrome-beta`). Do not assume it exists on other machines; `--no-bridge` must keep working.
- Known limitation: unknown acronyms (e.g. `XYZQQQ`) can return a junk fallback row parsed from page chrome instead of "No meanings parsed." Fix in `parse()` in `af.py:80-131` if touching that path.

## Safety and Data Rules
- Respect the target site: single lookups only, no bulk scraping (see `README.md`).
- Cloudflare blocking (`is_blocked`, `af.py:42-46`) is expected behavior — exit 3, wait a minute, retry. Do not add retry hammering.
- Never commit `.venv/`, `__pycache__/`, `*.json` output files, or credentials. There are no secrets in this repo.
- Destructive ops: none. The tool only performs GETs.

## PR / Commit Notes
- No commit, changelog, PR, or release convention established. Keep changes minimal and update `README.md` when CLI flags change.
