from hawatch.modules.catalog.identity import category_key_for_point, metadata_for_point, place_type_label


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


def test_shah_shahidan_page_uses_a_short_gilan_disambiguated_title():
    identity = metadata_for_point(
        "shah-shahidan-gilan",
        {"name": "روستای شاه‌شهیدان", "place_type": "village", "importance": "primary"},
        is_primary=True,
    )

    assert identity["page_name"] == "روستای شاه‌شهیدان گیلان"
    assert identity["short_label"] == "شاه‌شهیدان"
