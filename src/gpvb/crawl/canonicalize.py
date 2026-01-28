from __future__ import annotations

from urllib.parse import urlparse, urlunparse


def canonicalize_url(url: str, ignore_querystrings: bool) -> str:
    parsed = urlparse(url)
    path = parsed.path or "/"
    query = "" if ignore_querystrings else parsed.query
    fragment = ""
    normalized = parsed._replace(path=path, query=query, fragment=fragment)
    return urlunparse(normalized)
