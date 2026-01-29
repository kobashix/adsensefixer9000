from __future__ import annotations

import re
from typing import List

from gpvb.models import Finding, FindingCategory, PageResult, Severity


TRAFFIC_POLICY_LINKS = [
    "https://support.google.com/adsense/answer/48182",
    "https://support.google.com/adsense/answer/1346295",
]


INCENTIVIZED_PATTERNS = [
    r"get paid to visit",
    r"rewards for visiting",
    r"points for clicks",
    r"paid to click",
]


def detect_traffic_source_abuse(page: PageResult) -> List[Finding]:
    findings: List[Finding] = []
    html = page.html

    meta_refresh = re.search(
        r"<meta[^>]+http-equiv=['\"]?refresh[^>]+content=['\"]?(\d+)",
        html,
        re.IGNORECASE,
    )
    meta_refresh_fast = False
    if meta_refresh:
        try:
            meta_refresh_fast = int(meta_refresh.group(1)) < 5
        except ValueError:
            meta_refresh_fast = True

    js_redirect = re.search(
        r"(onload\s*=|addEventListener\(['\"]load['\"]\)).*(location|window\.location)",
        html,
        re.IGNORECASE,
    )
    location_replace = re.search(r"location\.replace\(", html, re.IGNORECASE)

    if meta_refresh_fast or js_redirect or location_replace:
        findings.append(
            Finding(
                detector="traffic_source_forced_redirects",
                severity=Severity.high,
                category=FindingCategory.program_policy,
                confidence=0.7,
                message="Forced redirects or fast refresh patterns detected.",
                remediation=[
                    "Remove auto-redirects or immediate refreshes before content loads.",
                    "Ensure users intentionally navigate to pages with ads.",
                ],
                policy_links=TRAFFIC_POLICY_LINKS,
                evidence={
                    "meta_refresh_fast": meta_refresh_fast,
                    "js_redirect": bool(js_redirect),
                    "location_replace": bool(location_replace),
                },
            )
        )

    text = (page.text or "").lower()
    for pattern in INCENTIVIZED_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            findings.append(
                Finding(
                    detector="traffic_source_incentivized",
                    severity=Severity.critical,
                    category=FindingCategory.program_policy,
                    confidence=0.86,
                    message="Incentivized traffic language detected.",
                    remediation=[
                        "Remove offers or rewards tied to visits or clicks.",
                        "Acquire traffic organically without incentivization.",
                    ],
                    policy_links=TRAFFIC_POLICY_LINKS,
                    evidence={"matched_pattern": pattern},
                )
            )
            break
    return findings
