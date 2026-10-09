from pathlib import Path
import re


def _repository_root() -> Path:
    return Path(__file__).resolve().parents[3]


def test_stage_stack_isolated_from_production_services_and_uses_live_database():
    root = _repository_root()
    compose = (root / "infra/compose/compose.stage.yaml").read_text(encoding="utf-8")
    services_section = compose.split("services:\n", 1)[1].split("\nnetworks:\n", 1)[0]
    services = re.findall(r"^  ([a-z][a-z0-9-]*):\s*$", services_section, re.MULTILINE)

    assert set(services) == {"stage-api","stage-web","stage-gateway","stage-postgres","stage-redis","stage-scheduler"}
    assert "HAWATCH_PRODUCTION_ENV_FILE" not in compose
    assert "POSTGRES_HOST: stage-postgres" in compose
    assert "POSTGRES_DB: hawatch_stage" in compose
    assert 'DEMO_DATA_ENABLED: "false"' in compose
    assert 'HAWATCH_BOOTSTRAP_LIVE_CATALOG_IF_EMPTY: "false"' in compose
    assert "external: true" not in compose
    assert "128mb" in compose


def test_stage_deploy_waits_for_real_forecast_through_the_public_gateway():
    root = _repository_root()
    script = (root / "scripts/deploy-stage.sh").read_text(encoding="utf-8")
    settings = (root / "apps/api/src/hawatch/config/settings/qa.py").read_text(encoding="utf-8")

    assert 'MODE="${1:-deploy}"' in script
    assert 'manage.py ingest_open_meteo --wait-lock-seconds 900' in script
    assert 'wait_for_healthy "$service"' in script
    assert '"${stage_base}/api/v1/health/ready/"' in script
    assert '"${stage_base}/api/v1/points/"' in script
    assert '"${stage_base}/api/v1/points/tochal/forecast/"' in script
    assert 'meta.get("data_mode") != "live"' in script
    assert 'meta.get("provider") != "open-meteo"' in script
    assert 'MODE" == prepare' in script
    assert 'HAWATCH_NEW_DESIGN = True' in settings
    assert 'DEMO_DATA_ENABLED = False' in settings


def test_production_deploy_wrapper_only_publishes_main():
    root = _repository_root()
    wrapper = (root / "scripts/deploy-hawatch").read_text(encoding="utf-8")

    assert 'git -C "$LOCAL_DIR" push origin main' in wrapper
    assert 'git -C "$LOCAL_DIR" push origin stage' not in wrapper
    assert "HAWATCH_STAGE_" not in wrapper
    assert "stage-on" not in wrapper
    assert "stage-off" not in wrapper


def test_stage_only_wrapper_never_runs_the_production_deploy_script():
    root = _repository_root()
    wrapper = (root / "scripts/deploy-stage-hawatch").read_text(encoding="utf-8")
    template = (root / "apps/api/src/hawatch/modules/catalog/templates/catalog/seo_page.html").read_text(encoding="utf-8")
    index = (root / "apps/web/index.html").read_text(encoding="utf-8")

    assert "scripts/deploy.sh" not in wrapper
    assert 'git -C "$LOCAL_DIR" push origin stage' in wrapper
    for html in (template.replace("{{ asset_prefix }}", "").replace("{{ public_asset_prefix }}", ""), index):
        assert 'href="/favicon.png" sizes="96x96" type="image/png"' in html
        assert 'href="/favicon.ico"' in html
        assert 'href="/apple-touch-icon.png" sizes="180x180"' in html
        assert '/brand/v2/favicon' not in html


def test_stage_env_upgrade_creates_independent_secrets_and_is_idempotent(tmp_path):
    import os
    import subprocess
    root=_repository_root()
    env_path=tmp_path/'stage.env'
    # A prior staging file may have contained production credentials. Never retain them.
    env_path.write_text('POSTGRES_HOST=postgres\nPOSTGRES_DB=hawatch\nPOSTGRES_PASSWORD=old-production-password\nDJANGO_SECRET_KEY=old-production-secret\nHAWATCH_PRODUCTION_ENV_FILE=/root/hawatch/.env\nHAWATCH_STAGE_ENABLED=0\n')
    process_env={**os.environ,'SSH_CONNECTION':'127.0.0.1 12345 203.0.113.1 22'}
    command=['python3',str(root/'scripts/prepare-stage-env.py'),str(env_path)]
    subprocess.run(command,check=True,env=process_env)
    first=env_path.read_text()
    assert 'old-production' not in first and 'HAWATCH_PRODUCTION_ENV_FILE' not in first
    assert 'POSTGRES_HOST=stage-postgres' in first and 'POSTGRES_DB=hawatch_stage' in first
    assert 'http://203.0.113.1:5050' in first and env_path.stat().st_mode&0o777==0o600
    subprocess.run(command,check=True,env=process_env)
    assert first==env_path.read_text()


def test_stage_update_ignores_legacy_upstream_and_duplicate_fetch_heads(tmp_path):
    import subprocess
    import os
    import shutil
    import pytest
    if not shutil.which("git"):
        pytest.skip("Deployment integration check requires Git; run on the development host")

    def git(path, *args):
        return subprocess.run(['git', '-C', str(path), *args], check=True, text=True, capture_output=True).stdout.strip()

    source = tmp_path/'source'
    source.mkdir()
    git(source, 'init', '-b', 'stage')
    git(source, 'config', 'user.name', 'Test')
    git(source, 'config', 'user.email', 'test@example.invalid')
    (source/'file').write_text('first')
    git(source, 'add', 'file')
    git(source, 'commit', '-m', 'first')
    git(source, 'branch', 'new-design')
    git(source, 'branch', 'main')
    checkout = tmp_path/'checkout'
    git(tmp_path, 'clone', '--branch', 'stage', str(source), str(checkout))
    git(checkout, 'config', '--replace-all', 'remote.origin.fetch', '+refs/heads/new-design:refs/remotes/origin/new-design')
    git(checkout, 'config', 'branch.stage.merge', 'refs/heads/new-design')
    (source/'file').write_text('second')
    git(source, 'commit', '-am', 'second')
    expected = git(source, 'rev-parse', 'HEAD')
    main_before = git(checkout, 'rev-parse', 'origin/main')
    (checkout/'.git/FETCH_HEAD').write_text(f"{expected}\t\tbranch 'stage'\n" * 2)
    for filename, variable in [('scripts/deploy-stage-hawatch','stage_dir'), ('scripts/deploy-stage.sh','STAGE_DIR')]:
        lines = (_repository_root()/filename).read_text().splitlines()
        start = next(i for i,line in enumerate(lines) if line.startswith(f'git -C "${variable}" config --replace-all remote.origin.fetch'))
        commands = '\n'.join(lines[start:start+5])
        subprocess.run(['bash','-e','-c',commands],check=True,env={**os.environ,variable:str(checkout)},capture_output=True)
        assert git(checkout, 'rev-parse', 'HEAD') == expected
        assert git(checkout, 'config', '--get-all', 'branch.stage.merge') == 'refs/heads/stage'
        assert git(checkout, 'config', '--get-all', 'remote.origin.fetch') == '+refs/heads/stage:refs/remotes/origin/stage'
        assert git(checkout, 'rev-parse', 'origin/main') == main_before
        assert len((checkout/'.git/FETCH_HEAD').read_text().splitlines()) == 1
        # Diverged local work must be refused, never reset or overwritten.
        git(checkout,'config','user.name','Test')
        git(checkout,'config','user.email','test@example.invalid')
        (checkout/'local').write_text('keep')
        git(checkout,'add','local')
        git(checkout,'commit','-m','local work')
        local = git(checkout,'rev-parse','HEAD')
        (source/'file').write_text(filename)
        git(source,'commit','-am','remote change')
        refused = subprocess.run(['bash','-e','-c',commands],env={**os.environ,variable:str(checkout)},capture_output=True)
        assert refused.returncode != 0
        assert git(checkout,'rev-parse','HEAD') == local
        # Reset only the disposable test checkout between the two script cases.
        git(checkout,'reset','--hard', 'origin/stage')
        expected = git(source,'rev-parse','HEAD')
