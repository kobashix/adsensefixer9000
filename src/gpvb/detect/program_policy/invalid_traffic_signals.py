from __future__ import annotations

import re
from typing import List

from gpvb.models import Finding, FindingCategory, PageResult, Severity

from .context import ProgramPolicyContext


ENCOURAGEMENT_PATTERNS = [
    r"support us by clicking ads",
    r"click the ads",
    r"help us by clicking",
    r"visit our sponsors",
]

INVALID_TRAFFIC_POLICY_LINKS = [
    "https://support.google.com/adsense/answer/1348695",
    "https://support.google.com/adsense/answer/57153",
]


def _nearby_texts(page: PageResult, context: ProgramPolicyContext, radius: float = 600) -> List[str]:
    texts: List[str] = []
    for ad in page.ad_elements:
        for block in context.text_blocks:
            if abs(block.y - ad.y) <= radius:
                texts.append(block.text)
    return texts


def detect_invalid_traffic_signals(
    page: PageResult, context: ProgramPolicyContext
) -> List[Finding]:
    findings: List[Finding] = []
    nearby_text = " ".join(_nearby_texts(page, context)).lower()
    for pattern in ENCOURAGEMENT_PATTERNS:
        if re.search(pattern, nearby_text, re.IGNORECASE):
            findings.append(
                Finding(
                    detector="invalid_traffic_encouragement",
                    severity=Severity.high,
                    category=FindingCategory.program_policy,
                    confidence=0.82,
                    message="Explicit encouragement to click ads detected near ad placements.",
                    remediation=[
                        "Remove any language that asks users to click ads or support the site via ads.",
                        "Ensure ad placements are separated from user prompts and calls-to-action.",
                    ],
                    policy_links=INVALID_TRAFFIC_POLICY_LINKS,
                    evidence={"matched_pattern": pattern},
                )
            )
            break

    html = page.html
    meta_refresh = re.search(r"<meta[^>]+http-equiv=['\"]?refresh", html, re.IGNORECASE)
    js_reload = re.search(
        r"set(interval|timeout)\([^)]*(reload|adsbygoogle|googlesyndication)",
        html,
        re.IGNORECASE,
    )
    if meta_refresh or js_reload:
        findings.append(
            Finding(
                detector="invalid_traffic_reload_patterns",
                severity=Severity.medium,
                category=FindingCategory.program_policy,
                confidence=0.64,
                message="Auto-refresh or script reload patterns detected around ad containers.",
                remediation=[
                    "Remove auto-refresh or timer-based reloads that could inflate ad impressions.",
                    "Avoid re-rendering ad containers on a timer.",
                ],
                policy_links=INVALID_TRAFFIC_POLICY_LINKS,
                evidence={
                    "meta_refresh": bool(meta_refresh),
                    "js_reload": bool(js_reload),
                },
            )
        )

    above_fold = 0
    viewport_height = context.viewport.get("height", 768)
    viewport_width = context.viewport.get("width", 1366)
    for ad in page.ad_elements:
        fully_visible = (
            ad.y >= 0
            and ad.x >= 0
            and ad.y + ad.height <= viewport_height
            and ad.x + ad.width <= viewport_width
        )
        if fully_visible:
            above_fold += 1
    if above_fold > 3:
        findings.append(
            Finding(
                detector="invalid_traffic_high_density",
                severity=Severity.medium,
                category=FindingCategory.program_policy,
                confidence=0.6,
                message="Unusually high number of ads above the fold detected.",
                remediation=[
                    "Reduce the number of above-the-fold ad placements.",
                    "Ensure ads do not dominate the initial viewport.",
                ],
                policy_links=INVALID_TRAFFIC_POLICY_LINKS,
                evidence={"above_fold_ads": above_fold},
            )
        )
    return findings
