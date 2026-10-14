import json
from pathlib import Path

import pytest

from hawatch.modules.catalog.search_text import SearchQuery, normalize_search_text, normalize_search_words


CASES = json.loads((Path(__file__).resolve().parents[1] / "fixtures/search-normalization.json").read_text())


@pytest.mark.parametrize("case", CASES, ids=[case["normalized"] for case in CASES])
def test_shared_persian_search_contract(case):
    for value in case["variants"]:
        assert normalize_search_words(value) == case["normalized"]
        assert normalize_search_text(value) == case["normalized"].replace(" ", "")


def test_spacing_is_optional_and_all_query_words_are_required():
    assert SearchQuery.parse("علمکوه").matches(["قلهٔ علم‌کوه"])
    assert SearchQuery.parse("علم کوه").matches(["قلهٔ علمکوه"])
    assert SearchQuery.parse("توچال دربند").matches(["دربند تا توچال"])
    assert SearchQuery.parse("دماوند مازندران").matches(["قلهٔ دماوند", "مازندران"])
    assert not SearchQuery.parse("دماوند سبلان").matches(["قلهٔ دماوند", "مازندران"])
    assert not SearchQuery.parse("ماهی").matches(["ماه"])
