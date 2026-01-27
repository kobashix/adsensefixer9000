# Google Policy Violations Bot (GPVB)

GPVB is a CLI tool that crawls a site and reports likely Google AdSense / Publisher Policy violations using heuristic detectors.

## Install

```bash
python -m venv .venv
. .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e .
python -m playwright install chromium
```

## Windows 11 (PowerShell) step-by-step

1. Open PowerShell and go to the repo folder:
   ```powershell
   cd C:\path\to\adsensefixer9000
   ```
2. Create and activate a virtual environment:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
3. Install the package and dev dependencies (optional for tests):
   ```powershell
   pip install -e .
   ```
   If you update the code, re-run the same command to refresh the console script:
   ```powershell
   pip install -e .
   ```
4. Install Playwright Chromium:
   ```powershell
   python -m playwright install chromium
   ```
5. Run an audit:
   ```powershell
   gpvb audit --site https://example.com --out .\out --max-pages 500 --concurrency 6 --respect-robots true --user-agent "GPVB/1.0"
   ```
6. Open the report:
   ```powershell
   start .\out\report.html
   ```

## Usage

```bash
gpvb audit --site https://example.com --out ./out --max-pages 500 --concurrency 6 \
  --respect-robots true --user-agent "GPVB/1.0"
```

### Options

- `--max-pages`: hard cap on pages crawled.
- `--max-depth`: BFS depth when no sitemap is found.
- `--include-regex`, `--exclude-regex`: URL filters.
- `--ignore-querystrings`: drop query strings when canonicalizing.
- `--respect-robots`: honor robots.txt (`true`/`false`).
- `--rate-limit-ms`: per-host delay (default 250ms).

## Output

```
out/
  report.html
  findings.json
  pages/<slug>/screenshot.png
```

## Development

```bash
ruff check .
pytest
```
