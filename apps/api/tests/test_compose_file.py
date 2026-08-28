from pathlib import Path

import pytest


def _find_compose_file() -> Path | None:
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "infra" / "compose" / "compose.yaml"
        if candidate.exists():
            return candidate
    extra = Path("/workspace/infra/compose/compose.yaml")
    return extra if extra.exists() else None


def test_compose_default_services_and_pinned_postgis():
    compose = _find_compose_file()
    if compose is None:
        pytest.skip("compose.yaml is not available in this test environment")
    text = compose.read_text(encoding="utf-8")
    assert "postgres:" in text
    assert "api:" in text
    assert "web:" in text
    assert "nginx:" in text
    assert "postgis/postgis:16-3.5" in text
    assert "image: postgis/postgis:latest" not in text
    assert 'profiles: ["cache"]' in text
    assert "kafka" not in text.lower()
    assert "../../.env.example" not in text
    assert "env_file:" in text
    assert "../../.env" in text
    assert "OPEN_METEO_BASE_URL" in text
    assert "FORECAST_STALE_AFTER_HOURS" in text
    assert 'profiles: ["observability"]' in text
    assert "LIVE_INGEST_INTERVAL_SECONDS" not in text
    assert "run --rm ingest" not in text
