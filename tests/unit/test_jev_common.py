"""Pure-logic unit tests for the shared Jev composition logic in ``kissaten.ai.jev.common``.

These tests exercise ``compose_search_params`` — the shared pure/deterministic
composition logic used by the native pydantic-ai TypeSafe adapter prototype
(``scripts/jev_native_prototype.py``) — with hand-built ``answers`` dicts: no
network, no DB.  The logic lives in the installed package as
``kissaten.ai.jev.common``.

All ``answers`` values use the exact shapes returned by the TypeSafe Jev
System One API (verified by the spike)::

    choice -> {"type": "choice", "choice": <str>, "probabilities": {...}, "confidence": float}
    noul   -> {"type": "noul", "noul": float}
    score  -> {"type": "score", "score": float, "legend": {...}, "probabilities": {...}, "confidence": float}
"""

from kissaten.ai.jev import common as jev_common
from kissaten.schemas.ai_search import Country, SearchContext

compose_search_params = jev_common.compose_search_params
generate_search_url = jev_common.generate_search_url
field_matches = jev_common.field_matches
NONE_OPTION = jev_common.NONE_OPTION
wants_tasting_notes = jev_common.wants_tasting_notes
wants_origin = jev_common.wants_origin
wants_region = jev_common.wants_region
wants_variety = jev_common.wants_variety
wants_farm = jev_common.wants_farm
sanitize_regex_value = jev_common.sanitize_regex_value
is_country_name = jev_common.is_country_name
fuzzy_matches = jev_common.fuzzy_matches
filter_context_by_query = jev_common.filter_context_by_query


def _context(**overrides):
    base = {
        "available_tasting_notes": ["Fruity", "Berry", "Chocolate", "Bitter", "Nutty"],
        "available_varietals": ["Geisha", "Pink Bourbon"],
        "available_roasters": ["KillBean", "Cafēn"],
        "available_processes": ["Natural", "Washed", "Honey"],
        "available_roast_levels": ["Light", "Medium", "Dark"],
        "available_countries": [
            Country(country_full_name="Ethiopia", country_code="ET"),
            Country(country_full_name="Colombia", country_code="CO"),
            Country(country_full_name="Brazil", country_code="BR"),
            Country(country_full_name="Panama", country_code="PA"),
            Country(country_full_name="Indonesia", country_code="ID"),
            Country(country_full_name="Kenya", country_code="KE"),
        ],
        "available_roaster_locations": ["GB (United Kingdom)", "XE (Europe)"],
        "available_farms": ["Finca Los Alpes"],
        "available_producers": ["Juan Perez"],
        "available_regions": ["Huila"],
    }
    base.update(overrides)
    return SearchContext(**base)


def _filtered(**overrides):
    base = {
        "tasting_notes": ["Fruity", "Berry", "Chocolate", "Bitter", "Nutty"],
        "varietals": ["Geisha", "Pink Bourbon"],
        "roasters": ["KillBean", "Cafēn"],
        "processes": ["Natural", "Washed", "Honey"],
        "farms": ["Finca Los Alpes"],
        "producers": ["Juan Perez"],
        "regions": ["Huila"],
        "roast_levels": ["Light", "Medium", "Dark"],
        "countries": ["Ethiopia (ET)", "Colombia (CO)"],
        "roaster_locations": ["GB (United Kingdom)", "XE (Europe)"],
    }
    base.update(overrides)
    return base


def _noul(value: float) -> dict:
    return {"type": "noul", "noul": value}


def _choice(value: str) -> dict:
    return {"type": "choice", "choice": value, "probabilities": {value: 1.0}, "confidence": 1.0}


def _score(value: float) -> dict:
    return {"type": "score", "score": value, "legend": {}, "probabilities": {}, "confidence": 1.0}


class TestPriceParsing:
    def test_max_price_under_gbp(self):
        answers = {"has_max_price": _noul(0.99), "has_min_price": _noul(0.1)}
        params = compose_search_params("fruity Ethiopian coffee under £25", answers, _context(), _filtered())
        assert params.max_price == 25.0
        assert params.min_price is None

    def test_min_price_over_usd(self):
        answers = {"has_max_price": _noul(0.1), "has_min_price": _noul(0.99)}
        params = compose_search_params("coffee over $40", answers, _context(), _filtered())
        assert params.min_price == 40.0
        assert params.max_price is None

    def test_price_only_set_when_noul_true(self):
        answers = {"has_max_price": _noul(0.1), "has_min_price": _noul(0.1)}
        params = compose_search_params("fruity Ethiopian coffee under £25", answers, _context(), _filtered())
        assert params.max_price is None
        assert params.min_price is None

    def test_euro_amount(self):
        answers = {"has_max_price": _noul(0.99), "has_min_price": _noul(0.1)}
        params = compose_search_params("cheaper than €30", answers, _context(), _filtered())
        assert params.max_price == 30.0


class TestWeightParsing:
    def test_1kg_sets_min_large_weight(self):
        answers = {"has_large_bag": _noul(0.99)}
        params = compose_search_params("1kg bags sorted by price", answers, _context(), _filtered())
        assert params.min_large_weight == 1000

    def test_500g_sets_min_large_weight(self):
        answers = {"has_large_bag": _noul(0.99)}
        params = compose_search_params("500g bags", answers, _context(), _filtered())
        assert params.min_large_weight == 500

    def test_bulk_without_number_defaults_to_1000(self):
        answers = {"has_large_bag": _noul(0.99)}
        params = compose_search_params("cheapest bulk options", answers, _context(), _filtered())
        assert params.min_large_weight == 1000

    def test_large_bag_without_number_defaults_to_500(self):
        answers = {"has_large_bag": _noul(0.99)}
        params = compose_search_params("large bag options", answers, _context(), _filtered())
        assert params.min_large_weight == 500

    def test_no_large_bag_noul_means_no_weight(self):
        answers = {"has_large_bag": _noul(0.1)}
        params = compose_search_params("1kg bags", answers, _context(), _filtered())
        assert params.min_large_weight is None


class TestElevationParsing:
    def test_above_sets_min_elevation(self):
        answers = {"high_altitude": _noul(0.99)}
        params = compose_search_params("high altitude Colombian coffee above 1800m", answers, _context(), _filtered())
        assert params.min_elevation == 1800

    def test_below_sets_max_elevation(self):
        answers = {"high_altitude": _noul(0.1)}
        params = compose_search_params("coffee below 1500m", answers, _context(), _filtered())
        assert params.max_elevation == 1500
        assert params.min_elevation is None

    def test_high_altitude_without_number_defaults_to_1500(self):
        answers = {"high_altitude": _noul(0.99)}
        params = compose_search_params("high altitude coffee", answers, _context(), _filtered())
        assert params.min_elevation == 1500


class TestTastingNotes:
    def test_conjunction(self):
        answers = {
            "note_fruity": _noul(0.99),
            "note_berry": _noul(0.99),
            "notes_disjunctive": _noul(0.1),
            "is_flavour_query": _noul(0.99),
        }
        params = compose_search_params("fruity and berry coffee", answers, _context(), _filtered())
        assert params.tasting_notes_search == "Fruity&Berry"
        assert params.use_tasting_notes_only is True

    def test_disjunction(self):
        answers = {
            "note_fruity": _noul(0.99),
            "note_berry": _noul(0.99),
            "notes_disjunctive": _noul(0.99),
            "is_flavour_query": _noul(0.99),
        }
        params = compose_search_params("fruity or berry coffee", answers, _context(), _filtered())
        assert params.tasting_notes_search == "Fruity|Berry"

    def test_negation(self):
        answers = {
            "note_chocolate": _noul(0.99),
            "exclude_bitter": _noul(0.99),
            "notes_disjunctive": _noul(0.1),
            "is_flavour_query": _noul(0.99),
        }
        params = compose_search_params("chocolate coffee that's not bitter", answers, _context(), _filtered())
        assert params.tasting_notes_search == "Chocolate&!Bitter"

    def test_excludes_only(self):
        answers = {
            "exclude_chocolate": _noul(0.99),
            "exclude_cocoa_placeholder": _noul(0.0),
            "notes_disjunctive": _noul(0.1),
            "is_flavour_query": _noul(0.99),
        }
        # no excludes should match the filtered list except chocolate
        params = compose_search_params("coffee that is not chocolatey", answers, _context(), _filtered())
        assert params.tasting_notes_search == "!Chocolate"

    def test_single_note_emitted_alone(self):
        answers = {"note_fruity": _noul(0.99), "notes_disjunctive": _noul(0.99), "is_flavour_query": _noul(0.99)}
        params = compose_search_params("fruity coffee", answers, _context(), _filtered())
        assert params.tasting_notes_search == "Fruity"

    def test_no_matching_notes_yields_none(self):
        answers = {"note_fruity": _noul(0.1), "notes_disjunctive": _noul(0.1), "is_flavour_query": _noul(0.1)}
        params = compose_search_params("light roast coffee", answers, _context(), _filtered())
        assert params.tasting_notes_search is None
        assert params.use_tasting_notes_only is False

    def test_compound_note_with_operator_is_parenthesized(self):
        filtered = _filtered(tasting_notes=["Bright & Fruity", "Chocolate"])
        answers = {
            "note_bright_fruity": _noul(0.99),
            "note_chocolate": _noul(0.99),
            "notes_disjunctive": _noul(0.1),
            "is_flavour_query": _noul(0.99),
        }
        params = compose_search_params("fruity and chocolate coffee", answers, _context(), filtered)
        # The "&" inside the note label must not be parsed as the AND operator.
        assert params.tasting_notes_search == "(Bright & Fruity)&Chocolate"

    def test_near_duplicate_notes_are_deduped_to_most_specific(self):
        filtered = _filtered(tasting_notes=["Choc", "Chocolate", "Bitter", "Bitterness"])
        answers = {
            "note_choc": _noul(0.99),
            "note_chocolate": _noul(0.99),
            "exclude_bitter": _noul(0.99),
            "exclude_bitterness": _noul(0.99),
            "notes_disjunctive": _noul(0.1),
            "is_flavour_query": _noul(0.99),
        }
        params = compose_search_params("chocolate coffee that's not bitter", answers, _context(), filtered)
        # The most specific term wins: "Chocolate" (not "Choc"), "Bitterness" (not "Bitter").
        assert params.tasting_notes_search == "Chocolate&!Bitterness"


class TestRegexFieldsOverride:
    """Hybrid split: the regex-field LLM's wildcard expression wins over Jev candidates."""

    def test_compose_regex_override(self):
        # Jev note nouls would emit "Fruity", but the regex-field LLM's
        # expression must win outright.
        answers = {
            "note_fruity": _noul(0.99),
            "notes_disjunctive": _noul(0.1),
            "is_flavour_query": _noul(0.99),
        }
        params = compose_search_params(
            "Find me coffee beans that taste like a pina colada",
            answers,
            _context(),
            _filtered(),
            regex_fields={"tasting_notes_search": "pineapple&coconut"},
        )
        assert params.tasting_notes_search == "pineapple&coconut"
        assert params.use_tasting_notes_only is True

    def test_compose_falls_back_to_notes(self):
        # regex_fields=None keeps the existing Jev candidate expression.
        answers = {
            "note_fruity": _noul(0.99),
            "notes_disjunctive": _noul(0.1),
            "is_flavour_query": _noul(0.99),
        }
        params = compose_search_params("fruity coffee", answers, _context(), _filtered(), regex_fields=None)
        assert params.tasting_notes_search == "Fruity"

    def test_compose_empty_regex_fields_falls_back(self):
        # An empty dict behaves identically to None.
        answers = {
            "note_fruity": _noul(0.99),
            "notes_disjunctive": _noul(0.1),
            "is_flavour_query": _noul(0.99),
        }
        params = compose_search_params("fruity coffee", answers, _context(), _filtered(), regex_fields={})
        assert params.tasting_notes_search == "Fruity"

    def test_field_matches_tasting_notes_casefold(self):
        # Case and outer whitespace differences are equal; operator changes are not.
        assert field_matches("tasting_notes_search", "Pineapple&Coconut", "pineapple&coconut") is True
        assert field_matches("tasting_notes_search", "  pineapple&coconut  ", "pineapple&coconut") is True
        assert field_matches("tasting_notes_search", "pineapple&coconut", "pineapple|coconut") is False
        assert field_matches("tasting_notes_search", "pineapple&coconut", None) is False
        assert field_matches("tasting_notes_search", None, None) is True


class TestOrigin:
    """Origin composition is gated by the ``needs_origin`` noul."""

    def test_continent_expansion(self):
        answers = {
            "needs_origin": _noul(0.99),
            "origin_group": _choice("south_america"),
            "origin_country": _choice("none"),
        }
        params = compose_search_params("coffees from south america", answers, _context(), _filtered())
        # Only CO, BR, PA exist in the fake DB (expansion is validated/dropped).
        assert params.origin == ["CO", "PA", "BR"]

    def test_specific_country(self):
        answers = {
            "needs_origin": _noul(0.99),
            "origin_group": _choice("specific_country"),
            "origin_country": _choice("ET"),
        }
        params = compose_search_params("ethiopian coffee", answers, _context(), _filtered())
        assert params.origin == ["ET"]

    def test_full_name_fixup(self):
        # Simulate a model returning a full country name instead of a code.
        answers = {
            "needs_origin": _noul(0.99),
            "origin_group": _choice("specific_country"),
            "origin_country": _choice("Ethiopia"),
        }
        params = compose_search_params("ethiopian coffee", answers, _context(), _filtered())
        assert params.origin == ["ET"]

    def test_unknown_country_dropped(self):
        answers = {
            "needs_origin": _noul(0.99),
            "origin_group": _choice("specific_country"),
            "origin_country": _choice("ZZ"),
        }
        params = compose_search_params("coffee from nowhere", answers, _context(), _filtered())
        assert params.origin is None

    def test_both_none_yields_none(self):
        answers = {
            "needs_origin": _noul(0.99),
            "origin_group": _choice("none"),
            "origin_country": _choice("none"),
        }
        params = compose_search_params("light roast coffee", answers, _context(), _filtered())
        assert params.origin is None


class TestNeedsOriginGate:
    """The ``needs_origin`` Jev gate in front of ``params.origin`` composition."""

    def test_gate_open_composes_origin(self):
        answers = {
            "needs_origin": _noul(0.99),
            "origin_group": _choice("specific_country"),
            "origin_country": _choice("CO"),
        }
        params = compose_search_params("colombian coffee", answers, _context(), _filtered())
        assert params.origin == ["CO"]

    def test_gate_closed_yields_none_even_with_origin_picks(self):
        # Jev picked origin_group/origin_country, but the gate says the query
        # never names a coffee origin (e.g. 'Standout ture waji', where the
        # country/continent only leaks from a producer/bean context match) —
        # so no origin filter may be composed.
        answers = {
            "needs_origin": _noul(0.1),
            "origin_group": _choice("specific_country"),
            "origin_country": _choice("CO"),
        }
        params = compose_search_params("colombian coffee", answers, _context(), _filtered())
        assert params.origin is None

    def test_gate_closed_yields_none_for_roaster_location_query(self):
        answers = {
            "needs_origin": _noul(0.1),
            "origin_group": _choice("europe"),
            "origin_country": _choice("none"),
        }
        params = compose_search_params("coffee from uk roasters", answers, _context(), _filtered())
        assert params.origin is None

    def test_missing_gate_answer_yields_none(self):
        answers = {
            "origin_group": _choice("specific_country"),
            "origin_country": _choice("CO"),
        }
        params = compose_search_params("colombian coffee", answers, _context(), _filtered())
        assert params.origin is None


class TestNeedsRegionGate:
    """The ``needs_region`` Jev gate in front of ``params.region`` composition."""

    def test_gate_open_composes_region(self):
        answers = {"needs_region": _noul(0.99), "region": _choice("Huila")}
        params = compose_search_params("coffee from Huila", answers, _context(), _filtered())
        assert params.region == "Huila"

    def test_gate_closed_yields_none_even_with_region_pick(self):
        # Jev picked a region candidate, but the gate says the query never
        # names a sub-national region (e.g. 'el salvador' — a whole country,
        # which is the coffee's origin, not a region; or a farm/varietal
        # name that happens to match a region candidate) — so no region
        # filter may be composed.
        answers = {"needs_region": _noul(0.1), "region": _choice("Huila")}
        params = compose_search_params("el salvador", answers, _context(), _filtered())
        assert params.region is None

    def test_missing_gate_answer_yields_none(self):
        answers = {"region": _choice("Huila")}
        params = compose_search_params("coffee from Huila", answers, _context(), _filtered())
        assert params.region is None


class TestNeedsVarietyGate:
    """The ``needs_variety`` Jev gate in front of ``params.variety`` composition."""

    def test_gate_open_composes_variety(self):
        answers = {"needs_variety": _noul(0.99), "variety": _choice("Pink Bourbon")}
        params = compose_search_params("pink bourbon coffee", answers, _context(), _filtered())
        assert params.variety == "Pink Bourbon"

    def test_gate_open_keeps_geisha_wildcard_logic(self):
        # The existing spelling-variant / geisha logic stays inside the open gate.
        answers = {
            "needs_variety": _noul(0.99),
            "variety": _choice("Geisha"),
            "variety_spelling_variant": _noul(0.99),
        }
        params = compose_search_params("panama geisha", answers, _context(), _filtered())
        assert params.variety == "Ge*sha"

    def test_gate_closed_yields_none_even_with_variety_pick(self):
        # Jev picked a variety candidate, but the gate says the name is a
        # roaster / producer / farm / bean / product / origin rather than a
        # varietal (e.g. 'Finca el paraiso' — Paraiso is a farm name) — so no
        # variety filter may be composed.
        answers = {"needs_variety": _noul(0.1), "variety": _choice("Geisha")}
        params = compose_search_params("finca el paraiso", answers, _context(), _filtered())
        assert params.variety is None

    def test_missing_gate_answer_yields_none(self):
        answers = {"variety": _choice("Pink Bourbon")}
        params = compose_search_params("pink bourbon coffee", answers, _context(), _filtered())
        assert params.variety is None


class TestNeedsFarmGate:
    """The ``needs_farm`` Jev gate in front of ``params.farm`` composition."""

    def test_gate_open_composes_farm(self):
        answers = {"needs_farm": _noul(0.99), "farm": _choice("Finca Los Alpes")}
        params = compose_search_params("finca los alpes coffee", answers, _context(), _filtered())
        assert params.farm == "Finca Los Alpes"

    def test_gate_closed_yields_none_even_with_farm_pick(self):
        # Jev picked a farm candidate, but the gate says the name is a
        # roaster / producer / varietal / bean / region / country rather than
        # a farm — so no farm filter may be composed.
        answers = {"needs_farm": _noul(0.1), "farm": _choice("Finca Los Alpes")}
        params = compose_search_params("geisha coffee", answers, _context(), _filtered())
        assert params.farm is None

    def test_missing_gate_answer_yields_none(self):
        answers = {"farm": _choice("Finca Los Alpes")}
        params = compose_search_params("finca los alpes coffee", answers, _context(), _filtered())
        assert params.farm is None


class TestSortMapping:
    def test_default_maps_to_date_added_desc(self):
        answers = {"sort_by": _choice("default"), "sort_order": _choice("default")}
        params = compose_search_params("best coffee", answers, _context(), _filtered())
        assert params.sort_by == "date_added"
        assert params.sort_order == "desc"

    def test_explicit_sort(self):
        answers = {"sort_by": _choice("price"), "sort_order": _choice("asc")}
        params = compose_search_params("cheapest coffee", answers, _context(), _filtered())
        assert params.sort_by == "price"
        assert params.sort_order == "asc"

    def test_missing_sort_answers_default(self):
        params = compose_search_params("coffee", {}, _context(), _filtered())
        assert params.sort_by == "date_added"
        assert params.sort_order == "desc"

    def test_url_omits_default_sort(self):
        params = compose_search_params(
            "best coffee", {"sort_by": _choice("default"), "sort_order": _choice("default")}, _context(), _filtered()
        )
        url = generate_search_url(params)
        assert "sort_by" not in url
        assert "sort_order" not in url

    def test_url_emits_explicit_sort(self):
        params = compose_search_params(
            "cheapest coffee", {"sort_by": _choice("price"), "sort_order": _choice("asc")}, _context(), _filtered()
        )
        url = generate_search_url(params)
        assert "sort_by=price" in url
        assert "sort_order=asc" in url

    def test_field_matches_sort_default(self):
        assert field_matches("sort_by", "date_added", "default") is True
        assert field_matches("sort_order", "desc", "default") is True
        assert field_matches("sort_by", "price", "default") is False


class TestBooleans:
    def test_decaf_true_when_noul_high(self):
        answers = {"is_decaf": _noul(0.99)}
        params = compose_search_params("decaf coffee", answers, _context(), _filtered())
        assert params.is_decaf is True

    def test_decaf_none_when_noul_low(self):
        answers = {"is_decaf": _noul(0.1)}
        params = compose_search_params("regular coffee", answers, _context(), _filtered())
        assert params.is_decaf is None

    def test_single_origin_none_vs_true(self):
        params_none = compose_search_params(
            "coffee", {"is_single_origin": _choice(NONE_OPTION)}, _context(), _filtered()
        )
        params_missing = compose_search_params("coffee", {}, _context(), _filtered())
        params_true = compose_search_params(
            "single origin coffee", {"is_single_origin": _choice("single_origin")}, _context(), _filtered()
        )
        params_blend = compose_search_params(
            "blends only", {"is_single_origin": _choice("blend")}, _context(), _filtered()
        )
        assert params_none.is_single_origin is None
        assert params_missing.is_single_origin is None
        assert params_true.is_single_origin is True
        assert params_blend.is_single_origin is False

    def test_in_stock_only_default_false(self):
        params = compose_search_params("coffee", {}, _context(), _filtered())
        assert params.in_stock_only is False
        params = compose_search_params("in stock coffee", {"in_stock_only": _noul(0.99)}, _context(), _filtered())
        assert params.in_stock_only is True


class TestVarietyAndProcess:
    def test_geisha_spelling_variant_emits_wildcard(self):
        answers = {
            "needs_variety": _noul(0.99),
            "variety": _choice("Geisha"),
            "variety_spelling_variant": _noul(0.99),
        }
        params = compose_search_params("panama geisha", answers, _context(), _filtered())
        assert params.variety == "Ge*sha"

    def test_geisha_mentioned_in_query_emits_wildcard_even_without_noul(self):
        answers = {
            "needs_variety": _noul(0.99),
            "variety": _choice("Geisha"),
            "variety_spelling_variant": _noul(0.1),
        }
        params = compose_search_params("any geisha variety", answers, _context(), _filtered())
        assert params.variety == "Ge*sha"

    def test_canonical_variety_no_wildcard(self):
        answers = {
            "needs_variety": _noul(0.99),
            "variety": _choice("Pink Bourbon"),
            "variety_spelling_variant": _noul(0.1),
        }
        params = compose_search_params("pink bourbon", answers, _context(), _filtered())
        assert params.variety == "Pink Bourbon"

    def test_process_excludes_anaerobic(self):
        answers = {"process": _choice("Natural"), "process_excludes_anaerobic": _noul(0.99)}
        params = compose_search_params("natural but not anaerobic", answers, _context(), _filtered())
        assert params.process == "Natural&!Anaerobic"


class TestRoasterAndLocation:
    def test_roaster_canonicalization(self):
        answers = {"roaster": _choice("Cafēn")}
        params = compose_search_params("cafen coffee", answers, _context(), _filtered())
        assert params.roaster == ["Cafēn"]

    def test_roaster_location_code(self):
        answers = {"roaster_location": _choice("GB")}
        params = compose_search_params("uk roasters", answers, _context(), _filtered())
        assert params.roaster_location == ["GB"]


class TestConfidence:
    def test_confidence_maps_score(self):
        answers = {"query_specificity": _score(0.0)}
        assert compose_search_params("coffee", answers, _context(), _filtered()).confidence == 0.7
        answers = {"query_specificity": _score(1.0)}
        assert compose_search_params("coffee", answers, _context(), _filtered()).confidence == 0.825
        answers = {"query_specificity": _score(2.0)}
        assert compose_search_params("coffee", answers, _context(), _filtered()).confidence == 0.95


class TestWantsTastingNotes:
    """The Jev gate in front of the regex-field Gemini call."""

    def test_missing_answer_is_false(self):
        assert wants_tasting_notes({}) is False

    def test_low_noul_is_false(self):
        assert wants_tasting_notes({"needs_tasting_notes": _noul(0.1)}) is False

    def test_high_noul_is_true(self):
        assert wants_tasting_notes({"needs_tasting_notes": _noul(0.99)}) is True


class TestWantsOrigin:
    """The Jev gate in front of ``params.origin`` composition."""

    def test_missing_answer_is_false(self):
        assert wants_origin({}) is False

    def test_low_noul_is_false(self):
        assert wants_origin({"needs_origin": _noul(0.1)}) is False

    def test_high_noul_is_true(self):
        assert wants_origin({"needs_origin": _noul(0.99)}) is True


class TestWantsRegion:
    """The Jev gate in front of ``params.region`` composition."""

    def test_missing_answer_is_false(self):
        assert wants_region({}) is False

    def test_low_noul_is_false(self):
        assert wants_region({"needs_region": _noul(0.1)}) is False

    def test_high_noul_is_true(self):
        assert wants_region({"needs_region": _noul(0.99)}) is True


class TestWantsVariety:
    """The Jev gate in front of ``params.variety`` composition."""

    def test_missing_answer_is_false(self):
        assert wants_variety({}) is False

    def test_low_noul_is_false(self):
        assert wants_variety({"needs_variety": _noul(0.1)}) is False

    def test_high_noul_is_true(self):
        assert wants_variety({"needs_variety": _noul(0.99)}) is True


class TestWantsFarm:
    """The Jev gate in front of ``params.farm`` composition."""

    def test_missing_answer_is_false(self):
        assert wants_farm({}) is False

    def test_low_noul_is_false(self):
        assert wants_farm({"needs_farm": _noul(0.1)}) is False

    def test_high_noul_is_true(self):
        assert wants_farm({"needs_farm": _noul(0.99)}) is True


class TestSanitizeRegexValue:
    """The regex-LLM output sanitiser (null-ish/sentinel strings must become None)."""

    def test_strips_whitespace(self):
        assert sanitize_regex_value("  pineapple&coconut ") == "pineapple&coconut"

    def test_null_ish_values_become_none(self):
        for value in ("null", "None", "", "  ", "*", "n/a", "NA", "nil"):
            assert sanitize_regex_value(value) is None

    def test_none_stays_none(self):
        assert sanitize_regex_value(None) is None

    def test_non_str_is_stringified(self):
        assert sanitize_regex_value(3.5) == "3.5"


class TestIsCountryName:
    """The region scraper-mislabel guard (country stored in the region column)."""

    _NAMES = {"colombia", "el salvador", "kenya", "cote d'ivoire"}

    def test_exact_country_name_is_flagged(self):
        assert is_country_name("Colombia", self._NAMES) is True

    def test_case_and_accents_are_normalised(self):
        assert is_country_name("EL SALVADOR", self._NAMES) is True
        assert is_country_name("Côte d'Ivoire", self._NAMES) is True

    def test_real_region_is_not_flagged(self):
        assert is_country_name("Huila", self._NAMES) is False
        assert is_country_name("Yirgacheffe", self._NAMES) is False

    def test_empty_value_is_not_flagged(self):
        assert is_country_name("", self._NAMES) is False


class TestFuzzyCandidateRecall:
    """Jaro-Winkler typo recall in the dynamic candidate lists."""

    def test_fuzzy_matches_typos(self):
        # Measured scores: larinA->Laurina 0.85, giesha->Gesha 0.82,
        # borbon->Bourbon 0.85 — all >= the 0.82 threshold.
        assert "Laurina" in fuzzy_matches("larina", ["Laurina", "Mariana", "Bernardina"])
        assert "Gesha" in fuzzy_matches("giesha", ["Gesha"])
        assert "Bourbon" in fuzzy_matches("borbon", ["Bourbon"])

    def test_fuzzy_matches_ranked_best_first(self):
        assert fuzzy_matches("larina", ["Bernardina", "Laurina", "Mariana"])[0] == "Laurina"

    def test_fuzzy_matches_threshold(self):
        # "berry" -> "Peaberry" scores 0.81 < 0.82: no recall at the threshold.
        assert fuzzy_matches("berry", ["Peaberry"]) == []
        assert fuzzy_matches("natural", ["Caturra"]) == []

    def test_filter_context_catches_typos(self):
        # "larina" has no substring match, so the per-ngram fuzzy fallback
        # surfaces "Laurina" in the varietal candidates.
        ctx = _context(available_varietals=["Laurina"])
        assert "Laurina" in filter_context_by_query("larina", ctx)["varietals"]

    def test_filter_context_country_guard(self):
        # "Ethiopia" may exist as a junk "variety" in the DB, but a country
        # name must never be offered as a varietal candidate.
        ctx = _context(
            available_varietals=["Ethiopia", "Geisha"],
            available_countries=[Country(country_full_name="Ethiopia", country_code="ET")],
        )
        assert "Ethiopia" not in filter_context_by_query("ethiopia", ctx)["varietals"]

    def test_country_guard_not_applied_to_roasters(self):
        # The guard only applies to varietals / farms / producers / regions.
        ctx = _context(
            available_roasters=["Ethiopia"],
            available_countries=[Country(country_full_name="Ethiopia", country_code="ET")],
        )
        assert "Ethiopia" in filter_context_by_query("ethiopia", ctx)["roasters"]
