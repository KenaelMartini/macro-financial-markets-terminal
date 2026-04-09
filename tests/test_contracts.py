from terminal_app.normalization.contracts import NewsArticle


def test_news_article_contract():
    row = NewsArticle(
        title="t",
        url="https://x.test",
        source="src",
        published_utc="2026-01-01T00:00:00+00:00",
    )
    assert row.title == "t"
    assert row.url.startswith("https://")
