"""Exercise production exact locations with an unavailable API upstream."""
import concurrent.futures
import os
from pathlib import Path
import subprocess
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from uuid import uuid4

import pytest

pytestmark = pytest.mark.real_clock


def docker(*args, check=True):
    return subprocess.run(["docker", *args], check=check, capture_output=True, text=True, timeout=25)


def test_production_sitemap_is_static_even_when_api_fails(tmp_path):
    root = Path(__file__).resolve().parents[3]
    try:
        if docker("info", check=False).returncode:
            pytest.skip("Docker daemon unavailable")
    except (OSError, subprocess.TimeoutExpired):
        pytest.skip("Docker unavailable")
    suffix = uuid4().hex[:8]
    network, backend, gateway = (f"hawatch-sitemap-{part}-{suffix}" for part in ("net", "api", "gateway"))
    directory = tmp_path / "seo"
    directory.mkdir(mode=0o755)
    artifact = directory / "sitemap.xml"
    content = b'<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>https://hawatch.ir/</loc></url></urlset>'
    artifact.write_bytes(content)
    os.utime(artifact, (time.time() - 10, time.time() - 10))
    backend_config = tmp_path / "backend.conf"
    backend_config.write_text('server { listen 8000; location / { return 503; } }\nserver { listen 5173; location / { return 503; } }')
    started = []
    try:
        docker("network", "create", network)
        docker("run", "-d", "--name", backend, "--network", network, "--network-alias", "api", "--network-alias", "web",
               "-v", f"{backend_config}:/etc/nginx/conf.d/default.conf:ro", "nginx:1.27.5-alpine")
        started.append(backend)
        docker("run", "-d", "--name", gateway, "--network", network, "-p", "127.0.0.1::80",
               "-v", f"{root}/infra/nginx/nginx.conf:/etc/nginx/nginx.conf:ro",
               "-v", f"{root}/infra/nginx/public-pages.inc:/etc/nginx/public-pages.inc:ro",
               "-v", f"{directory}:/var/lib/hawatch-seo:ro", "nginx:1.27.5-alpine")
        started.append(gateway)
        port = docker("port", gateway, "80").stdout.strip().split(":")[-1]
        base = f"http://127.0.0.1:{port}"
        for _ in range(30):
            try:
                with urlopen(base + "/healthz", timeout=1) as response:
                    if response.status == 200:
                        break
            except OSError:
                time.sleep(0.1)
        with urlopen(base + "/sitemap.xml", timeout=2) as response:
            assert response.read() == content
            assert response.headers.get_content_type() == "application/xml"
            assert response.headers["Cache-Control"] == "public, max-age=60, s-maxage=300"
            etag = response.headers["ETag"]
        with urlopen(Request(base + "/sitemap.xml", method="HEAD"), timeout=2) as response:
            assert response.status == 200 and response.read() == b""
            assert int(response.headers["Content-Length"]) == len(content)
        with pytest.raises(HTTPError) as conditional:
            urlopen(Request(base + "/sitemap.xml", headers={"If-None-Match": etag}), timeout=2)
        assert conditional.value.code == 304
        with urlopen(base + "/api/v1/seo/sitemap.xml", timeout=2) as response:
            assert response.read() == content
        with pytest.raises(HTTPError) as unavailable:
            urlopen(base + "/api/v1/health/live/", timeout=2)
        assert unavailable.value.code == 503
        def read(_):
            with urlopen(base + "/sitemap.xml", timeout=2) as response:
                return response.read()
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
            assert all(body == content for body in pool.map(read, range(30)))
        # A completed replacement must invalidate a previously cached validator.
        replacement = content.replace(b'https://hawatch.ir/', b'https://hawatch.ir/routes')
        from hawatch.modules.catalog.sitemap import _atomic_write
        _atomic_write(artifact, replacement)
        with urlopen(Request(base + "/sitemap.xml", headers={"If-None-Match": etag}), timeout=2) as response:
            assert response.status == 200 and response.read() == replacement
            assert response.headers["ETag"] != etag
        artifact.chmod(0o000)
        with pytest.raises(HTTPError) as unreadable:
            urlopen(base + "/sitemap.xml", timeout=2)
        assert unreadable.value.code == 503
        assert unreadable.value.headers["Cache-Control"] == "no-store"
        artifact.unlink()
        with pytest.raises(HTTPError) as missing:
            urlopen(base + "/sitemap.xml", timeout=2)
        assert missing.value.code == 503
        assert missing.value.headers["Cache-Control"] == "no-store"
    finally:
        for name in reversed(started):
            docker("rm", "-f", name, check=False)
        docker("network", "rm", network, check=False)
