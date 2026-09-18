"""Unit tests for Coffee County (shop-pro) canonical URL resolution.

shop-pro product links are query-only (``?pid=...``). ``urljoin`` against the
slash-less base URL produces ``https://shop.coffeecounty.cc?pid=...``, while
Pydantic's ``HttpUrl`` normalization (used for ``CoffeeBean.url``) stores the
canonical ``https://shop.coffeecounty.cc/?pid=...`` form in bean JSON files and
DuckDB. Before the ``resolve_url`` override, the two forms never matched, so
every session treated every in-stock bean as new (full AI re-scrape of the
whole catalogue) and simultaneously marked every known bean out of stock.
"""

import pytest


@pytest.fixture
def scraper(monkeypatch):
    from kissaten import ai as ai_module
    from kissaten.scrapers import coffee_county

    # Avoid constructing a real AI extractor (needs an API key + Agent).
    monkeypatch.setattr(ai_module, "CoffeeDataExtractor", lambda api_key=None: None)
    return coffee_county.CoffeeCountyScraper(api_key="dummy")


class TestResolveUrlCanonicalForm:
    """``resolve_url`` must emit the canonical ``/?pid=`` form for query-only links."""

    def test_query_only_href_gets_canonical_slash(self, scraper):
        assert scraper.resolve_url("?pid=149017079") == "https://shop.coffeecounty.cc/?pid=149017079"

    def test_absolute_no_slash_url_gets_canonical_slash(self, scraper):
        # Hardcoded absolute hrefs in listing HTML keep the same risk.
        assert (
            scraper.resolve_url("https://shop.coffeecounty.cc?pid=149017079")
            == "https://shop.coffeecounty.cc/?pid=149017079"
        )

    def test_canonical_url_with_slash_unchanged(self, scraper):
        assert (
            scraper.resolve_url("https://shop.coffeecounty.cc/?pid=149017079")
            == "https://shop.coffeecounty.cc/?pid=149017079"
        )

    def test_url_with_path_untouched(self, scraper):
        assert (
            scraper.resolve_url("https://shop.coffeecounty.cc/guide?pid=1")
            == "https://shop.coffeecounty.cc/guide?pid=1"
        )

    def test_category_pagination_url_resolved(self, scraper):
        assert (
            scraper.resolve_url("?mode=cate&cbid=1276755&csid=0&page=2")
            == "https://shop.coffeecounty.cc/?mode=cate&cbid=1276755&csid=0&page=2"
        )

    def test_resolved_url_matches_pydantic_normalized_bean_url(self, scraper):
        """Discovered URLs must equal the HttpUrl-normalized form stored on disk/DB."""
        from pydantic import HttpUrl

        resolved = scraper.resolve_url("?pid=192795538")
        normalized = str(HttpUrl("https://shop.coffeecounty.cc?pid=192795538"))
        assert resolved == normalized


class TestHistoryMatching:
    """Discovered URLs must be recognised as already-scraped by history lookup."""

    def test_resolved_url_detected_as_existing(self, scraper):
        stored_url = "https://shop.coffeecounty.cc/?pid=149017079"  # canonical, as stored
        discovered = scraper.resolve_url("?pid=149017079")

        scraper._load_existing_beans_from_all_sessions(_data_dir_with_history(monkeypatch_url=stored_url))
        assert scraper._is_bean_already_scraped_anywhere(discovered) is True

    def test_unknown_url_detected_as_new(self, scraper):
        discovered = scraper.resolve_url("?pid=999999999")
        assert scraper._is_bean_already_scraped_anywhere(discovered) is False


def _data_dir_with_history(monkeypatch_url, tmp_path=None):
    """Build a fake ``data/`` tree containing one stored bean with ``monkeypatch_url``.

    Returns the parent directory to pass as ``output_dir``.
    """
    import json
    import tempfile
    from pathlib import Path

    tmp = Path(tempfile.mkdtemp()) if tmp_path is None else Path(tmp_path)
    session_dir = tmp / "roasters" / "coffee_county" / "20260812"
    session_dir.mkdir(parents=True)
    bean = {"url": monkeypatch_url, "name": "The Ethiopian Roast"}
    (session_dir / "the_ethiopian_roast_010101.json").write_text(json.dumps(bean))
    return tmp
