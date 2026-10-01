from pathlib import Path
import re


def _repository_root() -> Path:
    return Path(__file__).resolve().parents[3]


def test_stage_stack_isolated_from_production_services_and_uses_live_database():
    root = _repository_root()
    compose = (root / "infra/compose/compose.stage.yaml").read_text(encoding="utf-8")
    services_section = compose.split("services:\n", 1)[1].split("\nnetworks:\n", 1)[0]
    services = re.findall(r"^  ([a-z][a-z0-9-]*):\s*$", services_section, re.MULTILINE)

    assert services == ["stage-api", "stage-web", "stage-gateway"]
    assert "env_file:\n      - ${HAWATCH_PRODUCTION_ENV_FILE:?Set absolute production .env path}" in compose
    assert "POSTGRES_HOST: ${HAWATCH_PRODUCTION_DB_HOST:-postgres}" in compose
    assert 'DEMO_DATA_ENABLED: "false"' in compose
    assert 'HAWATCH_BOOTSTRAP_LIVE_CATALOG_IF_EMPTY: "false"' in compose
    assert "external: true" in compose
    assert "postgres:" not in services_section
    assert "ingest-scheduler:" not in services_section
    assert "maintenance:" not in services_section


def test_stage_deploy_waits_for_real_forecast_through_the_public_gateway():
    root = _repository_root()
    script = (root / "scripts/deploy-stage.sh").read_text(encoding="utf-8")
    settings = (root / "apps/api/src/hawatch/config/settings/qa.py").read_text(encoding="utf-8")

    assert 'MODE="${1:-deploy}"' in script
    assert 'wait_for_healthy "$service"' in script
    assert '"${stage_base}/api/v1/health/ready/"' in script
    assert '"${stage_base}/api/v1/points/"' in script
    assert '"${stage_base}/api/v1/points/tochal/forecast/"' in script
    assert 'meta.get("data_mode") != "live"' in script
    assert 'meta.get("provider") != "open-meteo"' in script
    assert 'MODE" == prepare' in script
    assert 'HAWATCH_NEW_DESIGN = True' in settings
    assert 'DEMO_DATA_ENABLED = False' in settings


def test_combined_deploy_pushes_stage_only_when_enabled_and_migrates_legacy_branch():
    root = _repository_root()
    wrapper = (root / "scripts/deploy-hawatch").read_text(encoding="utf-8")

    assert 'remote_stage_enabled="$(ssh "$SSH_HOST"' in wrapper
    assert 'Stage is disabled; its branch will not be pushed or deployed.' in wrapper
    assert 'git -C "$legacy_stage_dir" fetch origin refs/heads/stage:refs/remotes/origin/stage' in wrapper
    assert 'git -C "$legacy_stage_dir" branch --set-upstream-to=origin/stage stage' in wrapper


def test_stage_only_wrapper_never_runs_the_production_deploy_script():
    root = _repository_root()
    wrapper = (root / "scripts/deploy-stage-hawatch").read_text(encoding="utf-8")
    template = (root / "apps/api/src/hawatch/modules/catalog/templates/catalog/seo_page.html").read_text(encoding="utf-8")
    index = (root / "apps/web/index.html").read_text(encoding="utf-8")

    assert "scripts/deploy.sh" not in wrapper
    assert 'git -C "$LOCAL_DIR" push origin stage' in wrapper
    assert '"/new-design/brand-mark.svg?v=stage-1"' in template
    assert '/new-design/brand-mark.svg?v=stage-1' in index
