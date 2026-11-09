---
type: "Reference"
title: "Acid Coffee — Roaster Profile"
description: "Shibuya, Tokyo specialty roaster selling super-fruity single origins in a quality-tier × process matrix, with a large drip-bag line and worldwide shipping."
---

# Acid Coffee — Roaster Profile

## Overview

Acid Coffee is a specialty coffee brand from Shibuya, Tokyo, built entirely around what it calls super-fruity coffee (スーパーフルーティ) — the homepage promises 「スーパーフルーティなコーヒーをご自宅で」 and the about page 「目覚めよ、スーパーフルーティ!!」. It is run by Kenta Tsukada (塚田健太), who also runs Coffee Bar Gallage and describes having run a Shibuya coffee stand before moving to Yoyogi-Uehara. Alongside the online shop it sells beans wholesale (「コーヒー豆の卸販売も行っております」, contact 担当：塚田). Freshness is the explicit pitch: beans are sold 「飲み頃(焙煎日より１ヶ月半以内の)」 — at their peak, within about a month and a half of roasting — with 「焙煎から2ヶ月がとびきり旨いです」 as the follow-up claim.

## Address

- Roastery / headquarters address: **not published**. No legal entity name (株式会社◯◯), corporate number or founding year could be verified either.
- The only address on the about page is 「住所：東京都渋谷区上原1-29-5」, labelled nothing more than 「住所」 — not 焙煎所 / ロースタリー / 本社 — so it reads as a public shop location in Shibuya-ku, Tokyo, Japan rather than a confirmed roasting site.
- The legally required disclosure page (特定商取引法) shows a different address, 〒150-0011 東京都渋谷区東3丁目16番3号 エフ・ニッセイ恵比寿ビル4階, but that page states 「※所在地・電話番号には、STORES を運営する STORES 株式会社 の情報が表示されています。」 — it is the storefront platform operator's address, not Acid Coffee's, and must not be recorded as a roastery address.

## Sourcing & Transparency

- No price transparency of any kind: no FOB or farm-gate figures, purchase volumes, importer names or direct-trade claims.
- Producer-level detail is strong instead. The catalogue is heavily single-origin with named farms, estates, producers and lots — Kenya Ngacha Estate Auction Lot, Panama Janson, Panama Chevas, Panama Flying Pumas, Colombia Las Flores Competition Lot, Colombia Aroma Nativo, Nicaragua Los Cipreses, Panama Garrido, Casa Abajo — and titles use lot language such as Competition Lot, Auction Lot, BOP, Geisha, Pink Bourbon, Sidra, Eugenoides and Sudan Rume.
- Product pages publish origin, process, variety and altitude in a consistent labelled block; the Kenya Ngacha lot, for example, carries `-PROCESS- Anaerobic Washed`, `-VARIETY- SL28, SL34`, `-ALTITUDE- 1680m`.

## Roasting & Equipment

- No roasting machine is published: no brand or model, no drum-versus-hot-air statement, no capacity, no roast profiles and no cupping protocol on the pages checked. What is verifiable is a freshness position rather than hardware — beans are offered at their 「飲み頃」 peak, roughly a month and a half after roasting — with super-fruity cup character claimed across the range.

## Schedules & Shipping

- Dispatch: 「オーダーから1週間以内に発送します。在庫あるものは即日発送！」 — everything ships within a week of ordering, in-stock items the same day. A more specific notice sets the order cutoff at Tuesday/Thursday 18:00 with Wednesday/Friday Click Post dispatch (「発送は、火木曜日18:00締め 水金曜日クリックポストで発送します。」), and the legal disclosure repeats the seven-day commitment.
- Domestic shipping is ¥550, with no free-shipping threshold set in the storefront configuration.
- Overseas shipping is enabled, with per-country rates shown on product pages: China and Taiwan ¥2,800; Indonesia, Philippines, Singapore and Thailand ¥3,850; Australia and Canada ¥5,550; United States, Colombia and other destinations ¥6,600. The rates come from the storefront's own shipping configuration and may be item- or platform-dependent.

## Philosophy & Quirks

- The catalogue is organised as a quality tier × process matrix rather than by roast level. Four tiers — `Awesome!!!! 〜至高〜`, `Confidence!!! 〜めっちゃ良いやつ〜`, `Innovative!! 〜ちょっと良いやつ〜`, `Daily! 〜初めての方も〜` — are each subdivided into Washed / Natural / Honey / Anaerobic / その他特殊プロセス, alongside a `Country Sort 〜国別〜` section and standalone Geisha, unusual-variety, decaf and drip-bag categories. The tier names are written for the customer rather than the trade: even `Daily! 〜初めての方も〜` ("for people trying it for the first time") is an inviting way into the top of the range.
- Drip bags are a real product line, not an add-on — 「ACID COFFEEがお送りするスーパーフルーティな『本気の』ドリップバッグ」 — sold with emphatic freezer guidance (「【要冷凍！！！】」「冷凍庫に入れてくれ！何ヶ月でも持つぞ！！！」) in formats from one random bag (¥300) to a 5-bag variety pack (¥1,500), a 5-bag premium set (¥2,500), a 12-bag set (¥5,000) and origin-specific 10-bag sets (¥2,700). Marketed for home, office, travel, outdoor use and gifting.
- Taglines include 「日常に感動があればいいなぁ。」 and 「『これから渋谷に素敵なコーヒー文化を作る』」 — the latter stating an aim to build a good coffee culture in Shibuya.

## Scraping Quirks

- The storefront is not Shopify and has no public read JSON API: `products.json`, `/collections/all/products.json`, `sitemap_products_1.xml` and WooCommerce-style `/wp-json/...` all 404, and `/?format=json` returns 406. It is server-rendered, so product data must come from the HTML — a `products.json`-shaped scraper here produces a silent empty scrape.
- Cloudflare blocks plain curl with a 403, and it also rejects the Web Bot Auth signature headers: adding `Signature-Agent` alone is enough to trigger the 403. Use the impersonation client rebuild *without* `WebBotAuth`, unlike the other scrapers in this repo that attach it.
- Walking categories double-counts — the four merch items are reachable from both `Others` and `Goods` — so the sitemap is the only clean enumeration source.
- The `Goods` breadcrumb is the only reliable non-coffee signal. An English-only name blocklist catches `Dripper` but misses サブスクリプション (subscription), Tシャツ (t-shirt) and マグ (mug).
- Titles carry promotional prefixes and status labels that the item page's own structured-data name lacks: 【ラストバッチ！】, 【ニュークロップ再入荷】, 【ゲリラ入荷】, 【デッドストック】, plus `new`, `hot`, `SOLD OUT`. Read the name from structured data and treat those suffixes as unreliable.
- Sizes are a wide ladder (16 g / 32 g / 100 g / 200 g / 300 g / 500 g on a typical product) and prices are a non-linear range rather than a per-100 g figure — the 16 g and 32 g tiers are drip-bag sample sizes. Prices are tax-inclusive (税込).
- Catalogue typos are baked into titles and category names — `Ethopia`, `Geisa`, `NICARAGA` — so exact country-string matching is unreliable.

## Sources

- https://acidcoffee.stores.jp/
- https://acidcoffee.stores.jp/about
- https://acidcoffee.stores.jp/tokushoho
- https://acidcoffee.stores.jp/items/6ab7caf4b21f830e5fc42c9a
- https://acidcoffee.stores.jp/items/66d264169d7c8c2a512cfc72
- https://note.com/acid_coffee
- https://x.com/acidcoffee