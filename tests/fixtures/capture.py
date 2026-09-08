"""Regenerate the roaster test fixtures from the live sites.

Run from the repo root:

    .venv/bin/python tests/fixtures/capture.py

Written files:
- blackmass_view-all-live-offerings_products.json   (Shopify products.json, trimmed)
- langora_produkter_products.json                   (Shopify products.json, trimmed)
- beberry_kava_category.html                        (WooCommerce category page, cropped to li.product cards)

The fixtures are deliberately *cropped, not synthetic*: they keep exactly the
fields/selectors the scrapers read so a catalogue change (renamed product_type,
new collection membership, moved product, class renames) fails the unit tests
and is visible as a diff. Regenerate and diff to see what changed on the site.

Trims applied:
- Shopify JSON: keeps id/title/handle/product_type/tags, body_html truncated to
  300 chars, variants reduced to title/price/available.
- BeBerry HTML: keeps the ``li.product`` cards as-is, strips ``data-*``
  attributes (embedded variant JSON the scraper never reads at category level)
  and image srcset/src (test asserts classes + anchors only).
"""

from __future__ import annotations

import json
import urllib.request
from pathlib import Path

FIXTURES = Path(__file__).resolve().parent
UA = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
}

SHOPIFY_URLS = {
    "blackmass_view-all-live-offerings_products.json": (
        "https://blackmassroasters.com/collections/view-all-live-offerings/products.json?limit=250"
    ),
    "langora_produkter_products.json": "https://langorakaffe.no/collections/produkter/products.json?limit=250",
}
BEBERRY_URL = "https://www.beberrycoffee.cz/categories/kava/"


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read().decode("utf-8", "replace")


def trim_shopify(raw: str) -> dict:
    data = json.loads(raw)
    products = []
    for p in data.get("products", []):
        body = p.get("body_html") or ""
        products.append(
            {
                "id": p.get("id"),
                "title": p.get("title"),
                "handle": p.get("handle"),
                "product_type": p.get("product_type"),
                "tags": p.get("tags") or [],
                "body_html": body[:300] + ("..." if len(body) > 300 else ""),
                "variants": [
                    {"title": v.get("title"), "price": v.get("price"), "available": v.get("available", False)}
                    for v in (p.get("variants") or [])
                ],
            }
        )
    return {"products": products}


def crop_beberry(html: str) -> str:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "lxml")
    cards = soup.select("li.product")
    for card in cards:
        for img in card.find_all("img"):
            img.attrs = {"alt": img.get("alt", "")}
        for el in card.find_all(True):
            el.attrs = {k: v for k, v in (el.attrs or {}).items() if not k.startswith("data-")}
    cards_html = "".join(str(c) for c in cards)
    return (
        '<html><head><meta charset="utf-8"></head><body>'
        f'<ul class="products">{cards_html}</ul></body></html>'
    )


def main() -> None:
    for name, url in SHOPIFY_URLS.items():
        payload = trim_shopify(fetch(url))
        (FIXTURES / name).write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n")
        print(f"wrote {name} ({len(payload['products'])} products)")
    (FIXTURES / "beberry_kava_category.html").write_text(crop_beberry(fetch(BEBERRY_URL)))
    print("wrote beberry_kava_category.html")


if __name__ == "__main__":
    main()
