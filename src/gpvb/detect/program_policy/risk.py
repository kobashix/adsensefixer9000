from __future__ import annotations

from typing import Dict, List

from gpvb.models import Finding, Severity


def calculate_account_risk_score(findings: List[Finding]) -> Dict[str, int | str]:
    score = 0
    for finding in findings:
        if finding.severity == Severity.critical:
            score += 30
        elif finding.severity == Severity.high:
            score += 15
        elif finding.severity == Severity.medium:
            score += 5
        elif finding.severity == Severity.low:
            score += 1
    score = min(score, 100)
    if score <= 15:
        label = "Low Risk"
    elif score <= 40:
        label = "Moderate Risk"
    elif score <= 70:
        label = "High Risk"
    else:
        label = "Severe Risk (Likely Enforcement)"
    return {"score": score, "label": label}
