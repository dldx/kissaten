---
type: "Reference"
title: "Aila — Roaster Profile"
description: "Zurich specialty coffee start-up offering origin-led coffees and weekly Saturday fulfilment through a Wix storefront."
---

# Aila — Roaster Profile

## Overview

Aila (also styled AILA Specialty Coffee Culture) is a Zurich, Switzerland
specialty coffee business offering single-origin and decaffeinated coffees. Its
Wix storefront lists filter and espresso categories and describes the business
as a start-up focused on coffee, education and brewing classes. The shop's
current products include coffees from Latin America and Africa.

## Address

- Badenerstrasse 230, CH-8004 Zürich — Switzerland (the site's imprint address; a separate production address is not published).

## Schedules & Shipping

- Orders ship every **Saturday**. Within Switzerland, Swiss Post PostPac rates
  are published as CHF 8.50 Economy or CHF 10.50 Priority for parcels up to 2
  kg; free Swiss shipping starts at **CHF 75**. A coffee-mailer option is free
  for a maximum of two coffee bags. EU and international charges are calculated
  at checkout, with duties and taxes payable on delivery.

## Scraping Quirks

- The scraper treats the Wix shop as two paginated listing pages (`/` and
  `?page=2`), filters sold-out cards before URL filtering, and narrows product
  pages to their `<article>` element for extraction.
- It excludes subscriptions, gift cards, courses, workshops, merchandise,
  equipment and filter papers; extracted currency is pinned to CHF.

## Sources

- https://www.ailacoffee.com
- https://www.ailacoffee.com/about-5
- https://www.ailacoffee.com/contact-8
- https://www.ailacoffee.com/terms-conditions/shipping-policy
