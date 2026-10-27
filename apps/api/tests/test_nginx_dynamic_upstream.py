"""Verify a long-lived Nginx proxy follows a Docker service IP replacement."""

import ipaddress
import shutil
import subprocess
import time
from pathlib import Path
from uuid import uuid4

import pytest


NGINX_IMAGE = "nginx:1.27.5-alpine"


def _docker(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["docker", *args],
        check=check,
        capture_output=True,
        text=True,
        timeout=20,
    )


def _docker_available() -> bool:
    return shutil.which("docker") is not None and subprocess.run(
        ["docker", "info"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5
    ).returncode == 0


def _wait_for_body(proxy: str, expected: str, timeout: float = 15) -> None:
    deadline = time.monotonic() + timeout
    last_error = "no response"
    while time.monotonic() < deadline:
        result = _docker(
            "exec", proxy, "wget", "-qO-", "-T", "2", "http://127.0.0.1/", check=False
        )
        if result.returncode == 0 and result.stdout.strip() == expected:
            return
        last_error = result.stderr.strip() or result.stdout.strip() or f"exit {result.returncode}"
        time.sleep(0.25)
    raise AssertionError(f"Nginx did not return {expected!r} within {timeout}s: {last_error}")


def _backend_config(body: str) -> str:
    return f'''server {{
    listen 8000;
    server_name _;
    location / {{ default_type text/plain; return 200 "{body}"; }}
}}
'''


def test_nginx_tracks_recreated_api_container_without_proxy_restart(tmp_path: Path):
    if not _docker_available():
        pytest.skip("Dynamic Docker DNS integration requires a reachable Docker daemon")

    suffix = uuid4().hex[:10]
    network = f"hawatch-dns-{suffix}"
    old_api = f"hawatch-dns-old-{suffix}"
    replacement_api = f"hawatch-dns-new-{suffix}"
    ip_holder = f"hawatch-dns-holder-{suffix}"
    proxy = f"hawatch-dns-proxy-{suffix}"
    created_containers: list[str] = []

    nginx_config = tmp_path / "nginx.conf"
    nginx_config.write_text(
        '''events {}
http {
    resolver 127.0.0.11 valid=5s ipv6=off;
    resolver_timeout 2s;
    upstream test_api {
        zone test_api 64k;
        server api:8000 resolve;
        keepalive 4;
    }
    server {
        listen 80;
        location / {
            proxy_pass http://test_api;
            proxy_http_version 1.1;
            proxy_set_header Connection "";
        }
    }
}
''',
        encoding="utf-8",
    )
    old_config = tmp_path / "api-old.conf"
    old_config.write_text(_backend_config("old"), encoding="utf-8")
    new_config = tmp_path / "api-new.conf"
    new_config.write_text(_backend_config("new"), encoding="utf-8")

    try:
        # Let Docker choose a free subnet, then recreate the network with that
        # subnet explicitly configured. Static container IPs require an
        # explicitly configured subnet, while this preserves Docker's own
        # collision-free allocation.
        _docker("network", "create", "--driver", "bridge", network)
        subnet = ipaddress.ip_network(
            _docker("network", "inspect", "--format", "{{(index .IPAM.Config 0).Subnet}}", network).stdout.strip()
        )
        _docker("network", "rm", network)
        _docker("network", "create", "--driver", "bridge", "--subnet", str(subnet), network)
        old_ip = subnet.network_address + (subnet.num_addresses - 10)
        new_ip = subnet.network_address + (subnet.num_addresses - 11)

        _docker(
            "run", "--detach", "--name", old_api, "--network", network,
            "--network-alias", "api", "--ip", str(old_ip),
            "--volume", f"{old_config}:/etc/nginx/conf.d/default.conf:ro", NGINX_IMAGE,
        )
        created_containers.append(old_api)
        _docker(
            "run", "--detach", "--name", proxy, "--network", network,
            "--volume", f"{nginx_config}:/etc/nginx/nginx.conf:ro", NGINX_IMAGE,
        )
        created_containers.append(proxy)
        _wait_for_body(proxy, "old")
        proxy_id = _docker("inspect", "--format", "{{.Id}}", proxy).stdout.strip()

        _docker("rm", "--force", old_api)
        created_containers.remove(old_api)
        # Reserve the previous address so Docker must give the service alias a
        # new IP when the replacement container joins the network.
        _docker("run", "--detach", "--name", ip_holder, "--network", network, "--ip", str(old_ip), NGINX_IMAGE)
        created_containers.append(ip_holder)
        _docker(
            "run", "--detach", "--name", replacement_api, "--network", network,
            "--network-alias", "api", "--ip", str(new_ip),
            "--volume", f"{new_config}:/etc/nginx/conf.d/default.conf:ro", NGINX_IMAGE,
        )
        created_containers.append(replacement_api)

        _wait_for_body(proxy, "new", timeout=15)
        assert _docker("inspect", "--format", "{{.Id}}", proxy).stdout.strip() == proxy_id
        assert _docker("inspect", "--format", "{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}", replacement_api).stdout.strip() == str(new_ip)
    finally:
        for container in reversed(created_containers):
            _docker("rm", "--force", container, check=False)
        _docker("network", "rm", network, check=False)
