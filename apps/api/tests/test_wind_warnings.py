from types import SimpleNamespace

from hawatch.api.v1.serializers import record_severity, wind_alert_payload


def test_existing_wind_only_critical_reading_is_yellow():
    record = SimpleNamespace(
        weather_code="overcast", severity="critical", wind_speed_kmh=15,
        wind_gust_kmh=45,
    )
    assert record_severity(record) == "change"
    assert wind_alert_payload(record) == {
        "code": "gale", "label": "تندباد", "severity": "change",
    }


def test_wind_does_not_downgrade_a_separate_critical_weather_warning():
    record = SimpleNamespace(
        weather_code="thunder", severity="critical", wind_speed_kmh=15,
        wind_gust_kmh=45,
    )
    assert record_severity(record) == "critical"
    assert wind_alert_payload(record)["severity"] == "change"
