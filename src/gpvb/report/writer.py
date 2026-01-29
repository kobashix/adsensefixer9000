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
    html = _render_html(
        report.pages, report.summary, report.program_policy_summary, duplicates, report.account_risk
    )
    (out_dir / "report.html").write_text(html, encoding="utf-8")


def _render_html(
    pages: List[PageResult],
    summary: Dict[str, Dict[str, int]],
    program_policy_summary: Dict[str, Dict[str, int]],
    duplicates: List[Dict],
    account_risk: Dict[str, int | str],
) -> str:
    sorted_pages = _sort_pages_by_severity(pages)
    page_cards = "\n".join(_render_page_card(page) for page in sorted_pages)
    program_policy_cards = "\n".join(
        _render_page_card(page, category_filter="program_policy") for page in sorted_pages
    )
    summary_rows = "\n".join(
        f"<tr><td>{detector}</td><td>{_format_counts(counts)}</td></tr>"
        for detector, counts in summary.items()
    )
    program_policy_rows = "\n".join(
        f"<tr><td>{detector}</td><td>{_format_counts(counts)}</td></tr>"
        for detector, counts in program_policy_summary.items()
    )
    dup_sections = "\n".join(
        f"<li>{', '.join(cluster['urls'])} (sim {cluster['similarity']})</li>" for cluster in duplicates
    )
    risk_score = int(account_risk.get("score", 0)) if account_risk else 0
    risk_label = account_risk.get("label", "Unknown") if account_risk else "Unknown"
    template = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>GPVB Report</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 20px; }}
    .tabs {{ display: flex; gap: 8px; margin-bottom: 16px; }}
    .tab-button {{ padding: 8px 12px; border: 1px solid #ccc; cursor: pointer; }}
    .tab-button.active {{ background: #f0f0f0; font-weight: bold; }}
    .tab-content {{ display: none; }}
    .tab-content.active {{ display: block; }}
    .card {{ border: 1px solid #ddd; padding: 16px; margin-bottom: 16px; }}
    .screenshot {{ width: 240px; border: 1px solid #ccc; }}
    .findings {{ margin-top: 8px; }}
    .risk-gauge {{ margin: 16px 0; }}
    .risk-bar {{ background: #eee; height: 16px; border-radius: 8px; overflow: hidden; }}
    .risk-fill {{ background: #d9534f; height: 100%; }}
  </style>
</head>
<body>
  <h1>GPVB Findings Report</h1>
  <div class="tabs">
    <button class="tab-button active" data-tab="overview">Overview</button>
    <button class="tab-button" data-tab="program-policy">Program Policy Violations</button>
  </div>
  <div id="overview" class="tab-content active">
    <div>
      <label>Severity filter:</label>
      <select id="severity-filter">
        <option value="all">All</option>
        <option value="critical">Critical</option>
        <option value="high">High</option>
        <option value="medium">Medium</option>
        <option value="low">Low</option>
        <option value="none">None</option>
      </select>
      <label>Detector filter:</label>
      <input id="detector-filter" placeholder="detector name" />
    </div>
    <div class="risk-gauge">
      <strong>Likely Account Risk:</strong> {risk_score} ({risk_label})
      <div class="risk-bar"><div class="risk-fill" style="width: {risk_score}%"></div></div>
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
  </div>
  <div id="program-policy" class="tab-content">
    <h2>Program Policy Summary</h2>
    <table>
      <tr><th>Detector</th><th>Counts</th></tr>
      {program_policy_rows}
    </table>
    <h2>Program Policy Findings</h2>
    {program_policy_cards}
  </div>
  <script>
    const tabs = Array.from(document.querySelectorAll('.tab-button'));
    const tabContents = Array.from(document.querySelectorAll('.tab-content'));
    tabs.forEach((tab) => {{
      tab.addEventListener('click', () => {{
        tabs.forEach((btn) => btn.classList.remove('active'));
        tab.classList.add('active');
        tabContents.forEach((content) => {{
          content.classList.toggle('active', content.id === tab.dataset.tab);
        }});
      }});
    }});
    const severityFilter = document.getElementById('severity-filter');
    const detectorFilter = document.getElementById('detector-filter');
    const cards = Array.from(document.querySelectorAll('#overview .card'));
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
        program_policy_rows=program_policy_rows,
        dup_sections=dup_sections,
        page_cards=page_cards,
        program_policy_cards=program_policy_cards,
        risk_score=risk_score,
        risk_label=risk_label,
    )


def _render_page_card(page: PageResult, category_filter: str | None = None) -> str:
    findings_list = page.findings
    if category_filter:
        findings_list = [finding for finding in page.findings if finding.category.value == category_filter]
    findings_list = _sort_findings(findings_list)
    if not findings_list:
        return ""
    findings = "\n".join(_render_finding(finding) for finding in findings_list)
    screenshot_html = (
        f"<img class='screenshot' src='{page.screenshot_path}' />" if page.screenshot_path else ""
    )
    detectors = ",".join({finding.detector for finding in findings_list}) or "none"
    severities = ",".join({finding.severity.value for finding in findings_list}) or "none"
    return f"""
  <div class="card" data-detectors="{detectors}" data-severities="{severities}">
    <h3>{page.url}</h3>
    <p>Status: {page.status} Final URL: {page.final_url}</p>
    {screenshot_html}
    <ul class="findings">{findings}</ul>
  </div>
"""


def _render_finding(finding) -> str:
    remediation = "".join(f"<li>{item}</li>" for item in finding.remediation) or "<li>None</li>"
    policy_links = "".join(f"<li>{link}</li>" for link in finding.policy_links) or "<li>None</li>"
    return (
        "<li>"
        f"<strong>{finding.detector}</strong> ({finding.severity.value}): {finding.message}"
        f"<div><em>Confidence:</em> {finding.confidence:.2f}</div>"
        f"<div><em>Remediation:</em><ul>{remediation}</ul></div>"
        f"<div><em>Policy references:</em><ul>{policy_links}</ul></div>"
        "</li>"
    )


def _sort_findings(findings: List) -> List:
    order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    return sorted(findings, key=lambda finding: order.get(finding.severity.value, 99))


def _sort_pages_by_severity(pages: List[PageResult]) -> List[PageResult]:
    order = {"critical": 0, "high": 1, "medium": 2, "low": 3}

    def max_severity(page: PageResult) -> int:
        if not page.findings:
            return 99
        return min(order.get(finding.severity.value, 99) for finding in page.findings)

    return sorted(pages, key=max_severity)


def _format_counts(counts: Dict[str, int]) -> str:
    return ", ".join(f"{severity}: {count}" for severity, count in sorted(counts.items()))
