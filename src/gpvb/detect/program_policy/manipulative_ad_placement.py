from __future__ import annotations

from typing import List

from bs4 import BeautifulSoup

from gpvb.models import Finding, FindingCategory, PageResult, Severity

from .context import ProgramPolicyContext


PLACEMENT_POLICY_LINKS = [
    "https://support.google.com/adsense/answer/1346295",
    "https://support.google.com/adsense/answer/48182",
]


def _ad_in_list_or_menu(html: str) -> bool:
    soup = BeautifulSoup(html, "lxml")
    selectors = [
        "ins.adsbygoogle",
        "iframe[src*='googlesyndication']",
        "iframe[id*='google_ads']",
        "[data-ad-client]",
        "[data-ad-slot]",
    ]
    for ad in soup.select(",".join(selectors)):
        if ad.find_parent(["ul", "ol", "nav", "menu", "li"]):
            return True
    return False


def _find_label_near_ad(
    ad_y: float, label_blocks: List, max_distance: float = 120
) -> List:
    return [label for label in label_blocks if abs(label.y - ad_y) <= max_distance]


def detect_manipulative_ad_placement(
    page: PageResult, context: ProgramPolicyContext
) -> List[Finding]:
    findings: List[Finding] = []
    misleading_styling = False
    if any(ad.overlaps_nav or ad.overlaps_content for ad in page.ad_elements):
        misleading_styling = True
    if _ad_in_list_or_menu(page.html):
        misleading_styling = True

    weak_labels = 0
    missing_labels = 0
    for ad in page.ad_elements:
        labels = _find_label_near_ad(ad.y, context.label_blocks)
        if not labels:
            missing_labels += 1
            continue
        if any(label.font_size < 10 or label.opacity < 0.7 for label in labels):
            weak_labels += 1

    if misleading_styling:
        findings.append(
            Finding(
                detector="manipulative_ad_styling",
                severity=Severity.high,
                category=FindingCategory.program_policy,
                confidence=0.72,
                message="Ads appear styled to blend with navigation or content.",
                remediation=[
                    "Separate ad placements from navigation and primary content blocks.",
                    "Use clear visual separation (borders, spacing) around ads.",
                ],
                policy_links=PLACEMENT_POLICY_LINKS,
                evidence={
                    "overlaps_nav_or_content": any(
                        ad.overlaps_nav or ad.overlaps_content for ad in page.ad_elements
                    ),
                    "ads_in_lists": _ad_in_list_or_menu(page.html),
                },
            )
        )

    if missing_labels or weak_labels:
        findings.append(
            Finding(
                detector="ad_labeling_issues",
                severity=Severity.medium,
                category=FindingCategory.program_policy,
                confidence=0.6,
                message="Ad labeling appears missing or low visibility.",
                remediation=[
                    "Add clear 'Advertisement' or 'Sponsored' labels adjacent to ads.",
                    "Ensure labels are legible and not faded or hidden.",
                ],
                policy_links=PLACEMENT_POLICY_LINKS,
                evidence={
                    "missing_labels": missing_labels,
                    "weak_labels": weak_labels,
                },
            )
        )
    return findings
