from gpvb.detect.text import cluster_simhash


def test_cluster_simhash_groups_similar():
    urls = ["https://a", "https://b", "https://c"]
    texts = [
        "hello world this is similar",
        "hello world this is similar content",
        "completely different text",
    ]
    clusters = cluster_simhash(urls, texts, threshold=0.8)
    assert clusters
    grouped_urls = clusters[0][0]
    assert "https://a" in grouped_urls
    assert "https://b" in grouped_urls
