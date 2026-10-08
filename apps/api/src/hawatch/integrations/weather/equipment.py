"""Weather-specific supplements, not a generic packing list. Policy v1.

Conservative provisional thresholds are explicit and testable; no inference of
surface ice, snowpack or technical terrain from forecast snowfall alone.
"""
from .hazards import value
from hawatch.common.time import now_tehran

def suggest_equipment(records):
    suggestions = {}
    def add(key, name, reason, row):
        item = suggestions.setdefault(key, {"id": key, "name": name, "reason": reason, "evidence": []})
        evidence = {"point": row.weather_point_id, "at": now_tehran(row.forecast_at).isoformat()}
        if evidence not in item["evidence"]:
            item["evidence"].append(evidence)
    for row in records:
        felt, wind, gust = value(row, "apparent_temperature_c"), value(row, "wind_speed_kmh"), value(row, "wind_gust_kmh")
        rain, snow = value(row, "precipitation_mm"), value(row, "snowfall_cm")
        windy = (wind is not None and wind >= 30) or (gust is not None and gust >= 50)
        if felt is not None and felt <= 10:
            add("fleece", "پلار", "دمای حسی پایین در زمان عبور", row)
        if felt is not None and felt <= 0:
            add("insulated-jacket", "کاپشن عایق", "دمای حسی صفر یا پایین‌تر", row)
            add("warm-gloves", "دستکش عایق", "سرما در زمان عبور", row)
            add("beanie", "کلاه گرم", "سرما در زمان عبور", row)
        if felt is not None and felt <= -10:
            add("down-mittens", "دستکش پر / میتن عایق", "سرمای شدید در زمان عبور", row)
        if windy:
            add("windstopper", "وینداستاپر", "باد یا تندباد در زمان عبور", row)
            if felt is not None and felt <= 0:
                add("balaclava", "کلاه طوفان", "هم‌زمانی باد و سرما", row)
        if rain is not None and rain > 0:
            if windy or (snow is not None and snow > 0):
                add("hardshell", "هاردشل و شلوار ضدآب", "بارش همراه باد یا برف", row)
            else:
                add("poncho", "پانچو یا هاردشل", "بارش در زمان عبور", row)
        if snow is not None and snow > 0:
            add("gaiters", "گتر", "برف پیش‌بینی‌شده در زمان عبور", row)
            if windy:
                add("goggles", "گوگل مناسب کولاک", "هم‌زمانی برف و باد", row)
        uv = value(row, "uv_index")
        if uv is not None and uv >= 3:
            add("uv-glasses", "عینک با محافظت UV", "شاخص UV بالا در زمان عبور", row)
            add("sunscreen", "ضدآفتاب و پوشش محافظ", "شاخص UV بالا در زمان عبور", row)
    if "hardshell" in suggestions:
        suggestions.pop("poncho", None)
        suggestions.pop("windstopper", None)
    return list(suggestions.values())
