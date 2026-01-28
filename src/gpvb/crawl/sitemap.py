from __future__ import annotations

from typing import Iterable, List
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup


async def fetch_sitemap_urls(client: httpx.AsyncClient, base_url: str) -> List[str]:
    candidates = [
        "/sitemap.xml",
        "/sitemap_index.xml",
        "/sitemap_post.xml",
        "/sitemap_page.xml",
    ]
    urls: List[str] = []
    for path in candidates:
        sitemap_url = urljoin(base_url, path)
        try:
            response = await client.get(sitemap_url)
            response.raise_for_status()
        except httpx.HTTPError:
            continue
        urls.extend(parse_sitemap(response.text))
    return list(dict.fromkeys(urls))


def parse_sitemap(xml_text: str) -> List[str]:
    soup = BeautifulSoup(xml_text, "xml")
    if soup.find("sitemapindex"):
        urls = []
        for sitemap in soup.find_all("sitemap"):
            loc = sitemap.find("loc")
            if loc and loc.text:
                urls.append(loc.text.strip())
        return urls
    urls = []
    for url in soup.find_all("url"):
        loc = url.find("loc")
        if loc and loc.text:
            urls.append(loc.text.strip())
    return urls


async def expand_sitemaps(client: httpx.AsyncClient, base_url: str) -> List[str]:
    seeds = await fetch_sitemap_urls(client, base_url)
    if not seeds:
        return []
    final_urls: List[str] = []
    for entry in seeds:
        if entry.endswith(".xml"):
            try:
                response = await client.get(entry)
                response.raise_for_status()
            except httpx.HTTPError:
                continue
            final_urls.extend(parse_sitemap(response.text))
        else:
            final_urls.append(entry)
    return list(dict.fromkeys(final_urls))


def extract_links(html: str, base_url: str) -> Iterable[str]:
    soup = BeautifulSoup(html, "lxml")
    for link in soup.select("a[href]"):
        href = link.get("href")
        if not href:
            continue
        if href.startswith("mailto:") or href.startswith("tel:"):
            continue
        yield urljoin(base_url, href)
