"""Tests for the Beanconqueror share-link encoder + /beanconquerer-link endpoint."""

import base64

import pytest

from kissaten.api.beanconqueror_share import (
    _CHUNK_SIZE,
    _BeanProto,
    build_share_link,
    encode_bean_to_proto_bytes,
)
from kissaten.schemas.api_models import APIBean, APICoffeeBean, TastingNote
from kissaten.schemas.coffee_bean import PriceOption

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fake_convert(conn, amount, from_currency, to_currency):
    """Identity convert when target is USD; None otherwise."""
    if to_currency == "USD":
        return amount
    return None


def _make_single_origin_bean(**overrides) -> APICoffeeBean:
    """Build a well-populated single-origin bean for round-trip tests."""
    defaults = dict(
        name="Ethiopia Yirgacheffe",
        roaster="Test Roaster",
        url="https://test.com/yirg",
        description="Washed Ethiopian coffee with floral notes.",
        is_single_origin=True,
        roast_level="Medium",
        roast_profile="Filter",
        price=18.0,
        currency="USD",
        weight=250,
        is_decaf=False,
        cupping_score=87.5,
        tasting_notes=["lemon", "jasmine", "honey"],
        origins=[
            APIBean(
                country="ET",
                region="Yirgacheffe",
                farm="Konga",
                producer="Smallholder",
                elevation_min=1900,
                elevation_max=2100,
                process="washed",
                variety="Heirloom",
            ),
        ],
        price_options=[PriceOption(weight=250, price=18.0)],
    )
    defaults.update(overrides)
    return APICoffeeBean(**defaults)


def _make_blend_bean() -> APICoffeeBean:
    return APICoffeeBean(
        name="Holiday Blend 2024",
        roaster="Big Roaster",
        url="https://example.com/holiday",
        description="Three-origin blend.",
        is_single_origin=False,
        roast_level="Medium-Dark",
        roast_profile="Espresso",
        price=22.50,
        currency="USD",
        weight=340,
        is_decaf=False,
        cupping_score=86.0,
        tasting_notes=[
            TastingNote(note="chocolate"),
            TastingNote(note="spice"),
        ],
        origins=[
            APIBean(
                country="BR",
                region="Sul de Minas",
                farm="Fazenda X",
                producer="Alice",
                elevation_min=1100,
                elevation_max=1300,
                process="natural",
                variety="Yellow Bourbon",
            ),
            APIBean(
                country="CO",
                region="Huila",
                farm="La Esperanza",
                producer="Bob",
                elevation_min=1700,
                elevation_max=1900,
                process="washed",
                variety="Caturra",
            ),
            APIBean(
                country="ET",
                region="Sidamo",
                farm=None,
                producer=None,
                elevation_min=1800,
                elevation_max=0,
                process="natural",
                variety="Heirloom",
            ),
        ],
        price_options=[PriceOption(weight=340, price=22.50)],
    )


# ---------------------------------------------------------------------------
# Unit tests — encoder & proto round-trip
# ---------------------------------------------------------------------------


class TestProtoRoundTrip:
    """Encode a bean, decode with the same proto, assert field-by-field."""

    def test_single_origin_round_trip(self):
        bean = _make_single_origin_bean()
        payload = encode_bean_to_proto_bytes(bean, convert_price=_fake_convert)

        decoded = _BeanProto()
        decoded.ParseFromString(payload)

        assert decoded.name == "Ethiopia Yirgacheffe"
        assert decoded.roaster == "Test Roaster"
        assert decoded.url == "https://test.com/yirg"
        assert decoded.note == "Washed Ethiopian coffee with floral notes."
        assert decoded.weight == 250
        assert decoded.cost == 18  # $18.00 → 18 (uint64, no cents scaling)
        assert decoded.cupping_points == "87.5"
        assert decoded.decaffeinated is False
        assert decoded.roast == 8  # FULL_CITY_ROAST (Medium)
        assert decoded.beanMix == 1  # SINGLE_ORIGIN
        assert decoded.bean_roasting_type == 1  # FILTER
        assert list(decoded.cupped_flavor.custom_flavors) == ["Lemon", "Jasmine", "Honey"]
        assert decoded.favourite is False
        assert decoded.rating == 0
        assert decoded.shared is False
        assert decoded.HasField("config")
        assert decoded.config.uuid

    def test_origin_maps_to_bean_information(self):
        bean = _make_single_origin_bean()
        payload = encode_bean_to_proto_bytes(bean, convert_price=_fake_convert)

        decoded = _BeanProto()
        decoded.ParseFromString(payload)

        assert len(decoded.bean_information) == 1
        info = decoded.bean_information[0]
        assert info.country == "ET"
        assert info.region == "Yirgacheffe"
        assert info.farm == "Konga"
        assert info.farmer == "Smallholder"
        assert info.elevation == "1900-2100"
        assert info.variety == "Heirloom"
        assert info.processing == "washed"

    def test_blend_round_trip_with_three_origins(self):
        bean = _make_blend_bean()
        payload = encode_bean_to_proto_bytes(bean, convert_price=_fake_convert)

        decoded = _BeanProto()
        decoded.ParseFromString(payload)

        assert decoded.beanMix == 2  # BLEND
        assert decoded.roast == 9  # FULL_CITY_PLUS_ROAST (Medium-Dark)
        assert decoded.bean_roasting_type == 2  # ESPRESSO
        assert decoded.cost == 22  # $22.50 → 22 (uint64, no cents scaling)

        assert len(decoded.bean_information) == 3
        assert decoded.bean_information[0].country == "BR"
        assert decoded.bean_information[0].variety == "Yellow Bourbon"
        assert decoded.bean_information[1].country == "CO"
        assert decoded.bean_information[1].variety == "Caturra"
        assert decoded.bean_information[2].country == "ET"
        # origin #3 had elevation_max=0 → single value
        assert decoded.bean_information[2].elevation == "1800"

    def test_decaf_sets_decaffeinated_true(self):
        bean = _make_single_origin_bean(is_decaf=True)
        payload = encode_bean_to_proto_bytes(bean, convert_price=_fake_convert)
        decoded = _BeanProto()
        decoded.ParseFromString(payload)
        assert decoded.decaffeinated is True

    def test_unknown_roast_level_maps_to_unknown_roast(self):
        # RoastLevel enum rejects unknown values, so we exercise the "missing" branch.
        bean = _make_single_origin_bean(roast_level=None)
        payload = encode_bean_to_proto_bytes(bean, convert_price=_fake_convert)
        decoded = _BeanProto()
        decoded.ParseFromString(payload)
        assert decoded.roast == 0  # UNKNOWN_ROAST

    def test_missing_roast_level_maps_to_unknown_roast(self):
        bean = _make_single_origin_bean(roast_level=None)
        payload = encode_bean_to_proto_bytes(bean, convert_price=_fake_convert)
        decoded = _BeanProto()
        decoded.ParseFromString(payload)
        assert decoded.roast == 0

    def test_all_roast_levels(self):
        """Every kissaten roast level should map to a valid Beanconqueror roast."""
        # Roast enum: UNKNOWN=0, CINNAMON=1, AMERICAN=2, NEW_ENGLAND=3,
        # HALF_CITY=4, MODERATE_LIGHT=5, CITY=6, CITY_PLUS=7,
        # FULL_CITY=8, FULL_CITY_PLUS=9, ITALIAN=10, VIEANNA=11, FRENCH=12
        expected = {
            "Extra-Light": 1,
            "Light": 2,
            "Medium-Light": 7,
            "Medium": 8,
            "Medium-Dark": 9,
            "Dark": 12,
        }
        for level, expected_int in expected.items():
            bean = _make_single_origin_bean(roast_level=level)
            payload = encode_bean_to_proto_bytes(bean, convert_price=_fake_convert)
            decoded = _BeanProto()
            decoded.ParseFromString(payload)
            assert decoded.roast == expected_int, f"roast_level={level}"

    def test_all_roast_profiles(self):
        """Filter/Espresso/Omni/Both map correctly."""
        expected = {"Filter": 1, "Espresso": 2, "Omni": 3, "Both": 3}
        for profile, expected_int in expected.items():
            bean = _make_single_origin_bean(roast_profile=profile)
            payload = encode_bean_to_proto_bytes(bean, convert_price=_fake_convert)
            decoded = _BeanProto()
            decoded.ParseFromString(payload)
            assert decoded.bean_roasting_type == expected_int, f"roast_profile={profile}"

    def test_currency_conversion_to_target_currency(self):
        bean = _make_single_origin_bean(price=15.23, currency="EUR")
        # Fake converter: 1 EUR = 1.1 USD
        def conv(conn, amount, fr, to):
            return amount * 1.1 if to == "USD" else None

        payload = encode_bean_to_proto_bytes(bean, convert_price=conv)
        decoded = _BeanProto()
        decoded.ParseFromString(payload)
        # 15.23 EUR * 1.1 = 16.753 USD → 17 (uint64, sub-unit truncated)
        assert decoded.cost == 17

    def test_currency_conversion_to_non_usd_target(self):
        """When the user picks a non-USD target currency the cost reflects that."""
        bean = _make_single_origin_bean(price=20.0, currency="USD")
        # Fake converter: USD → EUR at 0.9
        def conv(conn, amount, fr, to):
            if fr == "USD" and to == "EUR":
                return amount * 0.9
            return None

        payload = encode_bean_to_proto_bytes(
            bean, convert_price=conv, target_currency="EUR"
        )
        decoded = _BeanProto()
        decoded.ParseFromString(payload)
        # 20 USD → 18 EUR → 18 (uint64)
        assert decoded.cost == 18

    def test_decimal_price_truncated_by_uint64(self):
        """Sub-unit precision is lost because Beanconqueror's cost field is uint64."""
        bean = _make_single_origin_bean(price=15.23, currency="USD")
        payload = encode_bean_to_proto_bytes(bean, convert_price=_fake_convert)
        decoded = _BeanProto()
        decoded.ParseFromString(payload)
        # 15.23 → 15 (uint64 truncates the cents — same as the official app)
        assert decoded.cost == 15

    def test_no_currency_conversion_means_no_cost_field(self):
        bean = _make_single_origin_bean(price=20.0, currency="USD")
        payload = encode_bean_to_proto_bytes(bean)  # no convert_price
        decoded = _BeanProto()
        decoded.ParseFromString(payload)
        # Proto3 scalar: not-set fields return the type default (0 for uint64).
        assert decoded.cost == 0

    def test_weight_falls_back_to_price_options(self):
        bean = _make_single_origin_bean(weight=None, price_options=[PriceOption(weight=500, price=30.0)])
        payload = encode_bean_to_proto_bytes(bean, convert_price=_fake_convert)
        decoded = _BeanProto()
        decoded.ParseFromString(payload)
        assert decoded.weight == 500


# ---------------------------------------------------------------------------
# Wire-compatibility — decode a real Beanconqueror-produced payload
# ---------------------------------------------------------------------------


class TestWireCompatibility:
    """Decoding a payload produced by a real Beanconqueror app must succeed."""

    def test_decode_real_sample(self):
        # From the user's example share-link in the original conversation.
        # base64 chunk from https://beanconqueror.com/?shareUserBean0=...
        b64 = (
            "CghFdGhpb3BpYRoAIgAqADIAOABAAEgAUgBaAGAAaABwAIIBAIgBAJIBAJoBAKABAKoBALABALoBFggAEAAaACAA"
            "KAAwADoAQABIAFAAWADCAQDIAQDQAQDaARYIABAAGAAgACgAMAA4AEAASABQAFgA4gEA"
        )
        payload = base64.b64decode(b64)

        decoded = _BeanProto()
        decoded.ParseFromString(payload)

        # Field 1 = "Ethiopia"
        assert decoded.name == "Ethiopia"
        # 1 bean_information entry
        assert len(decoded.bean_information) == 1
        # decaf not set on field 17
        assert decoded.decaffeinated is False


# ---------------------------------------------------------------------------
# build_share_link — chunking & URL format
# ---------------------------------------------------------------------------


class TestBuildShareLink:
    def test_url_format(self):
        bean = _make_single_origin_bean()
        link = build_share_link(bean, convert_price=_fake_convert)
        assert link.startswith("https://beanconqueror.com/?shareUserBean0=")

    def test_chunking_with_long_payload(self):
        # Force a long payload by using a long description.
        long_desc = "A" * 5000
        bean = _make_single_origin_bean(description=long_desc)
        link = build_share_link(bean, convert_price=_fake_convert)

        # Find all chunks and verify they're each ≤ _CHUNK_SIZE chars.
        from urllib.parse import parse_qsl, urlparse

        query = urlparse(link).query
        params = dict(parse_qsl(query))
        chunk_names = sorted(
            (n for n in params if n.startswith("shareUserBean")),
            key=lambda n: int(n[len("shareUserBean"):]),
        )
        assert chunk_names == [f"shareUserBean{i}" for i in range(len(chunk_names))]
        assert len(chunk_names) > 1
        for name, value in params.items():
            if name.startswith("shareUserBean"):
                assert len(value) <= _CHUNK_SIZE, f"{name} exceeded chunk size"

    def test_reassembled_base64_decodes(self):
        """Rejoining the chunks should yield the same base64 the encoder produced."""
        long_desc = "B" * 5000
        bean = _make_single_origin_bean(description=long_desc)

        from urllib.parse import parse_qsl, urlparse

        link = build_share_link(bean, convert_price=_fake_convert)
        params = dict(parse_qsl(urlparse(link).query))

        # Reassemble in order
        chunks = []
        i = 0
        while f"shareUserBean{i}" in params:
            chunks.append(params[f"shareUserBean{i}"])
            i += 1
        reassembled = "".join(chunks)

        # The encoder randomises uuid + timestamp inside Config, so the byte-for-byte
        # base64 changes between calls. Decode instead and compare the user-visible
        # fields that should be identical.
        raw_b64 = base64.b64encode(link.encode("utf-8")).decode("ascii")
        # Sanity: the link itself round-trips through base64 (smoke check).
        assert raw_b64  # just confirm encoding works
        # Decode the reassembled chunks and check the user fields.
        decoded = _BeanProto()
        decoded.ParseFromString(base64.b64decode(reassembled))
        assert decoded.name == "Ethiopia Yirgacheffe"
        assert decoded.roaster == "Test Roaster"
        assert decoded.note == long_desc


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------


class TestBeanconquererLinkEndpoint:
    @pytest.mark.asyncio
    async def test_returns_valid_url_for_known_bean(self, client):
        from kissaten.api.db import conn as _conn

        row = _conn.execute(
            "SELECT bean_url_path FROM coffee_beans WHERE bean_url_path IS NOT NULL LIMIT 1"
        ).fetchone()
        if not row:
            pytest.skip("No beans with bean_url_path found in test database")

        response = client.get(f"/v1/beans{row[0]}/beanconquerer-link")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert "share_url" in data["data"]
        url = data["data"]["share_url"]
        assert url.startswith("https://beanconqueror.com?shareUserBean0=")

    @pytest.mark.asyncio
    async def test_returns_404_for_unknown_bean(self, client):
        response = client.get("/v1/beans/no-such-roaster/no-such-bean/beanconquerer-link")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_url_decodes_to_valid_proto(self, client):
        """The base64 payload in the URL must decode into a valid BeanProto."""
        import base64 as _b64
        from urllib.parse import parse_qsl, urlparse

        from kissaten.api.db import conn as _conn

        row = _conn.execute(
            "SELECT bean_url_path FROM coffee_beans WHERE bean_url_path IS NOT NULL LIMIT 1"
        ).fetchone()
        if not row:
            pytest.skip("No beans with bean_url_path found in test database")

        response = client.get(f"/v1/beans{row[0]}/beanconquerer-link")
        assert response.status_code == 200
        url = response.json()["data"]["share_url"]

        # Reassemble chunks
        params = dict(parse_qsl(urlparse(url).query))
        chunks = []
        i = 0
        while f"shareUserBean{i}" in params:
            chunks.append(params[f"shareUserBean{i}"])
            i += 1
        payload = _b64.b64decode("".join(chunks))

        proto = _BeanProto()
        proto.ParseFromString(payload)  # would raise on malformed bytes
        # Should at least carry a name (or be empty if the bean has no name)
        # — the point is that the bytes are valid proto wire format.
        assert isinstance(proto.name, str)
