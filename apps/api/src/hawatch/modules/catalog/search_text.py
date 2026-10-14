"""Persian search rules, mirrored by web/lib/searchText.ts and shared cases."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from functools import lru_cache


_LETTERS = str.maketrans("يىكۀةە", "ییکههه")
_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
_EZAFE = re.compile(r"(^| )(\S*ه) ی(?= |$)")


@lru_cache(maxsize=16384)
def normalize_search_words(value: str) -> str:
    text = unicodedata.normalize("NFKD", str(value or "")).translate(_LETTERS).translate(_DIGITS)
    letters = []
    for char in text:
        category = unicodedata.category(char)
        if char in "\u200c\u200d":
            letters.append(" ")
        elif char == "ـ" or category.startswith("M") or category == "Cf":
            continue
        else:
            letters.append(char.lower() if category[0] in "LN" else " ")
    words = " ".join("".join(letters).split())
    # Only the separate ezafe after a heh is optional; never erase a real ی.
    return _EZAFE.sub(r"\1\2", words)


def normalize_search_text(value: str) -> str:
    return normalize_search_words(value).replace(" ", "")


def prepare_search_terms(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(term for value in values if (term := normalize_search_text(value))))


def point_search_terms(point) -> list[str]:
    values = [point.name, point.page_name]
    if point.importance == "primary":
        values.append(point.short_label)
    values.extend(point.aliases or [])
    values.append(point.region)
    return list(dict.fromkeys(value.strip() for value in values if value and value.strip()))


def route_search_terms(route, linked_points) -> list[str]:
    values = [route.title, route.origin, route.target_label, route.region]
    for point in linked_points:
        if point.weather_point_id and point.weather_point.is_active:
            values.extend(point_search_terms(point.weather_point))
    return list(dict.fromkeys(value.strip() for value in values if value and value.strip()))


@dataclass(frozen=True)
class SearchQuery:
    compact: str
    tokens: tuple[str, ...]

    @classmethod
    def parse(cls, value: str) -> SearchQuery:
        words = normalize_search_words(value)
        return cls(words.replace(" ", ""), tuple(dict.fromkeys(words.split())))

    def score(self, terms: Sequence[str]) -> tuple[int, int] | None:
        """Exact, prefix, substring, then all words across this item's terms."""
        if not self.compact:
            return None
        best = None
        for index, term in enumerate(terms):
            position = 0 if term == self.compact else 1 if term.startswith(self.compact) else 2 if self.compact in term else -1
            if position >= 0 and (best is None or position < best[0]):
                best = (position, index)
                if position == 0:
                    return best
        if best is not None:
            return best
        if len(self.tokens) > 1 and all(any(token in term for term in terms) for token in self.tokens):
            return (3, 0)
        return None

    def matches(self, values: Iterable[str]) -> bool:
        return self.score(prepare_search_terms(values)) is not None
