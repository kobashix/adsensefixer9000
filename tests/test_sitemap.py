from gpvb.crawl.sitemap import parse_sitemap


def test_parse_sitemap_urlset():
    xml = """
    <urlset>
      <url><loc>https://example.com/a</loc></url>
      <url><loc>https://example.com/b</loc></url>
    </urlset>
    """
    assert parse_sitemap(xml) == ["https://example.com/a", "https://example.com/b"]


def test_parse_sitemap_index():
    xml = """
    <sitemapindex>
      <sitemap><loc>https://example.com/sitemap-1.xml</loc></sitemap>
    </sitemapindex>
    """
    assert parse_sitemap(xml) == ["https://example.com/sitemap-1.xml"]
