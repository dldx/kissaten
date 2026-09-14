---
type: "Reference"
title: "Impossible Coffees — Roaster Profile"
description: "Limited-edition 'impossible coffees' project by Delta Coffee House Experience (Delta Cafés / Grupo Nabeiro), Portugal — from the Azores (the first and only Portuguese coffee) to Angola, São Tomé, Colombia and Thailand, with per-edition social-impact commitments."
---

# Impossible Coffees — Roaster Profile

## Overview

Impossible Coffees is a limited-edition rare-coffee project by **Delta Coffee
House Experience** (DCHE), the specialty brand of Delta Cafés / Grupo Nabeiro
in Portugal. The WordPress showcase at impossiblecoffees.com describes it as
an unprecedented project of entrepreneurship and social activism telling the
stories of people who proved that coffee could grow where it was deemed
"impossible" — the result is a set of rare coffees from micro-productions
around the world. There are five editions: Café dos Açores (Portugal's first
and only coffee, from the Azores), Café Amboim (robusta from Angola),
Café Catoninho (São Tomé and Príncipe), Café Colômbia (the Nasa We'sx
indigenous community, Gaitania, Tolima) and Café Toki (forest-grown coffee
from Chiang Mai, Thailand). The pages are storytelling showcases with no
prices — the "COMPRAR" buttons link out to the separate shop at
shop.deltacoffeehouse.com.

## Address

- No production or roasting location is published on the project site. The
  parent group is based in **Campo Maior, Portugal** — per Delta Cafés'
  corporate site, which lists Campo Maior as the company's founding location;
  a full street address is not published on the pages checked.

## Sustainability

- The Toki edition is grown under the canopy of large trees in the Chiang Mai
  forest at over 1,500 m altitude, with the producers' mission explicitly
  framed as preserving the region's ecosystem.
- The Catoninho edition supports Firma Efraim's push for sustainable,
  environmentally respectful practices and the revitalisation of the historic
  Roça Monte Café in São Tomé and Príncipe.

## Sourcing & Transparency

- **Café Amboim (Angola):** 20% of the total sales of this special edition is
  donated to the **Associação das Mulheres Empreendedoras do Cuanza Sul**,
  founded after the civil war (1975–2002) by women who rebuilt plantations of
  the unique Robusta Amboim. The page shows a live fundraising counter —
  "Valor angariado: 23 078.84 €" at the time of checking.
- **Café Colômbia:** 10% of the total sales of this edition reverts to the
  Nasa We'sx indigenous community in Gaitania (Tolima), young producers who
  professionalised through the Young Professional People (Yuppie) project.
- **Café Toki:** 10% of the total sales reverts to Toki and his Karen family
  in Galyani Vadhana (Chiang Mai), to modernise production and offset
  climate-change losses.
- **Café Catoninho:** run with the NGO MOVE, which delivers a training
  programme for local producers; the page lists the São Tomé government,
  OGN MOVE and the Cooperativa Monte Café as partners.
- No FOB or farm-gate prices are published; the editions are sourced through
  named producer families, associations and communities rather than importers.

## Philosophy & Quirks

- The whole concept turns on the word "impossible": coffees from places where
  growing coffee was thought impossible — the Azores blend is billed as "the
  first and only Portuguese coffee".
- The project is open to new producers: a "Candidaturas" (applications) page
  invites anyone who knows or is a specialty producer to apply via form.

## Scraping Quirks

- The site is a WordPress.com storytelling showcase with **no product prices,
  weights or JSON-LD product data**; beans are extracted from the per-coffee
  story pages via AI extraction, and the site's Portuguese content is
  translated during extraction.
- The only € figures on the pages are **fundraising counters** (e.g. the
  Amboim "Valor angariado" total), so the scraper deliberately strips any
  extracted price and pins the currency to EUR — otherwise counters would
  pollute the price fields.
- The real shop lives on a separate JavaScript-rendered domain
  (shop.deltacoffeehouse.com) that this scraper does not touch.
- The showcase pages carry no stock markers, so there is no sold-out
  detection; WordPress.com also rate-limits aggressively (2 s fetch delay).

## Sources

- https://impossiblecoffees.com/
- https://impossiblecoffees.com/o-projeto/
- https://impossiblecoffees.com/os-cafes/
- https://impossiblecoffees.com/cafe-dos-acores/
- https://impossiblecoffees.com/cafe-amboim/
- https://impossiblecoffees.com/cafe-catoninho/
- https://impossiblecoffees.com/cafe-colombia/
- https://impossiblecoffees.com/cafe-toki/
- https://shop.deltacoffeehouse.com/pt/pt/cafes
- https://deltacoffeehouse.com/
- https://www.deltacafes.pt/
