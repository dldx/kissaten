"""Tests for the Naughty Dog scraper's article/modal parsing."""

from pathlib import Path

from bs4 import BeautifulSoup

from kissaten.scrapers.naughty_dog import NaughtyDogScraper

FIXTURE = Path(__file__).parent.parent / "fixtures" / "naughty_dog_page.html"


def _parse_fixture(scraper: NaughtyDogScraper):
    soup = BeautifulSoup(FIXTURE.read_text(encoding="utf-8"), "lxml")
    articles = soup.select("article.portfolio-item")
    beans = [b for art in articles if (b := scraper._parse_article(soup, art))]
    return beans, len(articles)


def test_parses_articles_from_current_dom():
    """The live DOM uses id-based data-bs-target (#coffee-modal-N); all articles must parse."""
    scraper = NaughtyDogScraper(output_dir="data")
    beans, article_count = _parse_fixture(scraper)
    assert article_count == 4
    assert len(beans) == article_count


def test_single_origin_bean_fields():
    scraper = NaughtyDogScraper(output_dir="data")
    beans, _ = _parse_fixture(scraper)
    by_name = {b.name: b for b in beans}

    bean = by_name["Autumn Negele Gorbitu"]
    assert bean.roaster == "The Naughty Dog"
    assert bean.currency == "CZK"
    assert bean.is_single_origin is True
    assert len(bean.origins) == 1
    origin = bean.origins[0]
    assert origin.country == "ET"
    assert origin.process == "natural"
    assert origin.variety and "Dega" in origin.variety
    assert origin.elevation_min == 1995
    assert origin.harvest_date is not None
    assert bean.tasting_notes
    assert bean.image_url is not None
    assert str(bean.url).startswith("https://www.thenaughtydog.cz/#")  # HttpUrl adds / before fragment


def test_modal_details_extracted():
    scraper = NaughtyDogScraper(output_dir="data")
    beans, _ = _parse_fixture(scraper)
    by_name = {b.name: b for b in beans}

    # Blend: modal origin contains two countries -> two origin entries
    blend = by_name["Christmas Coffee"]
    assert blend.is_single_origin is False
    assert [o.country for o in blend.origins] == ["CO", "ET"]
    assert blend.roast_profile == "Omni"

    # Decaf flag comes from the name; usage "special edition" maps to no roast profile
    decaf = by_name["El Paraiso Yn09 Decaf"]
    assert decaf.is_decaf is True
    assert decaf.roast_profile is None


def test_weight_from_variant_sizes():
    """Packaging table row is gone; weight now comes from .coffee-detail-variant-size spans."""
    scraper = NaughtyDogScraper(output_dir="data")
    beans, _ = _parse_fixture(scraper)
    by_name = {b.name: b for b in beans}

    # Christmas Coffee lists 200g / 1000g variants -> first is 200g
    assert by_name["Christmas Coffee"].weight == 200
    # Christmas Tasting Box lists 4x30g -> total 120g
    assert by_name["Christmas Tasting Box"].weight == 120


def test_weight_helpers():
    scraper = NaughtyDogScraper(output_dir="data")
    assert scraper._first_weight("250g bags") == 250
    assert scraper._first_weight("") is None
    assert scraper._weight_from_variants(None) is None
