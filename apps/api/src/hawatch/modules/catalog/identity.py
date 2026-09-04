"""Canonical identity rules for the point graph."""

from __future__ import annotations

import re
from collections.abc import Mapping


SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
IDENTITY_IMPORTANCE = {"primary", "support"}
NAME_STATUSES = {"official", "established", "descriptive"}
PLACE_TYPES = {
    "summit",
    "village",
    "shelter",
    "spring",
    "pass",
    "parking",
    "waterfall",
    "lake",
    "meadow",
    "ridge",
    "landmark",
    "trailhead",
    "camp",
    "forest",
    "desert",
    "technical_point",
}


ROUTE_SLUG_MAP = {
    "touchal-darband": "tochal-darband",
    "touchal-welanjak": "tochal-velenjak",
    "touchal-kalkchal": "tochal-kolakchal",
    "touchal-shahrestanak": "tochal-shahrestanak",
    "touchal-ahar": "tochal-ahar",
    "azadkouh-kelakbala": "azadkouh-kelak-bala",
    "daryasar-asalmahaleh": "daryasar-esel-mahalleh",
}

# These are intentionally explicit where a bare/generic term would produce a
# weak standalone page. All other independent legacy slugs are normalized by
# replacing underscores with hyphens.
POINT_SLUG_MAP = {
    # Legacy primary-point spellings are normalized to the same public point
    # slug as their catalog profile. No redirect is provided; this mapping is
    # only used while importing/normalizing pre-unification rows.
    "tochal_summit": "tochal",
    "damavand_summit": "damavand",
    "azadkouh_summit": "azadkouh",
    "darabad_summit": "darabad",
    "dorfak_summit": "dorfak",
    "gahar_lake": "gahar",
    "hazar_summit": "hazar",
    "sabalan_summit": "sabalan",
    "zarrinkuh_summit": "zarrinkuh",
    "daryasar_plain": "daryasar",
    "eskelim_waterfall": "eskelim",
    "tar_lake": "tar-lake",
    "ahar": "tochal-ahar-village",
    "amiri": "tochal-amiri-shelter",
    "barfchal": "tochal-barfchal-peak",
    "goleband": "tochal-goleband-ridge",
    "sarband": "tochal-sarband-square",
    "shahrestanak": "tochal-shahrestanak-village",
    "shirpala": "tochal-shirpala-shelter",
    "station_1": "tochal-telecabin-station-1",
    "station_2": "tochal-telecabin-station-2",
    "station_5": "tochal-telecabin-station-5",
    "station_7": "tochal-telecabin-station-7",
    "pas_ghaleh": "tochal-pas-ghaleh-village",
    "qezqunchal_dopestan": "tochal-qezqunchal-peak",
    "velenjak": "tochal-velenjak-village",
    "velenjak_parking": "tochal-velenjak-parking",
    "tochal_hotel": "tochal-hotel",
    "kolakchal_camp": "tochal-kolakchal-camp",
    "espilat_sarlo_pass": "tochal-espilat-sarlo-pass",
    "espilat-sarlo-pass": "tochal-espilat-sarlo-pass",
    "piyazchal_pass": "tochal-piyazchal-pass",
    "piyazchal-pass": "tochal-piyazchal-pass",
    "lezoon_east": "tochal-lezoon-east",
    "lezoon-east": "tochal-lezoon-east",
    "lezoon_west": "tochal-lezoon-west",
    "lezoon-west": "tochal-lezoon-west",
    "chahar_paloon": "tochal-chahar-paloon",
    "chahar-paloon": "tochal-chahar-paloon",
    "homand_tochal": "tochal-homand-tochal",
    "homand-tochal": "tochal-homand-tochal",
    "jamshidieh_park": "tochal-jamshidieh-park",
    "jamshidieh-park": "tochal-jamshidieh-park",
    "shahrestanak-spring": "tochal-shahrestanak-spring",
    "shahrestanak-sheepfold-spring": "tochal-shahrestanak-sheepfold-spring",
    "shahrestanak-pass": "tochal-shahrestanak-pass",
    "naseri-junction": "tochal-naseri-junction",
    "bazarek-pass": "tochal-bazarek-pass",
    "shahneshin-pass": "tochal-shahneshin-pass",
    "naseri_palace": "shahrestanak-naseri-palace",
    "shakarab": "tochal-shakarab-ahaar",
    "damavand_sulfur_hill": "damavand-sulfur-hill",
    "damavand_west_5008": "damavand-west-5008",
    "damavand_western_parking": "damavand-western-parking",
    "damavand_northeast_north_join": "damavand-northeast-north-junction",
    "damavand_sang_bozorg": "damavand-sang-bozorg",
    "damavand_shelter_4000": "damavand-shelter-4000",
    "damavand_shelter_5000": "damavand-shelter-5000",
    "daryasar_spring": "daryasar-spring",
    "alamkuh_siahsang": "alamkuh-siahsang",
    "gahar_aligudarz_tapleh_trailhead": "gahar-tapleh-trailhead",
    "zarrinkuh_khosravan_start": "zarrinkuh-khosravan-village",
    "zarrinkuh_aynehvarzan_start": "zarrinkuh-aynehvarzan-parking",
    "hazar_ardikan_babzangi_ridge": "hazar-ardikan-babzangi-junction",
    "hazar_babzangi_route_junction": "hazar-ardikan-babzangi-junction",
    "dorfak_south_spring": "dorfak-jeyruni-spring",
    "dorfak_west_jeyruni_spring": "dorfak-jeyruni-spring",
}


POINT_IDENTITY_OVERRIDES: dict[str, dict[str, object]] = {
    "tochal-ahar-village": {
        "name": "روستای آهار",
        "page_name": "روستای آهار، مبدأ مسیر آهار–توچال",
        "short_label": "آهار",
        "place_type": "village",
        "name_status": "official",
    },
    "tochal-shakarab-ahaar": {
        "name": "شکرآب آهار",
        "page_name": "شکرآب آهار، نقطهٔ مسیر آهار–توچال",
        "short_label": "شکرآب آهار",
        "place_type": "landmark",
        "name_status": "established",
        "aliases": ["آبشار شکرآب"],
    },
    "tochal-qezqunchal-peak": {
        "name": "قلهٔ قزقون‌چال",
        "page_name": "قلهٔ قزقون‌چال در مسیر آهار–توچال",
        "short_label": "قزقون‌چال",
        "place_type": "summit",
        "name_status": "established",
    },
    "tochal-homand-tochal": {
        "name": "قلهٔ هومند توچال",
        "page_name": "قلهٔ هومند توچال",
        "short_label": "هومند توچال",
        "place_type": "summit",
        "name_status": "established",
    },
    "tochal-barfchal-peak": {
        "name": "قلهٔ برف‌چال توچال",
        "page_name": "قلهٔ برف‌چال در مسیر توچال",
        "short_label": "برف‌چال",
        "place_type": "summit",
        "name_status": "established",
    },
    "tochal-chahar-paloon": {
        "name": "قلهٔ چهارپالون",
        "page_name": "قلهٔ چهارپالون در مسیر توچال",
        "short_label": "چهارپالون",
        "place_type": "summit",
        "name_status": "established",
    },
    "tochal-lezoon-east": {"name": "قلهٔ لزون شرقی", "page_name": "قلهٔ لزون شرقی", "short_label": "لزون شرقی", "place_type": "summit", "name_status": "established"},
    "tochal-lezoon-west": {"name": "قلهٔ لزون غربی", "page_name": "قلهٔ لزون غربی", "short_label": "لزون غربی", "place_type": "summit", "name_status": "established"},
    "tochal-goleband-ridge": {
        "name": "یال گوله‌بند توچال",
        "page_name": "یال گوله‌بند توچال",
        "short_label": "یال گوله‌بند",
        "place_type": "ridge",
        "name_status": "established",
        "aliases": ["یال کوله‌بند", "گوله‌بند", "کوله‌بند"],
    },
    "tochal-sarband-square": {
        "name": "میدان سربند",
        "page_name": "میدان سربند، ابتدای مسیر دربند–توچال",
        "short_label": "سربند",
        "place_type": "trailhead",
        "name_status": "official",
    },
    "tochal-pas-ghaleh-village": {
        "name": "روستای پس‌قلعه",
        "page_name": "روستای پس‌قلعه، ابتدای مسیر دربند–توچال",
        "short_label": "پس‌قلعه",
        "place_type": "village",
        "name_status": "official",
    },
    "tochal-shirpala-shelter": {
        "name": "پناهگاه شیرپلا",
        "page_name": "پناهگاه شیرپلا در مسیر دربند–توچال",
        "short_label": "شیرپلا",
        "place_type": "shelter",
        "name_status": "established",
    },
    "tochal-amiri-shelter": {
        "name": "جان‌پناه امیری",
        "page_name": "جان‌پناه امیری در مسیر دربند–توچال",
        "short_label": "امیری",
        "place_type": "shelter",
        "name_status": "established",
    },
    "tochal-kolakchal-camp": {
        "name": "پناهگاه و اردوگاه کلک‌چال",
        "page_name": "پناهگاه و اردوگاه کلک‌چال در مسیر توچال",
        "short_label": "کلک‌چال",
        "place_type": "camp",
        "name_status": "established",
        "aliases": ["کلکچال", "کولکچال", "اردوگاه کلک‌چال"],
    },
    "shahrestanak-naseri-palace": {
        "name": "کاخ ناصری شهرستانک",
        "page_name": "کاخ ناصری شهرستانک",
        "short_label": "کاخ ناصری",
        "place_type": "landmark",
        "name_status": "official",
    },
    "tochal-shahrestanak-village": {
        "name": "روستای شهرستانک",
        "page_name": "روستای شهرستانک، ابتدای مسیر شهرستانک–توچال",
        "short_label": "شهرستانک",
        "place_type": "village",
        "name_status": "official",
    },
    "tochal-velenjak-parking": {
        "name": "پارکینگ مجموعهٔ توچال در ولنجک",
        "page_name": "پارکینگ مجموعهٔ توچال در ولنجک",
        "short_label": "پارکینگ ولنجک",
        "place_type": "parking",
        "name_status": "established",
    },
    "tochal-telecabin-station-1": {"name": "ایستگاه ۱ تله‌کابین توچال", "page_name": "ایستگاه ۱ تله‌کابین توچال", "short_label": "ایستگاه ۱", "place_type": "landmark", "name_status": "official"},
    "tochal-telecabin-station-2": {"name": "ایستگاه ۲ تله‌کابین توچال", "page_name": "ایستگاه ۲ تله‌کابین توچال", "short_label": "ایستگاه ۲", "place_type": "landmark", "name_status": "official"},
    "tochal-telecabin-station-5": {"name": "ایستگاه ۵ تله‌کابین توچال", "page_name": "ایستگاه ۵ تله‌کابین توچال", "short_label": "ایستگاه ۵", "place_type": "landmark", "name_status": "official"},
    "tochal-telecabin-station-7": {"name": "ایستگاه ۷ تله‌کابین توچال", "page_name": "ایستگاه ۷ تله‌کابین توچال", "short_label": "ایستگاه ۷", "place_type": "landmark", "name_status": "official"},
    "tochal-shahrestanak-spring": {"name": "چشمهٔ شهرستانک", "page_name": "چشمهٔ شهرستانک در مسیر توچال", "short_label": "چشمهٔ شهرستانک", "place_type": "spring", "name_status": "established"},
    "tochal-shahrestanak-sheepfold-spring": {"name": "چشمه و گوسفندسرا شهرستانک", "page_name": "چشمه و گوسفندسرا شهرستانک در مسیر توچال", "short_label": "چشمه و گوسفندسرا", "place_type": "spring", "name_status": "established"},
    "tochal-shahrestanak-pass": {"name": "گردنهٔ شهرستانک", "page_name": "گردنهٔ شهرستانک در مسیر توچال", "short_label": "گردنهٔ شهرستانک", "place_type": "pass", "name_status": "established"},
    "tochal-naseri-junction": {"name": "دو راهی کاخ ناصری و توچال", "page_name": "دو راهی کاخ ناصری و توچال", "short_label": "دو راهی ناصری", "place_type": "landmark", "name_status": "descriptive"},
    "tochal-bazarek-pass": {"name": "گردنهٔ بازَرک توچال", "page_name": "گردنهٔ بازَرک در مسیر توچال", "short_label": "گردنهٔ بازَرک", "place_type": "pass", "name_status": "established"},
    "tochal-shahneshin-pass": {"name": "گردنهٔ شاه‌نشین توچال", "page_name": "گردنهٔ شاه‌نشین در مسیر توچال", "short_label": "گردنهٔ شاه‌نشین", "place_type": "pass", "name_status": "established"},
    "damavand-sulfur-hill": {"name": "تپهٔ گوگردی دماوند", "page_name": "تپهٔ گوگردی دماوند", "short_label": "تپهٔ گوگردی", "place_type": "landmark", "name_status": "established"},
    "damavand-western-parking": {"name": "پارکینگ غربی دماوند", "page_name": "پارکینگ غربی دماوند", "short_label": "پارکینگ غربی", "place_type": "parking", "name_status": "established"},
    "damavand-northeast-north-junction": {"name": "دوراهی شمالی و شمال‌شرقی دماوند", "page_name": "دوراهی شمالی و شمال‌شرقی دماوند", "short_label": "دوراهی شمالی–شمال‌شرقی", "place_type": "landmark", "name_status": "descriptive"},
    "damavand-sang-bozorg": {"name": "سنگ بزرگ دماوند", "page_name": "سنگ بزرگ دماوند، ابتدای مسیر شمالی", "short_label": "سنگ بزرگ", "place_type": "trailhead", "name_status": "established"},
    "damavand-shelter-4000": {"name": "جان‌پناه ۴۰۰۰ دماوند", "page_name": "جان‌پناه ۴۰۰۰ دماوند", "short_label": "جان‌پناه ۴۰۰۰", "place_type": "shelter", "name_status": "established"},
    "damavand-shelter-5000": {"name": "جان‌پناه ۵۰۰۰ دماوند", "page_name": "جان‌پناه ۵۰۰۰ دماوند", "short_label": "جان‌پناه ۵۰۰۰", "place_type": "shelter", "name_status": "established"},
    "daryasar-spring": {"name": "چشمهٔ مسیر اِسِل‌محله تا دشت دریاسر", "page_name": "چشمهٔ مسیر اِسِل‌محله تا دشت دریاسر", "short_label": "چشمهٔ دریاسر", "place_type": "spring", "name_status": "descriptive"},
    "alamkuh-siahsang": {"name": "سیاه‌سنگ علم‌کوه", "page_name": "سیاه‌سنگ علم‌کوه", "short_label": "سیاه‌سنگ", "place_type": "technical_point", "name_status": "established"},
    "gahar-tapleh-trailhead": {"name": "تپهٔ تاپله", "page_name": "تپهٔ تاپله، ابتدای مسیر الیگودرز به دریاچهٔ گهر", "short_label": "تپهٔ تاپله", "place_type": "trailhead", "name_status": "established"},
    "hazar-ardikan-babzangi-junction": {"name": "گدار دوراهی مسیرهای اردیکان و باب‌زنگی", "page_name": "گدار دوراهی مسیرهای اردیکان و باب‌زنگی در مسیر قلهٔ هزار", "short_label": "گدار دوراهی", "place_type": "landmark", "name_status": "established"},
    "dorfak-jeyruni-spring": {"name": "چشمهٔ جیرونی درفک", "page_name": "چشمهٔ جیرونی در مسیر درفک", "short_label": "چشمهٔ جیرونی", "place_type": "spring", "name_status": "established"},
    "zarrinkuh-khosravan-village": {"name": "روستای خسروان", "page_name": "روستای خسروان، ابتدای مسیر جنوبی زرین‌کوه", "short_label": "خسروان", "place_type": "village", "name_status": "official"},
    "zarrinkuh-aynehvarzan-parking": {"name": "پارکینگ آیینه‌ورزان", "page_name": "پارکینگ آیینه‌ورزان، ابتدای مسیر زرین‌کوه", "short_label": "آیینه‌ورزان", "place_type": "parking", "name_status": "established"},
    "azadkouh-kelakbala-start": {"name": "روستای کلاک بالا", "page_name": "روستای کلاک بالا، ابتدای مسیر کلاک بالا–آزادکوه", "short_label": "کلاک بالا", "place_type": "village", "name_status": "official"},
    "azadkouh-nahiyeh-start": {"name": "روستای ناحیه", "page_name": "روستای ناحیه، ابتدای مسیر آزادکوه", "short_label": "ناحیه", "place_type": "village", "name_status": "official"},
    "azadkouh-nesen-start": {"name": "حسینیهٔ روستای نسن", "page_name": "حسینیهٔ روستای نسن، ابتدای مسیر آزادکوه", "short_label": "نسن", "place_type": "trailhead", "name_status": "established"},
    "azadkouh-varangerud-start": {"name": "روستای وارنگه‌رود", "page_name": "روستای وارنگه‌رود، ابتدای مسیر آزادکوه", "short_label": "وارنگه‌رود", "place_type": "village", "name_status": "official"},
    "dorfak-east-shah-shahidan": {"name": "روستای شاه‌شهیدان", "page_name": "روستای شاه‌شهیدان، ابتدای مسیر درفک", "short_label": "شاه‌شهیدان", "place_type": "village", "name_status": "official"},
    "dorfak-west-shirkuh": {"name": "روستای شیرکوه", "page_name": "روستای شیرکوه، ابتدای مسیر درفک", "short_label": "شیرکوه", "place_type": "village", "name_status": "official"},
    "dorfak-west-larneh": {"name": "دشت لارنه", "page_name": "دشت لارنه در مسیر شیرکوه–درفک", "short_label": "دشت لارنه", "place_type": "meadow", "name_status": "established"},
    "hazar-rayen-shelter": {"name": "پناهگاه قلهٔ هزار در مسیر راین", "page_name": "پناهگاه قلهٔ هزار در مسیر راین", "short_label": "پناهگاه هزار", "place_type": "shelter", "name_status": "established"},
    "sabalan-ne-shabil-trailhead": {"name": "شابیل", "page_name": "شابیل، ابتدای مسیر شمال‌شرقی سبلان", "short_label": "شابیل", "place_type": "trailhead", "name_status": "official"},
    "sabalan-se-chay-goozi-trailhead": {"name": "چای‌گوزی", "page_name": "چای‌گوزی، ابتدای مسیر جنوب‌شرقی سبلان", "short_label": "چای‌گوزی", "place_type": "trailhead", "name_status": "established"},
    "sabalan-west-qartal-dashi": {"name": "سنگ قارتال‌داشی سبلان (عقاب سنگی)", "page_name": "سنگ قارتال‌داشی سبلان (عقاب سنگی)", "short_label": "سنگ قارتال‌داشی", "place_type": "landmark", "name_status": "established"},
}


def canonical_route_slug(slug: str) -> str:
    return ROUTE_SLUG_MAP.get(slug, slug)


def canonical_point_slug(slug: str, *, primary_slug: str | None = None) -> str:
    """Return the public slug for an independent point.

    All public places are points and therefore use a point URL.
    """
    if slug in POINT_SLUG_MAP:
        return POINT_SLUG_MAP[slug]
    if slug.startswith("route:"):
        _route, _primary, point = slug.split(":", 2)
        return canonical_point_slug(point, primary_slug=primary_slug)
    return slug.replace("_", "-")


def normalize_identity_text(value: str) -> str:
    text = str(value or "").strip().replace("ي", "ی").replace("ك", "ک")
    text = text.replace("\u200c", "")
    text = re.sub(r"[·•،,:؛/\\|()\[\]{}]+", " ", text)
    return re.sub(r"\s+", "", text).casefold()


def infer_place_type(slug: str, name: str) -> str:
    text = f"{slug} {name}".casefold()
    if "summit" in text or "قله" in text or "peak" in text:
        return "summit"
    if "parking" in text or "پارکینگ" in text:
        return "parking"
    if "shelter" in text or "hut" in text or "جانپناه" in text or "جان‌پناه" in text or "پناهگاه" in text:
        return "shelter"
    if "spring" in text or "چشمه" in text:
        return "spring"
    if "waterfall" in text or "آبشار" in text:
        return "waterfall"
    if "village" in text or "روستا" in text:
        return "village"
    if "pass" in text or "گردنه" in text:
        return "pass"
    if "ridge" in text or "یال" in text or "خطالرأس" in text:
        return "ridge"
    if "lake" in text or "دریاچه" in text:
        return "lake"
    if "meadow" in text or "دشت" in text:
        return "meadow"
    if "camp" in text or "کمپ" in text:
        return "camp"
    return "landmark"


def metadata_for_point(
    slug: str,
    row: Mapping[str, object],
    *,
    primary_label: str = "",
    source_urls: list[str] | None = None,
    is_primary: bool = False,
) -> dict[str, object]:
    """Fill a catalog point's identity block without inventing coordinates."""
    override = dict(POINT_IDENTITY_OVERRIDES.get(slug, {}))
    name = str(override.get("name") or row.get("name") or slug)
    page_name = str(override.get("page_name") or name)
    place_type = str(override.get("place_type") or infer_place_type(slug, name))
    aliases = list(row.get("aliases") or [])
    for alias in override.get("aliases", []) or []:
        if alias not in aliases:
            aliases.append(alias)
    if is_primary:
        importance = "primary"
    else:
        importance = str(row.get("importance") or "support")
    name_status = str(override.get("name_status") or row.get("name_status") or "descriptive")
    summary = str(
        row.get("identity_summary")
        or f"{page_name}؛ نقطهٔ {place_type} در محدودهٔ {primary_label or 'مسیر ثبت‌شده'}"
    )
    return {
        "name": name,
        "page_name": page_name,
        "short_label": str(override.get("short_label") or row.get("short_label") or name),
        "place_type": place_type,
        "aliases": aliases,
        "identity_summary": summary,
        "importance": importance,
        "name_status": name_status,
        "source_urls": list(row.get("source_urls") or source_urls or []),
    }
