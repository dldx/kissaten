"""Unit tests for the Bluebird scraper's product-page soup pruning.

The scraper sends ``str(soup)`` to the AI extractor, so
``BluebirdCoffeeScraper.preprocess_product_soup`` must narrow the Elementor
megapage (summary, spec table, description) and drop the ~100 KB
related-products carousel plus the per-product boilerplate sections without
losing the bean facts the extractor needs.
"""

from bs4 import BeautifulSoup

from kissaten.scrapers.bluebird_coffee import BluebirdCoffeeScraper


def _make_scraper() -> BluebirdCoffeeScraper:
    # api_key is only stored on the extractor; no network is touched here.
    return BluebirdCoffeeScraper(api_key="test-api-key")


def _elementor_page() -> str:
    """Build a minimal page mirroring Bluebird's Elementor product layout.

    The real template has 8 top-level sections: three product-specific ones
    (summary, spec table, description) followed by static boilerplate
    (recipe, "Coffee at its best", FAQ, "Subscribe, and save") and the
    related-products carousel.
    """

    def sec(cls: str, body: str) -> str:
        return f"<section class=\"{cls}\">{body}</section>"

    summary = (
        "<div class=\"elementor-widget-container\">"
        "<h2 class=\"elementor-heading-title\">Inmaculada Fellow Farms Geisha</h2>"
        '<p class="price"><span class="woocommerce-Price-amount"><bdi><span>R</span>'
        "284.00</bdi></span> - <span class=\"woocommerce-Price-amount\"><bdi>"
        "<span>R</span>560.00</bdi></span></p>"
        "<p>Raspberry, clementine, white grape 🍇</p>"
        "<form class=\"cart\"><select name=\"attribute_pa_bag-size\">"
        "<option>Choose an option</option><option>100g</option><option>250g</option></select>"
        "<button type=\"submit\">Add to cart</button>"
        '<input type="hidden" name="nonce" value="abc"/></form>'
        "</div>"
    )
    spec_table = (
        "<ul><li><span>Origin:</span> Colombia</li><li><span>Variety:</span> Geisha</li>"
        "<li><span>Altitude:</span> 1700 masl</li>"
        "<li><span>Processing:</span> Anaerobic Natural</li></ul>"
    )
    description = "<p>Coffee Origins One of the most famous producing farms...</p>"
    recipe = (
        "<p>Recipe April Plastic Brewer (you can use any flat bottom brewer) "
        'Kalita 185 filter 93c water 20g coffee... <a href="/grind-guide/">'
        "View our Grind Setting Guide here</a></p>"
    )
    best = "<p>Coffee at its best Freshly roasted beans make great coffee...</p>"
    faq = "<p>FAQs What is the best brew method for each coffee? Single origins: ...</p>"
    subscribe = "<p>Subscribe, and save If you love our coffee, consider signing up...</p>"
    related = (
        '<div class="related products"><h2>More coffees you may enjoy</h2>'
        '<div class="product"><a href="/product/las-margaritas-yellow-bourbon/">'
        "Colombia Las Margaritas Yellow Bourbon R269 Yellow plum & pineapple 🍍</a></div>"
        '<div class="product"><a href="/product/karogoto-aa/">'
        "Kenya Karogoto AA R299 Lemon sorbet, peach 🍑</a></div></div>"
    )
    return (
        "<html><head><title>t</title><style>body{}</style></head><body>"
        '<div class="elementor elementor-19404 elementor-location-single product" '
        'data-elementor-type="product">'
        + sec("elementor-element-aaaa", summary)
        + sec("elementor-element-bbbb", spec_table)
        + sec("elementor-element-cccc", description)
        + sec("elementor-element-dddd", recipe)
        + sec("elementor-element-eeee", best)
        + sec("elementor-element-ffff", faq)
        + sec("elementor-element-1111", subscribe)
        + sec("elementor-element-2222", related)
        + "</div></body></html>"
    )


def test_preprocess_keeps_product_sections_and_drops_noise():
    scraper = _make_scraper()
    pruned = scraper.preprocess_product_soup(BeautifulSoup(_elementor_page(), "lxml"))
    text = pruned.get_text(" ", strip=True)

    # Product facts survive.
    assert "Inmaculada Fellow Farms Geisha" in text
    assert "284.00" in text and "560.00" in text
    assert "Raspberry, clementine, white grape" in text
    assert "Origin:" in text and "Variety:" in text
    assert "1700 masl" in text and "Anaerobic Natural" in text
    assert "Add to cart" in text  # availability cue must not be stripped

    # Boilerplate and the related carousel are gone.
    assert "More coffees you may enjoy" not in text
    assert "Las Margaritas Yellow Bourbon R269" not in text
    assert "Subscribe, and save" not in text
    assert "FAQs What is the best brew method" not in text
    assert "Coffee at its best" not in text
    assert "Recipe April Plastic Brewer" not in text

    # Exactly the 3 product-specific sections are kept.
    kept = pruned.select("body > section")
    assert len(kept) == 3


def test_preprocess_strips_markup_noise():
    scraper = _make_scraper()
    pruned = scraper.preprocess_product_soup(BeautifulSoup(_elementor_page(), "lxml"))
    html = str(pruned)

    # Scripts, styles, form inputs and attributes are removed.
    assert "<script" not in html and "<style" not in html
    assert "<input" not in html
    assert "elementor-element-aaaa" not in html
    assert "data-elementor-type" not in html
    assert "woocommerce-Price-amount" not in html  # classes stripped, text kept


def test_preprocess_fallback_to_woocommerce_product():
    scraper = _make_scraper()
    html = (
        '<html><body><div class="product"><div class="summary entry-summary">'
        "<p>Fake Coffee R 100</p></div>"
        '<div class="related products"><a href="/product/other/">Other product</a></div>'
        "</div></body></html>"
    )
    pruned = scraper.preprocess_product_soup(BeautifulSoup(html, "lxml"))
    text = pruned.get_text(" ", strip=True)
    assert text == "Fake Coffee R 100"


def test_preprocess_falls_back_to_full_page_without_product_container():
    scraper = _make_scraper()
    html = "<html><body><p>not a product page</p></body></html>"
    soup = BeautifulSoup(html, "lxml")
    assert str(scraper.preprocess_product_soup(soup)) == str(soup)
