from __future__ import annotations

import re
from typing import List

from gpvb.models import Finding, FindingCategory, PageResult, Severity


UGC_POLICY_LINKS = [
    "https://support.google.com/adsense/answer/1346295",
    "https://support.google.com/adsense/answer/48182",
]

SPAM_KEYWORDS = [
    "buy now",
    "free money",
    "work from home",
    "viagra",
    "crypto giveaway",
]

HIGH_RISK_TERMS = [
    "casino",
    "betting",
    "porn",
    "escort",
    "illegal",
    "drugs",
]


def _has_comment_section(html: str) -> bool:
    lower = html.lower()
    return any(token in lower for token in ["comment", "forum", "reply", "thread", "post"])


def _has_moderation(html: str) -> bool:
    lower = html.lower()
    return any(token in lower for token in ["captcha", "moderation", "awaiting approval", "nofollow"])


def detect_ugc_risk(page: PageResult) -> List[Finding]:
    findings: List[Finding] = []
    if not _has_comment_section(page.html):
        return findings

    text = page.text.lower()
    high_risk_hits = [term for term in HIGH_RISK_TERMS if term in text]
    spam_hits = [term for term in SPAM_KEYWORDS if term in text]
    has_moderation = _has_moderation(page.html)

    if high_risk_hits:
        findings.append(
            Finding(
                detector="ugc_high_risk_terms",
                severity=Severity.high,
                category=FindingCategory.program_policy,
                confidence=0.7,
                message="User-generated content contains high-risk terms.",
                remediation=[
                    "Moderate or remove high-risk user-generated content.",
                    "Add keyword filters and active moderation workflows.",
                ],
                policy_links=UGC_POLICY_LINKS,
                evidence={"high_risk_terms": high_risk_hits},
            )
        )
    elif spam_hits and not has_moderation:
        findings.append(
            Finding(
                detector="ugc_unmoderated_spam",
                severity=Severity.medium,
                category=FindingCategory.program_policy,
                confidence=0.55,
                message="Comment or forum sections show spam signals without moderation.",
                remediation=[
                    "Enable moderation, CAPTCHA, or rel=\"nofollow\" on UGC links.",
                    "Remove spam-heavy threads or restrict posting privileges.",
                ],
                policy_links=UGC_POLICY_LINKS,
                evidence={"spam_terms": spam_hits},
            )
        )
    elif not has_moderation:
        findings.append(
            Finding(
                detector="ugc_unmoderated",
                severity=Severity.medium,
                category=FindingCategory.program_policy,
                confidence=0.5,
                message="User-generated content detected without clear moderation controls.",
                remediation=[
                    "Add moderation notices or CAPTCHA on comment submissions.",
                    "Apply rel=\"nofollow\" to outbound UGC links.",
                ],
                policy_links=UGC_POLICY_LINKS,
                evidence={"moderation_detected": has_moderation},
            )
        )
    return findings
