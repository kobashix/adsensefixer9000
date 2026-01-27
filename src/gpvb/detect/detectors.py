from __future__ import annotations

from typing import Dict, List

from bs4 import BeautifulSoup
from langdetect import detect

from gpvb.detect.text import cluster_simhash, extract_visible_text, word_count
from gpvb.models import AdElement, Finding, PageResult, Severity


def detect_thin_content(page: PageResult) -> List[Finding]:
    count = word_count(page.text)
    if count < 300:
        return [
            Finding(
                detector="thin_content",
                severity=Severity.medium,
                message="Page has low visible word count.",
                evidence={"word_count": count},
            )
        ]
    return []


def detect_ads_vs_content(page: PageResult) -> List[Finding]:
    ad_count = len(page.ad_elements)
    ad_area = sum(ad.width * ad.height for ad in page.ad_elements)
    viewport_area = 1366 * 768
    word_count_value = word_count(page.text)
    ad_ratio = ad_area / viewport_area if viewport_area else 0
    if (ad_count >= 4 and word_count_value < 400) or ad_ratio > 0.35:
        return [
            Finding(
                detector="ads_vs_content",
                severity=Severity.high,
                message="More ads than content detected.",
                evidence={
                    "ad_count": ad_count,
                    "word_count": word_count_value,
                    "ad_area_ratio": round(ad_ratio, 3),
                },
            )
        ]
    return []


def detect_ads_interfering(page: PageResult) -> List[Finding]:
    overlapping = [ad for ad in page.ad_elements if ad.overlaps_clickable or ad.overlaps_content]
    if overlapping:
        return [
            Finding(
                detector="ads_interfering",
                severity=Severity.high,
                message="Ads overlapping interactive or primary content.",
                evidence={"overlap_count": len(overlapping)},
            )
        ]
    return []


def detect_dead_end(page: PageResult, overlays: List[Dict[str, float]]) -> List[Finding]:
    if overlays and page.ad_elements:
        return [
            Finding(
                detector="dead_end_ad",
                severity=Severity.high,
                message="Modal overlay with ads may block content.",
                evidence={"overlay_count": len(overlays)},
            )
        ]
    return []


def detect_language_issue(page: PageResult) -> List[Finding]:
    soup = BeautifulSoup(page.html, "lxml")
    html_lang = (soup.html.get("lang") if soup.html else "") or ""
    try:
        detected = detect(page.text) if page.text else ""
    except Exception:
        detected = ""
    if not detected or (html_lang and detected not in html_lang):
        return [
            Finding(
                detector="language_issue",
                severity=Severity.low,
                message="Language mismatch or undetected language.",
                evidence={"html_lang": html_lang, "detected": detected},
            )
        ]
    return []


def detect_abusive_experience(page: PageResult, mobile_flags: Dict[str, bool]) -> List[Finding]:
    if any(mobile_flags.values()):
        return [
            Finding(
                detector="abusive_experience",
                severity=Severity.medium,
                message="Possible abusive experience heuristics triggered.",
                evidence=mobile_flags,
            )
        ]
    return []


def detect_privacy_policy(found: bool) -> List[Finding]:
    if not found:
        return [
            Finding(
                detector="missing_privacy_policy",
                severity=Severity.high,
                message="No privacy policy page found.",
                evidence={},
            )
        ]
    return []


def detect_ads_txt(status: int, lines: int) -> List[Finding]:
    if status >= 400 or lines < 1:
        return [
            Finding(
                detector="missing_ads_txt",
                severity=Severity.medium,
                message="ads.txt missing or empty.",
                evidence={"status": status, "lines": lines},
            )
        ]
    return []


def detect_replicated_content(pages: List[PageResult], threshold: float = 0.85) -> List[Finding]:
    urls = [page.url for page in pages]
    texts = [page.text for page in pages]
    clusters = cluster_simhash(urls, texts, threshold)
    findings: List[Finding] = []
    for urls_group, similarity in clusters:
        findings.append(
            Finding(
                detector="replicated_content",
                severity=Severity.high,
                message="Near-duplicate content cluster detected.",
                evidence={"urls": urls_group, "similarity": round(similarity, 3)},
            )
        )
    return findings


def merge_page_findings(page: PageResult, overlays: List[Dict[str, float]], mobile_flags: Dict[str, bool]) -> None:
    page.findings.extend(detect_thin_content(page))
    page.findings.extend(detect_ads_vs_content(page))
    page.findings.extend(detect_ads_interfering(page))
    page.findings.extend(detect_dead_end(page, overlays))
    page.findings.extend(detect_language_issue(page))
    page.findings.extend(detect_abusive_experience(page, mobile_flags))
