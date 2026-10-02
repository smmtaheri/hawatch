from hawatch.api.v1.serializers import record_severity, wind_alert_payload
from test_weather_hazards import row


def test_existing_moderate_gust_is_not_a_warning():
    record=row(wind_gust_kmh=45)
    assert record_severity(record)=="normal"
    assert wind_alert_payload(record) is None


def test_yellow_wind_does_not_downgrade_lightning():
    record=row(weather_code="thunder",wmo_code=95,wind_speed_kmh=30,wind_gust_kmh=50)
    assert record_severity(record)=="critical"
    assert wind_alert_payload(record)["severity"]=="change"


def test_extreme_wind_has_a_red_warning():
    record=row(wind_speed_kmh=45,wind_gust_kmh=80)
    assert record_severity(record)=="critical"
    assert wind_alert_payload(record)["severity"]=="critical"


def test_extreme_gust_with_low_mean_wind_has_no_wind_warning():
    record=row(wind_speed_kmh=29,wind_gust_kmh=100)
    assert record_severity(record)=="normal"
    assert wind_alert_payload(record) is None
