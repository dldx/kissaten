---
type: "Reference"
title: "Flames Coffee — Roaster Profile"
description: "Ukrainian specialty coffee roaster whose catalogue is protected by a JavaScript proof-of-work challenge and served in UAH."
---

# Flames Coffee — Roaster Profile

## Overview

Flames Coffee is a specialty coffee roaster based in Ukraine. Its registered
storefront is `flames.com.ua`, with coffee-filter and coffee-espresso catalogue
pages and prices normalised to UAH. The scraper translates extracted product
content to English for the catalogue; the site did not expose a reliable
roastery street address, equipment specification or published shipping policy
in the pages fetched for this profile.

## Address

- Ukraine — city and full roastery address not published on site.

## Scraping Quirks

- The site uses a JavaScript proof-of-work challenge. The scraper waits for the
  `challenge_passed` cookie and page reload before returning the catalogue HTML.
- Two catalogue URLs are used: the all-size filter-coffee page and the
  all-size espresso page. A third infuse-coffee URL is present only as a
  commented-out source in the scraper.
- Extracted beans are post-processed with currency forced to `UAH` and
  translation enabled.

## Sources

- https://flames.com.ua
- https://flames.com.ua/coffee-filter/filter/fasovka=1,2,5,8;page=all/
- https://flames.com.ua/coffee-espresso/filter/fasovka=1,2,5,8;page=all/
