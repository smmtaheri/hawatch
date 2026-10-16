"""Lifecycle CLI integration tests. SSH/Docker are fakes; no server is changed."""
import fcntl
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
SERVICES = ['stage-postgres', 'stage-redis', 'stage-api', 'stage-web', 'stage-gateway', 'stage-scheduler']


def executable(path, source):
    path.write_text(source.replace('#!/usr/bin/env python3', '#!'+sys.executable, 1))
    path.chmod(0o755)


@pytest.fixture
def remote(tmp_path):
    directory = tmp_path/'bin'
    directory.mkdir()
    state, log = tmp_path/'state.json', tmp_path/'commands.jsonl'
    state.write_text('{}')
    executable(directory/'docker', '''#!/usr/bin/env python3
import json,os,sys
from pathlib import Path
args=sys.argv[1:]; state=Path(os.environ['FAKE_STATE']); data=json.loads(state.read_text())
with open(os.environ['FAKE_LOG'],'a') as out: out.write(json.dumps(args)+'\\n')
if args[0]=='ps':
    assert args==['ps','-aq','--filter','label=com.docker.compose.project=hawatch-stage']
    print('\\n'.join(data))
elif args[0]=='inspect':
    for id in args[3:]:
        item=data[id]
        print('|'.join([id,*[item[k] for k in ['project','service','oneoff','state','health','image']]]))
elif args[0] in ('start','stop'):
    item=data[args[-1]]
    assert item['project']=='hawatch-stage' and item['oneoff']=='False'
    item['state']='running' if args[0]=='start' else 'exited'
    if args[0]=='start': item['health']='healthy'
    state.write_text(json.dumps(data))
else: raise AssertionError('Forbidden Docker command: '+repr(args))
''')
    executable(directory/'curl', '''#!/usr/bin/env python3
import json,os,sys
with open(os.environ['FAKE_LOG'],'a') as out: out.write(json.dumps(['curl',*sys.argv[1:]])+'\\n')
sys.exit(0 if os.environ.get('FAKE_HTTP_OK','1')=='1' else 22)
''')
    stage_env=tmp_path/'stage.env'
    stage_env.write_text('HAWATCH_STAGE_ORIGIN=http://203.0.113.1:5050\nPOSTGRES_PASSWORD=never-print-this\n')
    env={**os.environ, 'PATH':str(directory)+os.pathsep+os.environ['PATH'],
         'FAKE_STATE':str(state), 'FAKE_LOG':str(log), 'SSH_CONNECTION':'127.0.0.1 10000 203.0.113.1 22'}

    def populate(status='exited'):
        data={f'{i+1:012x}':dict(project='hawatch-stage',service=s,oneoff='False',state=status,
              health='none' if s=='stage-scheduler' else 'healthy',image=s+':release1') for i,s in enumerate(SERVICES)}
        state.write_text(json.dumps(data))
        return data

    def run(action, **values):
        return subprocess.run(['bash',str(ROOT/'scripts/control-stage.sh'),action,str(stage_env)],
                              env={**env,**values},text=True,capture_output=True,timeout=10)

    def commands():
        return [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []

    return populate,run,commands,state,stage_env


@pytest.mark.parametrize('status,expected', [('none','NOT DEPLOYED'), ('exited','DOWN'), ('running','UP')])
def test_status_is_read_only_and_reports_readiness(remote,status,expected):
    populate,run,commands,state,stage_env=remote
    if status!='none': populate(status)
    before=state.read_bytes(),stage_env.read_bytes()
    result=run('status')
    assert result.returncode==0,result.stderr
    assert '] '+expected+' —' in result.stdout
    assert 'http://203.0.113.1:5050/points/tochal' in result.stdout
    assert 'never-print-this' not in result.stdout+result.stderr
    assert (state.read_bytes(),stage_env.read_bytes())==before
    assert not stage_env.with_suffix('.env.lock').exists()
    assert all(c[0] in ('ps','inspect','curl') for c in commands())


def test_http_failure_is_not_reported_as_up(remote):
    populate,run,*_=remote; populate('running')
    result=run('status',FAKE_HTTP_OK='0')
    assert result.returncode==0 and '] UNHEALTHY —' in result.stdout


def test_optional_docker_health_uses_missing_key_safe_template(remote):
    populate,run,commands,*_=remote
    populate('running')  # The scheduler intentionally has no Docker Health key.
    result=run('status')
    assert result.returncode==0,result.stderr
    templates=[command[2] for command in commands() if command[0]=='inspect']
    assert templates
    assert all('{{with index .State "Health"}}' in template for template in templates)
    assert all('.State.Health' not in template for template in templates)


def test_partial_missing_or_unhealthy_services_are_not_up(remote):
    populate,run,_,state,_=remote
    data=populate('running'); del data[next(iter(data))]; state.write_text(json.dumps(data))
    assert '] PARTIAL —' in run('status').stdout
    data=populate('running'); next(iter(data.values()))['health']='unhealthy'; state.write_text(json.dumps(data))
    assert '] UNHEALTHY —' in run('status').stdout


def test_down_only_stops_applications_then_data_services_and_retains_everything(remote):
    populate,run,commands,state,stage_env=remote
    before=populate('running'); env_before=stage_env.read_bytes()
    result=run('down')
    assert result.returncode==0,result.stderr
    assert '] DOWN —' in result.stdout
    after=json.loads(state.read_text())
    assert set(before)==set(after) and all(d['state']=='exited' for d in after.values())
    stops=[before[c[-1]]['service'] for c in commands() if c[0]=='stop']
    assert stops==list(reversed(SERVICES))
    assert all(c[0] in ('ps','inspect','stop') for c in commands())
    assert stage_env.read_bytes()==env_before


def test_up_starts_the_same_release_in_dependency_order_without_build_or_ingest(remote):
    populate,run,commands,state,stage_env=remote
    before=populate(); env_before=stage_env.read_bytes()
    result=run('up')
    assert result.returncode==0,result.stderr
    assert '] UP —' in result.stdout
    after=json.loads(state.read_text())
    assert all(d['state']=='running' for d in after.values())
    assert [before[c[-1]]['service'] for c in commands() if c[0]=='start']==SERVICES
    assert {k:v['image'] for k,v in before.items()}=={k:v['image'] for k,v in after.items()}
    assert all(c[0] in ('ps','inspect','start','curl') for c in commands())
    assert stage_env.read_bytes()==env_before


def test_up_requires_a_complete_previous_deployment_before_starting_anything(remote):
    populate,run,commands,state,_=remote
    data=populate(); del data[next(iter(data))]; state.write_text(json.dumps(data))
    result=run('up')
    assert result.returncode!=0 and 'deploy-stage-hawatch first' in result.stderr
    assert not any(c[0]=='start' for c in commands())


@pytest.mark.parametrize('problem',['foreign','duplicate','unknown'])
def test_invalid_targets_are_rejected_before_mutation(remote,problem):
    populate,run,commands,state,_=remote
    data=populate('running')
    if problem=='foreign': next(iter(data.values()))['project']='hawatch'
    elif problem=='unknown': next(iter(data.values()))['service']='production-api'
    else: data['000000000099']=dict(next(iter(data.values())))
    state.write_text(json.dumps(data))
    assert run('down').returncode!=0
    assert all(c[0] in ('ps','inspect') for c in commands())


def test_oneoff_jobs_are_not_lifecycle_targets(remote):
    populate,run,_,state,_=remote
    data=populate('running'); data['000000000099']=dict(next(iter(data.values())),oneoff='True')
    state.write_text(json.dumps(data))
    assert run('down').returncode==0
    assert json.loads(state.read_text())['000000000099']['state']=='running'


def test_lifecycle_lock_does_not_make_status_write_or_block(remote):
    populate,run,commands,_,stage_env=remote; populate('running')
    with open(str(stage_env)+'.lock','w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        assert run('down').returncode!=0
        assert '] UP —' in run('status').stdout
    assert not any(c[0]=='stop' for c in commands())


@pytest.fixture
def local(tmp_path):
    checkout=tmp_path/'stage'; checkout.mkdir()
    scripts=checkout/'scripts'; scripts.mkdir()
    for name in ['deploy-stage-hawatch','stage-hawatch','control-stage.sh','install-stage-commands.sh']:
        shutil.copy2(ROOT/'scripts'/name,scripts/name)
    def git(*args):
        return subprocess.run(['git','-C',str(checkout),*args],check=True,capture_output=True,text=True).stdout.strip()
    git('init','-b','stage'); git('config','user.name','Test'); git('config','user.email','test@example.invalid')
    git('remote','add','origin','git@github.com:smmtaheri/hawatch.git'); git('add','.'); git('commit','-m','Test')
    caller=tmp_path/'unrelated project'; caller.mkdir()
    subprocess.run(['git','init','-b','unrelated-feature',str(caller)],check=True,capture_output=True)
    (caller/'dirty').write_text('keep this')
    binary=tmp_path/'bin'; binary.mkdir(); log=tmp_path/'calls.jsonl'
    executable(binary/'ssh', '''#!/usr/bin/env python3
import json,os,sys
source=sys.stdin.read()
with open(os.environ['CALL_LOG'],'a') as f: f.write(json.dumps(['ssh',sys.argv[1:],source])+'\\n')
sys.exit(int(os.environ.get('FAKE_SSH_EXIT','0')))
''')
    real_git=shutil.which('git')
    executable(binary/'git', f'''#!/usr/bin/env python3
import json,os,sys
args=sys.argv[1:]
if 'push' in args:
    with open(os.environ['CALL_LOG'],'a') as f: f.write(json.dumps(['git',args])+'\\n')
else: os.execv({real_git!r},[{real_git!r},*args])
''')
    env={**os.environ,'PATH':str(binary)+os.pathsep+os.environ['PATH'],'CALL_LOG':str(log)}
    installed=tmp_path/'global'; installed.mkdir()
    result=subprocess.run(['bash',str(scripts/'install-stage-commands.sh')],cwd=caller,
                          env={**env,'HAWATCH_COMMAND_BIN_DIR':str(installed)},capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    return checkout,caller,installed,env,log,git


def test_global_deploy_ignores_cwd_branch_and_generic_local_dir(local):
    checkout,caller,installed,env,log,git=local
    result=subprocess.run([str(installed/'deploy-stage-hawatch')],cwd=caller,
                          env={**env,'HAWATCH_LOCAL_DIR':str(caller)},capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    calls=[json.loads(line) for line in log.read_text().splitlines()]
    assert calls[0]==['git',['-C',str(checkout),'push','origin','stage']]
    assert calls[1][0]=='ssh'
    assert git('branch','--show-current')=='stage'
    assert (caller/'dirty').read_text()=='keep this'
    assert subprocess.check_output(['git','-C',str(caller),'branch','--show-current'],text=True).strip()=='unrelated-feature'


@pytest.mark.parametrize('action',['up','down','status'])
def test_global_lifecycle_sends_only_requested_stage_action_from_any_directory(local,action):
    _,caller,installed,env,log,_=local
    result=subprocess.run([str(installed/'stage-hawatch'),action],cwd=caller,env=env,capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    calls=[json.loads(line) for line in log.read_text().splitlines()]
    assert len(calls)==1 and calls[0][0]=='ssh'
    assert calls[0][1]==['hawatch','bash','-s','--',action,'/root/hawatch-stage.env']
    assert 'load_state' in calls[0][2]


def test_ssh_error_is_not_misreported_as_down(local):
    _,caller,installed,env,_,_=local
    result=subprocess.run([str(installed/'stage-hawatch'),'status'],cwd=caller,
                          env={**env,'FAKE_SSH_EXIT':'255'},capture_output=True,text=True)
    assert result.returncode==255 and '] DOWN' not in result.stdout


def test_help_and_bad_actions_never_deploy(local):
    _,caller,installed,env,log,_=local
    for command in ['stage-hawatch','deploy-stage-hawatch']:
        result=subprocess.run([str(installed/command),'--help'],cwd=caller,env=env,capture_output=True)
        assert result.returncode==0
    result=subprocess.run([str(installed/'stage-hawatch'),'destroy'],cwd=caller,env=env,capture_output=True)
    assert result.returncode!=0
    assert not log.exists()


def test_deploy_from_main_worktree_never_switches_or_publishes_main(local):
    checkout,_,installed,env,log,git=local
    main=checkout.parent/'main'
    git('worktree','add','-b','main',str(main))
    (main/'uncommitted').write_text('preserve')
    result=subprocess.run([str(installed/'deploy-stage-hawatch')],cwd=main,env=env,capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    calls=[json.loads(line) for line in log.read_text().splitlines()]
    assert calls[0]==['git',['-C',str(checkout),'push','origin','stage']]
    assert subprocess.check_output(['git','-C',str(main),'branch','--show-current'],text=True).strip()=='main'
    assert (main/'uncommitted').read_text()=='preserve'


def test_dirty_dedicated_stage_refuses_deploy_without_ssh_or_push(local):
    checkout,caller,installed,env,log,_=local
    (checkout/'uncommitted').write_text('preserve')
    result=subprocess.run([str(installed/'deploy-stage-hawatch')],cwd=caller,env=env,capture_output=True,text=True)
    assert result.returncode!=0 and 'dirty' in result.stderr
    assert not log.exists()


def test_installer_refuses_to_overwrite_an_unrelated_regular_command(local):
    checkout,caller,installed,env,_,_=local
    (installed/'stage-hawatch').unlink()
    (installed/'stage-hawatch').write_text('user command')
    result=subprocess.run(['bash',str(checkout/'scripts/install-stage-commands.sh')],cwd=caller,
                          env={**env,'HAWATCH_COMMAND_BIN_DIR':str(installed)},capture_output=True,text=True)
    assert result.returncode!=0 and 'non-symlink' in result.stderr
    assert (installed/'stage-hawatch').read_text()=='user command'


def test_production_env_and_invalid_ssh_target_are_rejected_locally(local):
    _,caller,installed,env,log,_=local
    for invalid in [{'HAWATCH_STAGE_ENV_FILE':'/root/hawatch/.env'},{'HAWATCH_SSH_HOST':'-oProxyCommand=bad'}]:
        result=subprocess.run([str(installed/'stage-hawatch'),'down'],cwd=caller,
                              env={**env,**invalid},capture_output=True,text=True)
        assert result.returncode!=0
    assert not log.exists()
