import httpx
import pytest

from gpvb.detect.ads_txt import fetch_ads_txt


@pytest.mark.asyncio
async def test_fetch_ads_txt_counts_lines():
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="# comment\nline1\nline2\n")

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport, base_url="https://example.com") as client:
        status, lines = await fetch_ads_txt(client, "https://example.com")
    assert status == 200
    assert lines == 2
