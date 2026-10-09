from types import SimpleNamespace

from hawatch.modules.catalog.identity import category_key_for_point, metadata_for_point, place_type_label
from hawatch.modules.catalog.seo import point_subject


def test_village_place_type_uses_the_shared_village_icon_category():
    assert category_key_for_point("", "village") == "village"


def test_explicit_category_key_remains_authoritative_for_villages():
    assert category_key_for_point("custom-village", "village") == "custom-village"


def test_neighborhood_place_type_uses_a_distinct_category_key():
    assert category_key_for_point("", "neighborhood") == "neighborhood"


def test_city_place_type_uses_a_distinct_category_key():
    assert category_key_for_point("", "city") == "city"


def test_beach_place_type_uses_its_own_icon_and_persian_label():
    assert category_key_for_point("", "beach") == "beach"
    assert place_type_label("beach") == "ساحل"


def test_valley_place_type_has_a_distinct_semantic_category_and_label():
    assert category_key_for_point("", "valley") == "valley"
    assert place_type_label("valley") == "دره"


def test_valley_subject_does_not_get_a_generic_landmark_prefix():
    point = SimpleNamespace(
        name="درهٔ گاهان تفت",
        page_name="درهٔ گاهان تفت",
        place_type="valley",
        seo_indexable=True,
    )

    assert point_subject(point) == "درهٔ گاهان تفت"


def test_shah_shahidan_page_uses_a_short_gilan_disambiguated_title():
    identity = metadata_for_point(
        "shah-shahidan-gilan",
        {"name": "روستای شاه‌شهیدان", "place_type": "village", "importance": "primary"},
        is_primary=True,
    )

    assert identity["page_name"] == "روستای شاه‌شهیدان گیلان"
    assert identity["short_label"] == "شاه‌شهیدان"


def test_siahsang_alamkuh_is_classified_as_an_independent_summit():
    identity = metadata_for_point(
        "alamkuh-siahsang",
        {"name": "سیاه‌سنگ", "place_type": "summit", "importance": "primary"},
        is_primary=True,
    )

    assert identity["name"] == "قلهٔ سیاه‌سنگ علم‌کوه"
    assert identity["page_name"] == "قلهٔ سیاه‌سنگ علم‌کوه"
    assert identity["place_type"] == "summit"
    assert category_key_for_point("", identity["place_type"]) == "mountain"


def test_sabalan_shabil_has_contextual_page_name_and_keeps_route_name_short():
    identity = metadata_for_point(
        "sabalan-shabil",
        {
            "name": "شابیل",
            "page_name": "شابیل سبلان",
            "short_label": "شابیل",
            "place_type": "trailhead",
            "importance": "primary",
        },
        is_primary=True,
    )

    assert identity["name"] == "شابیل"
    assert identity["page_name"] == "شابیل سبلان"
    assert identity["short_label"] == "شابیل"


def test_indexable_trailhead_uses_its_curated_name_without_generic_type_prefix():
    point = SimpleNamespace(
        name="شابیل",
        page_name="شابیل سبلان",
        place_type="trailhead",
        seo_indexable=True,
    )

    assert point_subject(point) == "شابیل سبلان"

    point.seo_indexable = False
    assert point_subject(point) == "مبدأ مسیر شابیل سبلان"
