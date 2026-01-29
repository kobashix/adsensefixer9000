from __future__ import annotations

import re
from typing import List

from bs4 import BeautifulSoup

from gpvb.models import Finding, FindingCategory, PageResult, Severity


DECEPTIVE_POLICY_LINKS = [
    "https://support.google.com/adsense/answer/1346295",
    "https://support.google.com/adsense/answer/2785928",
]


AFFILIATION_KEYWORDS = [
    "google",
    "irs",
    "government",
    "official",
    "authorized",
    "partner",
    "approved",
]

DISCLAIMER_PATTERNS = [
    r"not affiliated",
    r"not endorsed",
    r"no affiliation",
    r"independent",
]


def _claims_affiliation(text: str) -> bool:
    lowered = text.lower()
    for keyword in ["official", "authorized", "partner", "approved"]:
        if keyword in lowered and any(brand in lowered for brand in ["google", "irs", "government"]):
            return True
    return False


def _find_disclaimer(html: str) -> bool:
    for pattern in DISCLAIMER_PATTERNS:
        if re.search(pattern, html, re.IGNORECASE):
            return True
    return False


def _disclaimer_low_visibility(html: str) -> bool:
    soup = BeautifulSoup(html, "lxml")
    for pattern in DISCLAIMER_PATTERNS:
        for element in soup.find_all(string=re.compile(pattern, re.IGNORECASE)):
            parent = element.parent
            if not parent:
                continue
            style = parent.get("style", "").lower()
            classes = " ".join(parent.get("class", [])).lower()
            if "font-size" in style or "opacity" in style or "fine-print" in classes or "footer" in classes:
                return True
            if parent.name in {"small", "footer"}:
                return True
    return False


def detect_deceptive_representation(page: PageResult) -> List[Finding]:
    findings: List[Finding] = []
    text = page.text or ""
    if not _claims_affiliation(text):
        return findings

    disclaimer_present = _find_disclaimer(page.html)
    if not disclaimer_present:
        findings.append(
            Finding(
                detector="deceptive_affiliation_claims",
                severity=Severity.high,
                category=FindingCategory.program_policy,
                confidence=0.72,
                message="Claims of affiliation or authorization detected without disclaimer.",
                remediation=[
                    "Remove claims of official status or brand affiliation unless authorized.",
                    "Add clear disclaimers when referencing third-party brands.",
                ],
                policy_links=DECEPTIVE_POLICY_LINKS,
                evidence={"keywords": AFFILIATION_KEYWORDS},
            )
        )
    elif _disclaimer_low_visibility(page.html):
        findings.append(
            Finding(
                detector="deceptive_affiliation_disclaimer_low_visibility",
                severity=Severity.medium,
                category=FindingCategory.program_policy,
                confidence=0.6,
                message="Affiliation disclaimer appears low visibility or buried.",
                remediation=[
                    "Place disclaimers near claims and make them easy to read.",
                    "Avoid hiding disclosures in footers or fine print.",
                ],
                policy_links=DECEPTIVE_POLICY_LINKS,
                evidence={"disclaimer_low_visibility": True},
            )
        )
    return findings
