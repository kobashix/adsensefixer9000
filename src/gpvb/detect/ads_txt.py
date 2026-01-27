from __future__ import annotations

from typing import Tuple
from urllib.parse import urljoin

import httpx


async def fetch_ads_txt(client: httpx.AsyncClient, base_url: str) -> Tuple[int, int]:
    ads_url = urljoin(base_url, "/ads.txt")
    try:
        response = await client.get(ads_url)
    except httpx.HTTPError:
        return 0, 0
    status = response.status_code
    lines = [line for line in response.text.splitlines() if line.strip() and not line.strip().startswith("#")]
    return status, len(lines)
