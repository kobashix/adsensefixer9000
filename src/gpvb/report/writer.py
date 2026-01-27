from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

from gpvb.models import FindingsReport, PageResult


def write_json(report: FindingsReport, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    data = report.model_dump()
    (out_dir / "findings.json").write_text(json.dumps(data, indent=2))


def write_html(report: FindingsReport, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    duplicates = [cluster.__dict__ for cluster in report.duplicates]
    html = _render_html(report.pages, report.summary, duplicates)
    (out_dir / "report.html").write_text(html, encoding="utf-8")


def _render_html(
    pages: List[PageResult], summary: Dict[str, Dict[str, int]], duplicates: List[Dict]
) -> str:
    page_cards = "\n".join(_render_page_card(page) for page in pages)
    summary_rows = "\n".join(
        f"<tr><td>{detector}</td><td>{counts}</td></tr>" for detector, counts in summary.items()
    )
    dup_sections = "\n".join(
        f"<li>{', '.join(cluster['urls'])} (sim {cluster['similarity']})</li>" for cluster in duplicates
    )
    template = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>GPVB Report</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 20px; }}
    .card {{ border: 1px solid #ddd; padding: 16px; margin-bottom: 16px; }}
    .screenshot {{ width: 240px; border: 1px solid #ccc; }}
    .findings {{ margin-top: 8px; }}
  </style>
</head>
<body>
  <h1>GPVB Findings Report</h1>
  <div>
    <label>Severity filter:</label>
    <select id="severity-filter">
      <option value="all">All</option>
      <option value="high">High</option>
      <option value="medium">Medium</option>
      <option value="low">Low</option>
      <option value="none">None</option>
    </select>
    <label>Detector filter:</label>
    <input id="detector-filter" placeholder="detector name" />
  </div>
  <h2>Summary</h2>
  <table>
    <tr><th>Detector</th><th>Counts</th></tr>
    {summary_rows}
  </table>
  <h2>Duplicate Clusters</h2>
  <ul>
    {dup_sections}
  </ul>
  <h2>Pages</h2>
  {page_cards}
  <script>
    const severityFilter = document.getElementById('severity-filter');
    const detectorFilter = document.getElementById('detector-filter');
    const cards = Array.from(document.querySelectorAll('.card'));
    const applyFilters = () => {{
      const severity = severityFilter.value;
      const detector = detectorFilter.value.trim().toLowerCase();
      cards.forEach((card) => {{
        const severities = card.dataset.severities.split(',');
        const detectors = card.dataset.detectors.split(',');
        const severityMatch = severity === 'all' || severities.includes(severity);
        const detectorMatch = !detector || detectors.some((d) => d.includes(detector));
        card.style.display = severityMatch && detectorMatch ? 'block' : 'none';
      }});
    }};
    severityFilter.addEventListener('change', applyFilters);
    detectorFilter.addEventListener('input', applyFilters);
  </script>
</body>
</html>
"""
    return template.format(
        summary_rows=summary_rows,
        dup_sections=dup_sections,
        page_cards=page_cards,
    )


def _render_page_card(page: PageResult) -> str:
    findings = "\n".join(
        f"<li><strong>{finding.detector}</strong> ({finding.severity}): {finding.message}</li>"
        for finding in page.findings
    )
    screenshot_html = (
        f"<img class='screenshot' src='{page.screenshot_path}' />" if page.screenshot_path else ""
    )
    detectors = ",".join({finding.detector for finding in page.findings}) or "none"
    severities = ",".join({finding.severity.value for finding in page.findings}) or "none"
    return f"""
  <div class="card" data-detectors="{detectors}" data-severities="{severities}">
    <h3>{page.url}</h3>
    <p>Status: {page.status} Final URL: {page.final_url}</p>
    {screenshot_html}
    <ul class="findings">{findings}</ul>
  </div>
"""
