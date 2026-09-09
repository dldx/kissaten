---
type: "Reference"
title: "Juu Coffee — Roaster Profile"
description: "Nairobi coffee processing company (founded 2010 per their site) trading Kenyan Arabica, Robusta, Excelsa and Liberica from a brochure-style WordPress site with no online checkout — orders go through phone, email and bank transfer."
---

# Juu Coffee — Roaster Profile

## Overview

Juu Coffee (styled **JUU COFFEE**) is a coffee processing company headquartered in
Nairobi, Kenya, which per their site was founded in **2010** and is led by CEO
**Ruth Nyambura** (the homepage hero simultaneously claims "Getting It Right
Since 2019" — the site is inconsistent on the founding year). It sells a tiny,
flat catalogue of four products — **Arabica**, **Original Robusta**,
**Original Excelsa** and **Original Liberica** — shown with pack shots for
100 g / 250 g / 500 g / 1 kg and priced in **US dollars ($9.75 each on the
products page)**. The website is not an e-commerce store: it is a
WordPress + Elementor brochure site where every "order now" button is a
placeholder link, and the contact page says "Kindly contact us for bank
details" for payment — ordering happens by phone/email rather than a cart.

## Address

- P.O. Box 13586-00100, Nairobi, Kenya (listed as "JUU COFFEE PROCESSING") — no street address published on site

## Philosophy & Quirks

- Taglines: "Freshly roasted, lovingly brewed" and "Have you tasted the best
  coffee in Africa?" — the marketing leans heavily on Kenya's reputation for
  bright, fruity, floral coffee from the Mount Kenya highlands (Nyeri,
  Kirinyaga and Muranga are name-checked on the products page).
- The company calls itself a coffee *processing* company rather than a
  roastery, describing a team of "coffee professionals" covering sourcing,
  processing and roasting (per their site).
- The team page shows Ruth Nyambura (CEO), Caroline Kinyanjui and Stephen
  Ikeda; the site's testimonial section is still lorem-ipsum placeholder text,
  so the storefront reads as an early-stage brochure.
- Contact: +254 721 923 558, info@juu.co.ke; payment is by bank transfer
  arranged over phone/email.

## Scraping Quirks

- **No per-product pages exist.** The whole catalogue is one static Elementor
  page (`/products/`) whose product cards have no hrefs. The scraper parses
  the cards (h4 name + h5 price) and synthesises stable per-product URLs with
  fragments (`https://juu.co.ke/products/#<slug>`), serving the cached card
  HTML to the AI extractor instead of refetching.
- **Currency is USD, not KES.** Despite being Kenyan, all prices are displayed
  with a "$" sign; the scraper pins `currency="USD"`.
- **Aggressive rate limiting.** The site sits behind Imunify360 and returns
  429s (or a "Rate limit exceeded" page) even minutes between requests; the
  scraper uses a 10 s delay, 4 retries with backoff, and records a failed
  listing fetch so stock updates are suppressed rather than wiping the
  history.
- All four products are genuine coffee; no tasting-kit/sampler filtering is
  needed — the catalogue contains nothing but beans.

## Sources

- https://juu.co.ke/
- https://juu.co.ke/about-us/
- https://juu.co.ke/products/
- https://juu.co.ke/contactus/
