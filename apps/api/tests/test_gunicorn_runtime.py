"""The serving arguments, fixed Compose capacity and real proxy concurrency."""
import concurrent.futures
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time
from urllib.request import urlopen
from uuid import uuid4

import pytest

pytestmark = pytest.mark.real_clock
ROOT = Path(__file__).resolve().parents[3]


def startup_args(tmp_path, **overrides):
    binary = tmp_path / "gunicorn"
    binary.write_text(f"#!{sys.executable}\nimport json,sys\nprint(json.dumps(sys.argv[1:]))\n")
    binary.chmod(0o755)
    env = {k: v for k, v in os.environ.items() if k not in {"GUNICORN_WORKERS", "GUNICORN_THREADS", "GUNICORN_CMD_ARGS"}}
    return subprocess.run(
        ["sh", str(ROOT / "apps/api/entrypoint.sh"), "--check-gunicorn"],
        env={**env, "PATH": str(tmp_path) + os.pathsep + env["PATH"], **overrides},
        text=True, capture_output=True, timeout=10,
    )


def test_default_entrypoint_uses_three_two_thread_workers_without_database_startup(tmp_path):
    result = startup_args(tmp_path)
    assert result.returncode == 0, result.stderr
    args = json.loads(result.stdout)
    assert args[args.index("--workers") + 1] == "3"
    assert args[args.index("--threads") + 1] == "2"
    assert args[args.index("--worker-class") + 1] == "gthread"
    assert args[args.index("--keep-alive") + 1] == "5"
    assert args[-1] == "--check-config"


@pytest.mark.parametrize("key,value", [("GUNICORN_WORKERS", "0"), ("GUNICORN_THREADS", "0"), ("GUNICORN_THREADS", "bad"), ("GUNICORN_WORKERS", "-1")])
def test_invalid_capacity_fails_before_database_or_listener(tmp_path, key, value):
    result = startup_args(tmp_path, **{key: value})
    assert result.returncode != 0
    assert "positive integers" in result.stderr
    assert "startup." not in result.stdout


def test_compose_pins_capacity_even_with_legacy_env_and_shell_values(tmp_path):
    if not shutil.which("docker"):
        pytest.skip("Docker Compose unavailable")
    project = tmp_path / "project"
    compose = project / "infra/compose/compose.yaml"
    compose.parent.mkdir(parents=True)
    compose.write_bytes((ROOT / "infra/compose/compose.yaml").read_bytes())
    env_file = project / ".env"
    env_file.write_text((ROOT / ".env.example").read_text() + "\nGUNICORN_WORKERS=1\nGUNICORN_THREADS=9\n")
    result = subprocess.run(
        ["docker", "compose", "--env-file", str(env_file), "-f", str(compose), "config", "--format", "json"],
        env={**os.environ, "GUNICORN_WORKERS": "1", "GUNICORN_THREADS": "12"},
        capture_output=True, text=True, timeout=20,
    )
    assert result.returncode == 0, result.stderr
    environment = json.loads(result.stdout)["services"]["api"]["environment"]
    assert environment["GUNICORN_WORKERS"] == "3"
    assert environment["GUNICORN_THREADS"] == "2"


def free_port():
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


def docker(*args, check=True):
    return subprocess.run(["docker", *args], capture_output=True, text=True, check=check, timeout=25)


def test_real_gthread_workers_and_production_nginx_reuse_connections_and_serve_six_requests(tmp_path):
    try:
        if docker("info", check=False).returncode:
            pytest.skip("Local Docker daemon unavailable")
    except (OSError, subprocess.TimeoutExpired):
        pytest.skip("Local Docker daemon unavailable")
    if sys.platform != "linux":
        pytest.skip("Linux host networking required for local Gunicorn/proxy integration")
    fixture = tmp_path / "probe.py"
    fixture.write_text('''import json,os,threading,time
def application(environ,start_response):
 started=time.monotonic()
 time.sleep(0.25)
 body=json.dumps({"pid":os.getpid(),"thread":threading.get_ident(),"start":started,"end":time.monotonic(),"connection":environ.get("HTTP_CONNECTION",""),"protocol":environ["SERVER_PROTOCOL"],"port":environ["REMOTE_PORT"]}).encode()
 start_response("200 OK",[("Content-Type","application/json"),("Content-Length",str(len(body)))])
 return [body]
''')
    api_port, gateway_port = free_port(), free_port()
    while gateway_port == api_port:
        gateway_port = free_port()
    args = json.loads(startup_args(tmp_path).stdout)
    args[0] = "probe:application"
    args[args.index("--bind") + 1] = f"127.0.0.1:{api_port}"
    args.remove("--check-config")
    log_path = tmp_path / "gunicorn.log"
    config = (ROOT / "infra/nginx/nginx.conf").read_text()
    config = config.replace("listen 80;", f"listen 127.0.0.1:{gateway_port};")
    config = config.replace("server api:8000 resolve;", f"server 127.0.0.1:{api_port};")
    config = config.replace("server web:5173 resolve;", f"server 127.0.0.1:{api_port};")
    gateway_config = tmp_path / "nginx.conf"
    gateway_config.write_text(config)
    name = "hawatch-gthread-test-" + uuid4().hex[:10]
    with log_path.open("w") as log:
        process = subprocess.Popen(
            [sys.executable, "-m", "gunicorn", *args], cwd=tmp_path,
            env={**os.environ, "PYTHONPATH": str(tmp_path), "GUNICORN_CMD_ARGS": ""}, stdout=log, stderr=log,
        )
        try:
            for _ in range(100):
                assert process.poll() is None, log_path.read_text()
                if log_path.read_text().count("Booting worker with pid:") == 3:
                    break
                time.sleep(0.1)
            else:
                pytest.fail("Three Gunicorn workers did not start: " + log_path.read_text())
            docker("run", "-d", "--name", name, "--network", "host",
                   "-v", f"{gateway_config}:/etc/nginx/nginx.conf:ro",
                   "-v", f"{ROOT}/infra/nginx/public-pages.inc:/etc/nginx/public-pages.inc:ro",
                   "nginx:1.27.5-alpine")
            base = f"http://127.0.0.1:{gateway_port}"
            for _ in range(50):
                try:
                    with urlopen(base + "/healthz", timeout=1) as response:
                        if response.status == 200:
                            break
                except OSError:
                    time.sleep(0.1)
            paths = ["/points/tochal", "/api/v1/health/live/", "/api/v1/points/tochal/forecast/week/"]
            def read(index):
                with urlopen(base + paths[index % len(paths)], timeout=15) as response:
                    return json.loads(response.read())
            sequential = [read(i) for i in range(6)]
            assert len({row["port"] for row in sequential}) < len(sequential), "Upstream keep-alive was not reused"
            with concurrent.futures.ThreadPoolExecutor(max_workers=18) as pool:
                rows = list(pool.map(read, range(36)))
            assert all(row["protocol"] == "HTTP/1.1" and row["connection"] == "" for row in rows)
            pids = {row["pid"] for row in rows}
            assert len(pids) == 3
            assert all(len({row["thread"] for row in rows if row["pid"] == pid}) == 2 for pid in pids)
            events = sorted([(row["start"], 1) for row in rows] + [(row["end"], -1) for row in rows])
            active = peak = 0
            for _, change in events:
                active += change
                peak = max(peak, active)
            assert peak == 6, f"Expected six simultaneous handlers, observed {peak}"
        finally:
            docker("rm", "-f", name, check=False)
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
