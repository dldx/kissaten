"""
Generate Beanconqueror share-link URLs from a kissaten ``APICoffeeBean``.

Beanconqueror (the Android/iOS app) shares a coffee bean by encoding it as a
proto3 ``BeanProto`` message, base64-encoding the bytes, and chunking the
result into 400-char ``shareUserBeanN`` URL parameters under
``https://beanconqueror.com?...``. On receipt, the app concatenates the chunks,
decodes the base64, and reconstructs the proto.

The wire format is defined by ``Beanconqueror/src/classes/bean/bean.proto``;
this module uses a protoc-generated Python module (``bean_pb2``) compiled from
that ``.proto`` file.

Public entry points
-------------------

- ``build_share_link(bean, base_url="https://beanconqueror.com", target_currency="USD") -> str`` —
  full URL ready to drop into a QR code or share sheet.
- ``encode_bean_to_proto_bytes(bean, target_currency="USD") -> bytes`` — the raw protobuf payload
  (useful for tests / round-trip checks).

Both helpers accept an optional ``target_currency`` (default ``"USD"``) — the price is
converted to that currency and stored in the ``cost`` field of the Beanconqueror proto
as a whole-unit integer. Note that ``cost`` is ``uint64`` in the Beanconqueror schema
(``Beanconqueror/src/classes/bean/bean.proto``), so sub-unit precision (e.g. the
``.23`` in ``15.23``) is truncated on the wire — exactly as it is in the official
Beanconqueror app. Pass any ISO currency code (``"EUR"``, ``"GBP"``, ``"JPY"``, ...)
to embed the price in the user's own currency instead of USD.
"""

from __future__ import annotations

import base64
from collections.abc import Iterable
from urllib.parse import quote as _urlquote

from kissaten.api.proto import bean_pb2
from kissaten.schemas.api_models import APICoffeeBean, TastingNote

# Re-export for tests that import internal types.
_BeanProto = bean_pb2.BeanProto
_BeanInformation = bean_pb2.BeanInformation


# ---------------------------------------------------------------------------
# Field-mapping helpers
# ---------------------------------------------------------------------------

# Kissaten roast levels (6 buckets) → Beanconqueror Roast enum ints.
# This is a best-effort mapping; the proto only carries a small set of named
# roast profiles so we pick the closest one.
_ROAST_LEVEL_TO_PROTO: dict[str, int] = {
    "Extra-Light": 1,    # CINNAMON_ROAST
    "Light": 2,          # AMERICAN_ROAST
    "Medium-Light": 7,   # CITY_PLUS_ROAST
    "Medium": 8,         # FULL_CITY_ROAST
    "Medium-Dark": 9,    # FULL_CITY_PLUS_ROAST
    "Dark": 12,          # FRENCH_ROAST
}

_ROAST_PROFILE_TO_PROTO: dict[str, int] = {
    "Filter": 1,
    "Espresso": 2,
    "Omni": 3,
    "Both": 3,           # Beanconqueror's OMNI covers "both" in the kissaten sense
}


def _tasting_note_to_string(note: TastingNote | str) -> str | None:
    if isinstance(note, TastingNote):
        return note.note
    if isinstance(note, str):
        return note
    return None


def _normalize_currency(currency: str | None) -> str:
    if not currency:
        return ""
    return currency.upper()


def _convert_to_target_currency(
    price: float | None,
    currency: str | None,
    target_currency: str,
    conn,
    convert_price,
) -> int | None:
    """Convert a price to ``target_currency`` as an integer.

    Returns ``None`` when no conversion is possible (no price, unknown source
    currency, or FX helper missing/returns ``None``).

    Note: the Beanconqueror ``cost`` field is ``uint64``, so the value must
    fit in an integer. We send the whole-unit price in the target currency
    (no cents scaling — Beanconqueror's own JavaScript class stores ``cost``
    as ``number`` and the on-the-wire uint64 truncates any sub-unit portion
    on share). For example, ``15.23 EUR`` → ``15``.
    """
    if price is None or price <= 0:
        return None
    source = _normalize_currency(currency)
    if not source:
        return None
    target = _normalize_currency(target_currency) or "USD"
    if source != target:
        if convert_price is None:
            return None
        converted = convert_price(conn, price, source, target)
        if converted is None:
            return None
        price = converted
    return int(round(price))


def _format_elevation(min_elev: int, max_elev: int) -> str | None:
    """Match Beanconqueror's free-form elevation string."""
    if min_elev <= 0 and max_elev <= 0:
        return None
    if min_elev <= 0:
        return str(max_elev)
    if max_elev <= 0 or max_elev == min_elev:
        return str(min_elev)
    if max_elev < min_elev:
        min_elev, max_elev = max_elev, min_elev
    return f"{min_elev}-{max_elev}"


def _bean_information_from_origin(origin) -> _BeanInformation:
    """Build a BeanInformation proto message from one kissaten APIBean origin."""
    info = _BeanInformation()
    # Use the full country name when available; fall back to the two-letter
    # code for origins that only have a code populated.
    if origin.country_full_name:
        info.country = origin.country_full_name
    elif origin.country:
        info.country = origin.country
    if origin.region:
        info.region = origin.region
    if origin.farm:
        info.farm = origin.farm
    if origin.producer:
        info.farmer = origin.producer
    elevation = _format_elevation(origin.elevation_min, origin.elevation_max)
    if elevation:
        info.elevation = elevation
    if origin.variety:
        info.variety = origin.variety
    if origin.process:
        info.processing = origin.process
    if origin.harvest_date:
        info.harvest_time = origin.harvest_date.isoformat()
    return info


def _weight_from_bean(bean: APICoffeeBean) -> int | None:
    """Pick a single weight in grams from the bean's price options."""
    if bean.weight is not None and bean.weight > 0:
        return int(bean.weight)
    if bean.price_options:
        for option in bean.price_options:
            if option.weight and option.weight > 0:
                return int(option.weight)
        return None
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def encode_bean_to_proto_bytes(
    bean: APICoffeeBean,
    *,
    conn=None,
    convert_price=None,
    target_currency: str = "USD",
    kissaten_url: str | None = None,
) -> bytes:
    """Encode a kissaten ``APICoffeeBean`` as Beanconqueror ``BeanProto`` bytes.

    Parameters
    ----------
    bean:
        The bean to encode.
    conn:
        Optional DuckDB connection. Required when ``convert_price`` is supplied
        because the FX helper needs to look up exchange rates.
    convert_price:
        Optional ``convert_price(conn, amount, from_currency, to_currency)``
        callable. When supplied, ``bean.price`` is converted to ``target_currency``
        and stored as a whole-unit integer in the ``cost`` field (no cents
        scaling; the Beanconqueror ``cost`` field is ``uint64`` and the
        official app truncates sub-unit precision on share). When omitted,
        ``cost`` is left unset.
    target_currency:
        ISO currency code the ``cost`` field should be denominated in. Defaults
        to ``"USD"`` for backwards compatibility. Ignored when ``convert_price``
        is ``None`` and the bean's own currency differs from the target.
    """
    msg = _BeanProto()

    if bean.name:
        msg.name = bean.name
    if bean.roaster:
        msg.roaster = bean.roaster
    if bean.url:
        msg.url = str(bean.url)
    # Back-reference to the Kissaten bean page. The Beanconqueror app's ``note``
    # field surfaces inside the bean's notes screen, so embedding a deep-link
    # to the full roaster page (description, photos, all price options) gives
    # the user a one-click jump back to Kissaten for the rich data we don't
    # cram into the share payload.
    if kissaten_url:
        msg.note = f"Bean details on Kissaten: {kissaten_url}"
    else:
        msg.note = ""

    # Tasting notes → aromatics string. We only populate the free-text
    # ``aromatics`` field (comma-separated) and leave ``cupped_flavor`` empty,
    # matching the working reference links. Beanconqueror's import flow
    # initializes an empty IFlavor on its own.
    custom_flavors: list[str] = []
    if bean.tasting_notes:
        for note in bean.tasting_notes:
            text = _tasting_note_to_string(note)
            if text:
                custom_flavors.append(text)
    if custom_flavors:
        msg.aromatics = ", ".join(custom_flavors)

    # Weight (grams).
    weight = _weight_from_bean(bean)
    if weight is not None:
        msg.weight = weight

    # Cost in target_currency (USD by default). Stored as a whole-unit integer —
    # no cents scaling. The Beanconqueror ``cost`` field is ``uint64`` (see
    # ``Beanconqueror/src/classes/bean/bean.proto``), so any sub-unit precision
    # is truncated by the wire format, exactly as it is in the official app.
    if bean.price is not None:
        units = _convert_to_target_currency(
            bean.price, bean.currency, target_currency, conn, convert_price
        )
        if units is not None:
            msg.cost = units

    # Cupping score → cupping_points string (Beanconqueror stores as string).
    # Always present (empty string when unknown) to match the app encoder.
    msg.cupping_points = str(bean.cupping_score) if bean.cupping_score is not None else ""

    # Booleans & enums — explicit defaults to mirror the TS sanitizer.
    # ``decaffeinated`` is always emitted (proto3 presence) so the decoder
    # never sees ``undefined``.
    msg.decaffeinated = bool(bean.is_decaf)

    if bean.roast_level and bean.roast_level in _ROAST_LEVEL_TO_PROTO:
        msg.roast = _ROAST_LEVEL_TO_PROTO[bean.roast_level]
    else:
        msg.roast = 0  # UNKNOWN_ROAST

    if bean.is_single_origin is False:
        msg.beanMix = 2  # BLEND
    elif bean.is_single_origin is True and len(bean.origins) <= 1:
        msg.beanMix = 1  # SINGLE_ORIGIN
    else:
        msg.beanMix = 2  # BLEND

    if bean.roast_profile and bean.roast_profile in _ROAST_PROFILE_TO_PROTO:
        msg.bean_roasting_type = _ROAST_PROFILE_TO_PROTO[bean.roast_profile]
    else:
        msg.bean_roasting_type = 0  # UNKNOWN_BEAN_ROASTING_TYPE

    # bean_information — one entry per origin (Beanconqueror proto supports this).
    for origin in bean.origins:
        msg.bean_information.append(_bean_information_from_origin(origin))

    # Explicit defaults — mirrors Beanconqueror's own sanitizer that strips
    # user-private fields before sharing. With proto3 ``optional`` fields,
    # setting these explicitly ensures they appear on the wire (presence = true)
    # so the Beanconqueror decoder sees defined values rather than ``undefined``.
    msg.finished = False
    msg.favourite = False
    msg.rating = 0
    msg.shared = False

    # Empty scalar fields the official app encoder always emits. Beanconqueror's
    # protobuf-es encoder writes every field of the Bean message — including the
    # empty ones — and its import flow reads them back expecting presence. When
    # we omit them (proto3 default-value elision) the decoded object has
    # ``undefined`` for these keys and the bean fails to import. Set them all to
    # their zero value so the wire format matches a genuine app-generated link.
    msg.note = f"Bean details on Kissaten: {kissaten_url}" if kissaten_url else ""
    msg.roastingDate = ""
    msg.roast_range = 0
    msg.roast_custom = ""
    msg.ean_article_number = ""
    msg.qr_code = ""

    # Present-but-empty sub-messages. The working reference links carry empty
    # ``config{}``, ``bean_roast_information{}``, ``cupping{}`` and
    # ``cupped_flavor{}`` messages. ``SetInParent`` marks the message field as
    # present without populating any of its fields, so the decoder sees an empty
    # object instead of ``undefined`` (which the import flow chokes on).
    msg.config.SetInParent()
    msg.bean_roast_information.SetInParent()
    msg.cupping.SetInParent()
    msg.cupped_flavor.SetInParent()

    # Repeated scalar fields default to empty; explicitly clearing them ensures
    # the wire format never carries any leftover attachment/image URLs.
    msg.ClearField("attachments")
    msg.ClearField("external_images")

    return msg.SerializeToString()


# Chunk size matches Beanconqueror's share-service.service.ts:118.
_CHUNK_SIZE = 400


def build_share_link(
    bean: APICoffeeBean,
    *,
    base_url: str = "https://beanconqueror.com",
    conn=None,
    convert_price=None,
    target_currency: str = "USD",
    kissaten_url: str | None = None,
) -> str:
    """Return a ``https://beanconqueror.com/?shareUserBean0=...`` URL for the bean.

    The trailing ``/`` before ``?`` is required: Beanconqueror's deep-link
    handler matches ``https://beanconqueror.com/?shareUserBean0=`` (with the
    path slash) and the OS universal-link routing only forwards the URL to the
    app when the path is present. Without the slash the link opens the website
    instead of the app, so the bean never imports.

    Parameters
    ----------
    target_currency:
        ISO currency code for the embedded price (defaults to ``"USD"``).
        The bean's price is converted from its native currency using
        ``convert_price`` and written to the proto's ``cost`` field as a
        whole-unit integer (no cents scaling — the field is ``uint64``).
    """
    payload = encode_bean_to_proto_bytes(
        bean,
        conn=conn,
        convert_price=convert_price,
        target_currency=target_currency,
        kissaten_url=kissaten_url,
    )
    encoded = base64.b64encode(payload).decode("ascii")

    parts: list[str] = []
    loops = (len(encoded) + _CHUNK_SIZE - 1) // _CHUNK_SIZE
    for i in range(loops):
        chunk = encoded[i * _CHUNK_SIZE : (i + 1) * _CHUNK_SIZE]
        # Percent-encode the base64 value. Standard base64 contains "+", "/"
        # and "=" which are unsafe in a URL query: "+" decodes to a space and
        # "=" / "&" confuse parameter splitting, corrupting the payload before
        # Beanconqueror can atob() it. Working app links encode these as
        # %2B / %2F / %3D, so we do the same (safe="" encodes everything).
        quoted = _urlquote(chunk, safe="")
        parts.append(f"shareUserBean{i}={quoted}")
    # Normalize the base so we always emit exactly one "/" before the "?".
    root = base_url.rstrip("/")
    return f"{root}/?{'&'.join(parts)}"


def share_link_segments(link: str) -> Iterable[tuple[str, str]]:
    """Yield ``(name, value)`` pairs from a share-link URL — used in tests."""
    from urllib.parse import parse_qsl, urlparse

    parsed = urlparse(link)
    yield from parse_qsl(parsed.query, keep_blank_values=True)
