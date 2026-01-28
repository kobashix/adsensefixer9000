from gpvb.crawl.canonicalize import canonicalize_url


def test_canonicalize_removes_fragment():
    url = "https://example.com/page?x=1#section"
    assert canonicalize_url(url, ignore_querystrings=False) == "https://example.com/page?x=1"


def test_canonicalize_ignores_querystrings():
    url = "https://example.com/page?x=1&y=2"
    assert canonicalize_url(url, ignore_querystrings=True) == "https://example.com/page"
