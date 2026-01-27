# Google Policy Violations Bot (GPVB)

GPVB is a CLI tool that crawls a site and reports likely Google AdSense / Publisher Policy violations using heuristic detectors.

## Install

```bash
python -m venv .venv
. .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e .
python -m playwright install chromium
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
- `--respect-robots`: honor robots.txt.
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
