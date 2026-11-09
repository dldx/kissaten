"""Unit tests for ``set_default_price_option`` on both bean schemas.

``CoffeeBean.set_default_price_option`` and ``CoffeeBeanOptional.set_default_price_option``
are two hand-maintained copies of the same rule, and the duplication is the risk
here: whichever copy is edited, the other has to be edited the same way. So this
file deliberately tests the *rule* once and then asserts the two classes agree on
it, rather than testing one copy and hoping the other follows.

The rule under test:

* ``price`` unset + bean already carries a ``weight`` → the price option for
  **that exact weight** supplies the price; the weight is left alone.
* ``price`` unset + no ``weight`` → the option nearest to 200 g supplies both.
* ``price`` already set → nothing is touched.
* no usable option (none at all, or every option weightless) → ``price`` stays
  ``None``.

No network, no filesystem, no DuckDB: these are pure model-validation tests.
"""

import pytest

from kissaten.schemas.coffee_bean import CoffeeBean, CoffeeBeanOptional

# Payload keys accepted by both classes. ``CoffeeBeanOptional`` inherits every
# field from ``CoffeeBean`` with an ``Optional``/default wrapper, so anything
# valid for the strict class is valid for the lenient one too.
_BASE = {
    "name": "Test Espresso",
    "roaster": "Test Roaster",
    "url": "https://test-roaster.example/product/test-espresso",
    "origins": [{"country": "CO"}],
}


def _strict(**overrides) -> CoffeeBean:
    return CoffeeBean(**{**_BASE, **overrides})


def _optional(**overrides) -> CoffeeBeanOptional:
    return CoffeeBeanOptional(**{**_BASE, **overrides})


# ---------------------------------------------------------------------------
# GAP 1: ``CoffeeBeanOptional`` — the mirrored copy, previously untested
# ---------------------------------------------------------------------------


def test_optional_fills_price_from_the_exact_weight_option():
    # The extractor often reports the bag size but omits the price. The option
    # matching that size is the only one whose price describes the same bag, so
    # it wins and the reported weight must survive the fill.
    bean = _optional(price=None, weight=250, price_options=[{"weight": 250, "price": 15.0}])

    assert bean.price == 15.0
    assert bean.weight == 250


def test_optional_fills_price_and_weight_from_the_option_nearest_to_200g():
    # With no weight on the bean there is nothing to match against, so the
    # 200 g rule decides — the same default the strict schema uses.
    bean = _optional(
        price=None,
        weight=None,
        price_options=[
            {"weight": 1000, "price": 60.0},
            {"weight": 100, "price": 8.0},
            {"weight": 250, "price": 15.0},
        ],
    )

    assert bean.price == 15.0
    assert bean.weight == 250


def test_optional_leaves_an_explicit_price_untouched():
    bean = _optional(price=12.0, weight=250, price_options=[{"weight": 250, "price": 15.0}])

    assert bean.price == 12.0
    assert bean.weight == 250


def test_optional_leaves_price_none_when_there_are_no_options():
    bean = _optional(price=None, weight=250, price_options=[])

    assert bean.price is None
    assert bean.weight == 250


def test_optional_leaves_price_none_when_every_option_is_weightless():
    # A weightless option cannot be tied to the bag the bean describes, so it
    # is not a candidate for the top-level price.
    bean = _optional(
        price=None,
        weight=None,
        price_options=[{"weight": None, "price": 9.0}, {"weight": None, "price": 11.0}],
    )

    assert bean.price is None
    assert bean.weight is None


def test_optional_ignores_weightless_options_but_uses_the_weighed_one():
    bean = _optional(
        price=None,
        weight=None,
        price_options=[{"weight": None, "price": 9.0}, {"weight": 250, "price": 15.0}],
    )

    assert bean.price == 15.0
    assert bean.weight == 250


def test_optional_breaks_a_200g_distance_tie_on_first_seen():
    # 100 g and 300 g are equidistant from 200 g. ``min`` keeps the first of
    # equal keys, so the result is positional rather than accidental.
    bean = _optional(
        price=None, weight=None, price_options=[{"weight": 100, "price": 8.0}, {"weight": 300, "price": 20.0}]
    )

    assert bean.price == 8.0
    assert bean.weight == 100


def test_optional_fills_a_price_that_the_strict_range_check_would_reject():
    # ``CoffeeBeanOptional.check_prices`` is a deliberate no-op (the lenient
    # schema exists for sources that cannot be trusted to state a sensible
    # price), so a value copied out of ``price_options`` is never range-checked
    # on this class. Pinning that asymmetry keeps it a documented difference
    # rather than an accident: the same payload raises on ``CoffeeBean``.
    payload = dict(price=None, weight=250, price_options=[{"weight": 250, "price": 4000.0}])

    bean = _optional(**payload)

    assert bean.price == 4000.0
    assert bean.weight == 250
    with pytest.raises(ValueError, match="between"):
        _strict(**payload)


# ---------------------------------------------------------------------------
# GAP 2: weight mismatch fills nothing (both classes)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("factory", [_strict, _optional], ids=["CoffeeBean", "CoffeeBeanOptional"])
def test_weight_with_no_matching_option_fills_nothing(factory):
    # Invariant: a weight on the bean is a *claim about the bag*, and only an
    # option at that exact weight is evidence about the same bag. Borrowing a
    # price from a differently-sized option would produce a price/weight pair
    # that disagrees with each other, and ``price_usd``/``price_per_kg`` are
    # both derived from that pair at refresh time — so the conservative answer
    # is to fill nothing and leave the bean visibly priceless instead.
    bean = factory(
        price=None, weight=250, price_options=[{"weight": 100, "price": 8.0}, {"weight": 500, "price": 30.0}]
    )

    assert bean.price is None
    assert bean.weight == 250


# ---------------------------------------------------------------------------
# Parity: the two copies of the rule must produce identical results
# ---------------------------------------------------------------------------

# (id, kwargs, expected price, expected weight). Every price is inside the
# strict schema's per-gram acceptance band so the comparison isolates the fill
# rule and is not masked by ``check_prices`` rejecting the payload outright.
_PARITY_CASES = [
    ("exact_weight", {"price": None, "weight": 250, "price_options": [{"weight": 250, "price": 15.0}]}, 15.0, 250),
    (
        "exact_weight_among_several",
        {
            "price": None,
            "weight": 250,
            "price_options": [{"weight": 100, "price": 8.0}, {"weight": 250, "price": 15.0}],
        },
        15.0,
        250,
    ),
    (
        "nearest_to_200g",
        {
            "price": None,
            "weight": None,
            "price_options": [
                {"weight": 1000, "price": 60.0},
                {"weight": 100, "price": 8.0},
                {"weight": 250, "price": 15.0},
            ],
        },
        15.0,
        250,
    ),
    (
        "nearest_to_200g_small_bag_wins",
        {
            "price": None,
            "weight": None,
            "price_options": [{"weight": 1000, "price": 60.0}, {"weight": 100, "price": 8.0}],
        },
        8.0,
        100,
    ),
    ("price_already_set", {"price": 12.0, "weight": 250, "price_options": [{"weight": 250, "price": 15.0}]}, 12.0, 250),
    (
        "price_already_set_without_weight",
        {"price": 12.0, "weight": None, "price_options": [{"weight": 250, "price": 15.0}]},
        12.0,
        None,
    ),
    (
        "weight_mismatch",
        {
            "price": None,
            "weight": 250,
            "price_options": [{"weight": 100, "price": 8.0}, {"weight": 500, "price": 30.0}],
        },
        None,
        250,
    ),
    ("no_options", {"price": None, "weight": 250, "price_options": []}, None, 250),
    (
        "all_options_weightless",
        {"price": None, "weight": None, "price_options": [{"weight": None, "price": 9.0}]},
        None,
        None,
    ),
    (
        "weightless_option_skipped",
        {
            "price": None,
            "weight": None,
            "price_options": [{"weight": None, "price": 9.0}, {"weight": 250, "price": 15.0}],
        },
        15.0,
        250,
    ),
    ("no_price_and_no_options_at_all", {"price": None, "weight": None, "price_options": []}, None, None),
]


@pytest.mark.parametrize(
    "case_id,kwargs,expected_price,expected_weight", _PARITY_CASES, ids=[c[0] for c in _PARITY_CASES]
)
def test_strict_and_optional_fill_agree(case_id, kwargs, expected_price, expected_weight):
    # The highest-value assertion in this file: the rule is written down twice,
    # so the two classes must agree case for case, including the cases where
    # nothing is filled.
    strict = _strict(**kwargs)
    optional = _optional(**kwargs)

    assert (strict.price, strict.weight) == (expected_price, expected_weight), (
        f"CoffeeBean regressed on case {case_id!r}"
    )
    assert (optional.price, optional.weight) == (expected_price, expected_weight), (
        f"CoffeeBeanOptional regressed on case {case_id!r}"
    )
    assert (strict.price, strict.weight) == (optional.price, optional.weight)
