from pathlib import Path


def test_fixture_contains_ad_selectors():
    html = Path("tests/fixtures/ad_page.html").read_text(encoding="utf-8")
    assert "adsbygoogle" in html
    assert "googlesyndication" in html
    assert "google_ad_client" in html
