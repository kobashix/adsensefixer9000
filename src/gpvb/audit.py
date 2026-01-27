from __future__ import annotations

import asyncio
import re
import time
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
from urllib import robotparser

from gpvb.crawl.canonicalize import canonicalize_url
from gpvb.crawl.sitemap import expand_sitemaps, extract_links
from gpvb.detect.ads_txt import fetch_ads_txt
from gpvb.detect.detectors import (
    detect_ads_txt,
    detect_privacy_policy,
    detect_replicated_content,
    merge_page_findings,
)
from gpvb.detect.text import extract_visible_text
from gpvb.models import AdElement, CrawlConfig, DuplicateCluster, FindingsReport, PageResult
from gpvb.render.browser import BrowserPool
from gpvb.report.writer import write_html, write_json
from gpvb.storage import Storage


async def audit_site(config: CrawlConfig) -> FindingsReport:
    out_dir = Path(config.out_dir)
    pages_dir = out_dir / "pages"
    pages_dir.mkdir(parents=True, exist_ok=True)

    client = httpx.AsyncClient(headers={"User-Agent": config.user_agent}, timeout=20)
    robots = await _load_robots(client, config.site, config.respect_robots)

    sitemap_urls = await expand_sitemaps(client, config.site)
    queue: asyncio.Queue[Tuple[str, int]] = asyncio.Queue()
    if sitemap_urls:
        for url in sitemap_urls:
            await queue.put((url, 0))
    else:
        await queue.put((config.site, 0))

    include_pattern = re.compile(config.include_regex) if config.include_regex else None
    exclude_pattern = re.compile(config.exclude_regex) if config.exclude_regex else None

    seen: Set[str] = set()
    pages: List[PageResult] = []
    last_request: Dict[str, float] = defaultdict(float)
    privacy_found = False
    lock = asyncio.Lock()

    async with BrowserPool(config.concurrency, config.user_agent) as pool:
        async def worker() -> None:
            nonlocal privacy_found
            while True:
                item = await queue.get()
                if item is None:
                    queue.task_done()
                    break
                url, depth = item
                canonical = canonicalize_url(url, config.ignore_querystrings)

                async with lock:
                    if canonical in seen or len(pages) >= config.max_pages:
                        queue.task_done()
                        continue
                    seen.add(canonical)

                if include_pattern and not include_pattern.search(canonical):
                    queue.task_done()
                    continue
                if exclude_pattern and exclude_pattern.search(canonical):
                    queue.task_done()
                    continue
                if robots and not robots.can_fetch(config.user_agent, canonical):
                    queue.task_done()
                    continue

                await _rate_limit(canonical, last_request, config.rate_limit_ms, lock)

                slug = _slugify(canonical)
                screenshot_path = pages_dir / slug / "screenshot.png"
                screenshot_path.parent.mkdir(parents=True, exist_ok=True)

                final_url, status, html, text, network, ad_elements, extras = await pool.render_page(
                    canonical,
                    viewport={"width": 1366, "height": 768},
                    screenshot_path=str(screenshot_path),
                )
                text = extract_visible_text(html)
                page = PageResult(
                    url=canonical,
                    final_url=final_url,
                    status=status,
                    html=html,
                    text=text,
                    screenshot_path=str(screenshot_path.relative_to(out_dir)),
                    network_summary=network,
                    ad_elements=ad_elements,
                )
                if extras.get("has_google_ad_client"):
                    page.ad_elements.append(
                        AdElement(
                            selector="google_ad_client_script",
                            x=0,
                            y=0,
                            width=0,
                            height=0,
                        )
                    )

                noindex_header = _has_noindex_header(extras.get("headers", {}))
                if extras.get("has_noindex_meta") or noindex_header:
                    page.skipped_reason = "noindex"

                overlays = extras.get("overlays", [])
                mobile_flags = await pool.collect_mobile_flags(
                    canonical,
                    viewport={"width": 390, "height": 844},
                )

                if not page.skipped_reason:
                    merge_page_findings(page, overlays, mobile_flags)
                    if _page_mentions_privacy(html):
                        privacy_found = True

                async with lock:
                    pages.append(page)

                if not sitemap_urls and depth < config.max_depth:
                    for link in extract_links(html, final_url):
                        canonical_link = canonicalize_url(link, config.ignore_querystrings)
                        async with lock:
                            if canonical_link in seen:
                                continue
                        await queue.put((canonical_link, depth + 1))

                queue.task_done()

        workers = [asyncio.create_task(worker()) for _ in range(config.concurrency)]
        await queue.join()
        for _ in workers:
            await queue.put(None)
        await asyncio.gather(*workers)

    privacy_found = privacy_found or await _probe_privacy_paths(client, config.site)
    ads_status, ads_lines = await fetch_ads_txt(client, config.site)
    await client.aclose()

    summary = _summarize(pages)
    summary_findings = detect_ads_txt(ads_status, ads_lines)
    privacy_findings = detect_privacy_policy(privacy_found)

    duplicates = []
    replicated_findings = detect_replicated_content(
        [page for page in pages if not page.skipped_reason]
    )
    if replicated_findings:
        for finding in replicated_findings:
            duplicates.append(
                DuplicateCluster(urls=finding.evidence["urls"], similarity=finding.evidence["similarity"])
            )

    report = FindingsReport(
        summary=summary,
        pages=pages,
        duplicates=duplicates,
        site=config.site,
    )
    for finding in summary_findings + privacy_findings:
        summary.setdefault(finding.detector, {})[finding.severity.value] = (
            summary.setdefault(finding.detector, {}).get(finding.severity.value, 0) + 1
        )

    write_json(report, out_dir)
    write_html(report, out_dir)

    if config.list_skipped:
        skipped = [page for page in pages if page.skipped_reason]
        if skipped:
            storage = Storage(Path("gpvb.sqlite"))
            storage.save_pages(skipped)

    return report


async def _load_robots(
    client: httpx.AsyncClient, base_url: str, respect_robots: bool
) -> Optional[robotparser.RobotFileParser]:
    if not respect_robots:
        return None
    robots_url = base_url.rstrip("/") + "/robots.txt"
    try:
        response = await client.get(robots_url)
    except httpx.HTTPError:
        return None
    parser = robotparser.RobotFileParser()
    parser.parse(response.text.splitlines())
    return parser


async def _rate_limit(
    url: str, last_request: Dict[str, float], delay_ms: int, lock: asyncio.Lock
) -> None:
    host = urlparse(url).netloc
    async with lock:
        elapsed = time.time() - last_request[host]
        wait_for = max(0, delay_ms / 1000 - elapsed)
    if wait_for > 0:
        await asyncio.sleep(wait_for)
    async with lock:
        last_request[host] = time.time()


def _page_mentions_privacy(html: str) -> bool:
    soup = BeautifulSoup(html, "lxml")
    for link in soup.select("a"):
        text = (link.get_text() or "").strip().lower()
        if "privacy" in text:
            return True
    return False


def _has_noindex_header(headers: Dict[str, str]) -> bool:
    value = headers.get("x-robots-tag", "") if headers else ""
    return "noindex" in value.lower()


def _summarize(pages: List[PageResult]) -> Dict[str, Dict[str, int]]:
    summary: Dict[str, Dict[str, int]] = {}
    for page in pages:
        for finding in page.findings:
            summary.setdefault(finding.detector, {})
            summary[finding.detector][finding.severity.value] = (
                summary[finding.detector].get(finding.severity.value, 0) + 1
            )
    return summary


async def _probe_privacy_paths(client: httpx.AsyncClient, base_url: str) -> bool:
    for path in ["/privacy", "/privacy-policy", "/policies/privacy"]:
        try:
            response = await client.get(base_url.rstrip("/") + path)
        except httpx.HTTPError:
            continue
        if response.status_code < 400:
            return True
    return False


def _slugify(url: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9]+", "-", url).strip("-")
    return safe[:80] if safe else "page"
