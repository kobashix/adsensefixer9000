from __future__ import annotations

import asyncio
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from gpvb.models import AdElement


AD_SELECTORS = [
    "iframe[src*='googlesyndication']",
    "iframe[id*='google_ads']",
    "ins.adsbygoogle",
    "[data-ad-client]",
    "[data-ad-slot]",
]


class BrowserPool:
    def __init__(self, concurrency: int, user_agent: str) -> None:
        self._concurrency = concurrency
        self._user_agent = user_agent
        self._browser: Optional[Browser] = None
        self._playwright = None
        self._semaphore = asyncio.Semaphore(concurrency)

    async def __aenter__(self) -> "BrowserPool":
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

    async def new_context(self, viewport: Dict[str, int]) -> BrowserContext:
        if not self._browser:
            raise RuntimeError("Browser not started")
        return await self._browser.new_context(
            viewport=viewport,
            user_agent=self._user_agent,
        )

    async def render_page(
        self,
        url: str,
        viewport: Dict[str, int],
        timeout_ms: int = 30000,
        screenshot_path: Optional[str] = None,
    ) -> Tuple[str, int, str, str, Dict[str, int], List[AdElement], Dict[str, Any]]:
        async with self._semaphore:
            context = await self.new_context(viewport)
            page = await context.new_page()
            requests = Counter()
            page.on(
                "request",
                lambda request: requests.update([request.url.split("/")[2]]),
            )
            response = await page.goto(url, wait_until="networkidle", timeout=timeout_ms)
            status = response.status if response else 0
            headers = response.headers if response else {}
            final_url = page.url
            html = await page.content()
            text = await page.inner_text("body")
            if screenshot_path:
                await page.screenshot(path=screenshot_path, full_page=True)
            ad_elements, extras = await self._collect_ads(page)
            await context.close()
            extras["headers"] = headers
            return final_url, status, html, text, dict(requests), ad_elements, extras

    async def collect_mobile_flags(self, url: str, viewport: Dict[str, int]) -> Dict[str, bool]:
        async with self._semaphore:
            context = await self.new_context(viewport)
            page = await context.new_page()
            await page.goto(url, wait_until="networkidle", timeout=30000)
            flags = await page.evaluate(
                """
                () => {
                  const autoplayAudio = Array.from(document.querySelectorAll('video[autoplay]'))
                    .some((v) => !v.muted);
                  const sticky = Array.from(document.querySelectorAll('*'))
                    .filter((el) => {
                      const style = window.getComputedStyle(el);
                      return style.position === 'fixed' || style.position === 'sticky';
                    })
                    .some((el) => el.getBoundingClientRect().height > window.innerHeight * 0.3);
                  const popups = Array.from(document.querySelectorAll('[role=\"dialog\"], .modal, .popup'))
                    .some((el) => {
                      const r = el.getBoundingClientRect();
                      return r.width * r.height > 0 && window.getComputedStyle(el).display !== 'none';
                    });
                  return {\n                    autoplay_audio: autoplayAudio,\n                    sticky_elements: sticky,\n                    popup_on_load: popups,\n                  };\n                }
                """
            )
            await context.close()
            return flags

    async def _collect_ads(self, page: Page) -> Tuple[List[AdElement], Dict[str, Any]]:
        data = await page.evaluate(
            """
            () => {
              const selectors = %s;
              const ads = [];
              const clickable = Array.from(document.querySelectorAll('a, button, input, select'));
              const navRegion = {x: 0, y: 0, width: window.innerWidth, height: 120};
              const textBlocks = Array.from(document.querySelectorAll('main, article, section, div'))
                .map(el => ({el, text: (el.innerText || '').trim().length}))
                .sort((a, b) => b.text - a.text);
              const primaryContent = textBlocks.length ? textBlocks[0].el : document.body;

              const overlaps = (a, b) => {
                const xOverlap = Math.max(0, Math.min(a.x + a.width, b.x + b.width) - Math.max(a.x, b.x));
                const yOverlap = Math.max(0, Math.min(a.y + a.height, b.y + b.height) - Math.max(a.y, b.y));
                return xOverlap * yOverlap;
              };

              const getRect = (el) => {
                const r = el.getBoundingClientRect();
                return {x: r.x, y: r.y, width: r.width, height: r.height};
              };

              const hasNoindex = !!document.querySelector('meta[name="robots"][content*="noindex" i]');

              selectors.forEach((selector) => {
                document.querySelectorAll(selector).forEach((el) => {
                  const rect = getRect(el);
                  const clickableOverlap = clickable.some((c) => overlaps(rect, getRect(c)) > 0);
                  const navOverlap = overlaps(rect, navRegion) > 0;
                  const contentOverlap = overlaps(rect, getRect(primaryContent)) > 0;
                  ads.push({
                    selector,
                    x: rect.x,
                    y: rect.y,
                    width: rect.width,
                    height: rect.height,
                    overlaps_clickable: clickableOverlap,
                    overlaps_nav: navOverlap,
                    overlaps_content: contentOverlap,
                  });
                });
              });

              const scripts = Array.from(document.querySelectorAll('script'));
              const hasGoogleAdClient = scripts.some((s) => (s.textContent || '').includes('google_ad_client'));

              const overlays = Array.from(document.querySelectorAll('[role="dialog"], .modal, .overlay'))
                .map(getRect)
                .filter((rect) => rect.width * rect.height > window.innerWidth * window.innerHeight * 0.6);

              return {
                ads,
                has_google_ad_client: hasGoogleAdClient,
                has_noindex_meta: hasNoindex,
                overlays,
              };
            }
            """ % AD_SELECTORS
        )
        ads = [AdElement(**item) for item in data["ads"]]
        extras = {
            "has_google_ad_client": data["has_google_ad_client"],
            "has_noindex_meta": data["has_noindex_meta"],
            "overlays": data["overlays"],
        }
        return ads, extras
