from pathlib import Path


def test_production_week_deploy_enables_shared_cache_and_matching_asset_versions():
    root=Path(__file__).resolve().parents[3]
    compose=(root/'infra/compose/compose.yaml').read_text()
    script=(root/'scripts/deploy.sh').read_text()
    assert compose.count('REDIS_URL: redis://redis:6379/0')==2
    assert compose.count('OPEN_METEO_FORECAST_DAYS: ${OPEN_METEO_FORECAST_DAYS:-10}')==2
    assert 'VITE_ASSET_VERSION: ${HAWATCH_ASSET_VERSION:-local}' in compose
    assert compose.count('HAWATCH_ASSET_VERSION: ${HAWATCH_ASSET_VERSION:-local}')==2
    assert 'profiles: ["cache"]' not in compose
    assert '"--maxmemory", "128mb", "--maxmemory-policy", "allkeys-lru"' in compose
    assert 'set_env_value OPEN_METEO_FORECAST_DAYS 10' in script
    assert 'wait_for_healthy redis' in script
    assert 'exec -T api python manage.py apply_route_descent' in script
    assert script.index('sync_catalog --apply')<script.index('manage.py apply_route_descent')
    assert 'manage.py warm_week_cache' not in script
    assert 'ingest manage.py ingest_open_meteo --wait-lock-seconds 900' in script
    assert script.index("load_packaged_catalogs") < script.index("Starting the new release")


import os
import subprocess


def _deployment_harness(tmp_path):
    repo = tmp_path / 'repo'
    repo.mkdir()
    subprocess.run(['git','init','-q',str(repo)],check=True)
    subprocess.run(['git','-C',str(repo),'config','user.email','test@example.invalid'],check=True)
    subprocess.run(['git','-C',str(repo),'config','user.name','Deployment test'],check=True)
    fixture = repo / 'apps/api/fixtures/catalog/example.json'
    fixture.parent.mkdir(parents=True)
    fixture.write_text('{}')
    def commit():
        subprocess.run(['git','-C',str(repo),'add','.'],check=True)
        subprocess.run(['git','-C',str(repo),'commit','-qm','test inputs'],check=True)
    commit()
    script = (Path(__file__).resolve().parents[3]/'scripts/deploy.sh').read_text()
    function = 'run_stack() {' + script.split('run_stack() {',1)[1].split('\ninstall_base_packages\n',1)[0]
    commands = tmp_path/'commands.log'
    harness = r"""
set -Eeuo pipefail
COMPOSE_RELATIVE_PATH=infra/compose/compose.yaml
ENABLE_OBSERVABILITY=0
DOCKER_BUILD_RETRIES=1
RUN_INITIAL_INGEST=0
API_PUBLISH_PORT=8000
WEB_PUBLISH_PORT=5173
NGINX_PUBLISH_PORT=80
PUBLIC_HOST=example.invalid
ENV_FILE=unused
log(){ :; }
fail(){ exit 1; }
wait_for_healthy(){ :; }
wait_for_running(){ :; }
get_env_value(){ :; }
curl(){ :; }
docker(){
 printf '%s\n' "$*" >> "$COMMAND_LOG"
 if [[ "$*" == *'sync_catalog --apply'* && "${FAIL_SYNC:-0}" == 1 ]]; then return 1; fi
}
""" + function + '\nrun_stack\n'
    def run(fail=False):
        commands.write_text('')
        result=subprocess.run(['bash','-c',harness],env={**os.environ,'REPO_DIR':str(repo),'COMMAND_LOG':str(commands),'FAIL_SYNC':str(int(fail))},capture_output=True,text=True)
        return result, commands.read_text()
    return repo,fixture,commit,run


def test_normal_deploy_preserves_data_services_and_never_warms_or_fetches(tmp_path):
    repo,fixture,commit,run=_deployment_harness(tmp_path)
    result,commands=run()
    assert result.returncode==0,result.stderr
    assert 'up -d --no-recreate postgres redis' in commands
    assert 'up -d --no-deps api web maintenance ingest-scheduler' in commands
    assert 'up -d --no-deps --force-recreate nginx' in commands
    assert 'warm_week_cache' not in commands and 'ingest_open_meteo' not in commands
    assert ' down' not in commands
    assert commands.count('sync_catalog --apply')==1
    assert commands.count('manage.py apply_route_descent')==1
    result,commands=run()
    assert result.returncode==0,result.stderr
    assert 'sync_catalog --apply' not in commands and 'manage.py apply_route_descent' not in commands


def test_only_catalog_changes_trigger_data_sync(tmp_path):
    repo,fixture,commit,run=_deployment_harness(tmp_path)
    assert run()[0].returncode==0
    (repo/'ui.txt').write_text('UI release')
    commit()
    result,commands=run()
    assert result.returncode==0 and 'sync_catalog --apply' not in commands
    fixture.write_text('{"updated":true}')
    commit()
    result,commands=run()
    assert result.returncode==0 and 'sync_catalog --apply' in commands


def test_failed_catalog_sync_does_not_mark_inputs_applied(tmp_path):
    repo,fixture,commit,run=_deployment_harness(tmp_path)
    result,commands=run(fail=True)
    assert result.returncode!=0
    assert not (repo/'.git/hawatch-catalog-deploy.sha256').exists()
    result,commands=run()
    assert result.returncode==0 and 'sync_catalog --apply' in commands
