"""Run the real web and gateway configs against archived and current icons."""

from contextlib import contextmanager
from pathlib import Path
import subprocess
import time
from urllib.error import HTTPError
from urllib.request import HTTPRedirectHandler, Request, build_opener, urlopen
from uuid import uuid4

import pytest


ROOT = Path(__file__).resolve().parents[1]
IMAGE = "nginx:1.27.5-alpine"
CACHE_CONTROL = "public, max-age=3600, must-revalidate"


def docker(*args, check=True):
    return subprocess.run(
        ["docker", *args], capture_output=True, text=True, check=check, timeout=25,
    )


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        return None


@contextmanager
def response_without_redirect(request):
    try:
        response = build_opener(NoRedirect).open(request, timeout=3)
    except HTTPError as error:
        response = error
    with response:
        yield response


def test_legacy_icons_redirect_once_through_web_and_gateway(tmp_path):
    try:
        if docker("info", check=False).returncode:
            pytest.skip("Docker daemon unavailable")
        if docker("image", "inspect", IMAGE, check=False).returncode:
            pytest.skip("Nginx test image unavailable locally")
    except (OSError, subprocess.TimeoutExpired):
        pytest.skip("Docker unavailable")

    suffix = uuid4().hex[:10]
    network = f"hawatch-favicon-{suffix}"
    started = []
    api_config = tmp_path / "api.conf"
    api_config.write_text("server { listen 8000; location / { return 503; } }")
    archived = tmp_path / "public" / "test-version" / "brand"
    archived.mkdir(parents=True)
    legacy_bytes = (ROOT / "apps/web/public/brand/favicon-48.png").read_bytes()
    (archived / "favicon-48.png").write_bytes(legacy_bytes)
    try:
        docker("network", "create", network)
        for role, mounts, port in [
            ("api", [(api_config, "/etc/nginx/conf.d/default.conf")], 8000),
            ("web", [
                (ROOT / "apps/web/nginx.conf", "/etc/nginx/conf.d/default.conf"),
                (ROOT / "apps/web/nginx-public-pages.inc", "/etc/nginx/public-pages.inc"),
                (ROOT / "apps/web/public", "/usr/share/nginx/html"),
                (tmp_path / "public", "/var/lib/hawatch-frontend/static-public"),
            ], 5173),
            ("gateway", [
                (ROOT / "infra/nginx/nginx.conf", "/etc/nginx/nginx.conf"),
                (ROOT / "infra/nginx/public-pages.inc", "/etc/nginx/public-pages.inc"),
            ], 80),
        ]:
            name = f"hawatch-favicon-{role}-{suffix}"
            args = ["run", "-d", "--name", name, "--network", network,
                    "--network-alias", role, "-p", f"127.0.0.1::{port}"]
            for source, destination in mounts:
                args += ["-v", f"{source}:{destination}:ro"]
            docker(*args, IMAGE)
            started.append(name)
            docker("exec", name, "nginx", "-t")
            if role == "api":
                continue
            published = docker("port", name, str(port)).stdout.strip().rsplit(":", 1)[-1]
            base = f"http://127.0.0.1:{published}"
            for attempt in range(30):
                try:
                    with urlopen(base + "/healthz", timeout=1):
                        break
                except OSError:
                    if attempt == 29:
                        raise
                    time.sleep(.1)

            aliases = {}
            for prefix in ["/brand/", "/brand/v2/"]:
                aliases[prefix + "favicon.ico"] = "/favicon.ico"
                aliases[prefix + "apple-touch-icon.png"] = "/apple-touch-icon.png"
                for filename in ["favicon.svg", "favicon-16.png", "favicon-32.png", "favicon-48.png"]:
                    aliases[prefix + filename] = "/favicon.png"
            for source, destination in aliases.items():
                for method in ["GET", "HEAD"]:
                    request = Request(base + source + "?v=old", method=method, headers={
                        "X-Forwarded-Proto": "https", "User-Agent": "Googlebot-Image/1.0",
                    })
                    with response_without_redirect(request) as response:
                        assert response.status == 301, (role, source)
                        assert response.headers["Location"] == destination
                        assert response.headers["Cache-Control"] == CACHE_CONTROL
                        if method == "HEAD":
                            assert response.read() == b""
                with urlopen(base + source, timeout=3) as response:
                    assert response.url == base + destination
                    assert response.status == 200
                    assert response.read() == (ROOT / "apps/web/public" / destination.lstrip("/")).read_bytes()
                    assert response.headers.get_content_type().startswith("image/")
                    assert response.headers["Cache-Control"] == CACHE_CONTROL
            # Archived immutable URLs and non-icon brand assets retain their bytes.
            for path in ["/brand/v2/logo-dark.svg", "/brand/hawatch-favicon-512.png"]:
                with urlopen(base + path, timeout=3) as response:
                    assert response.status == 200
                    assert response.read() == (ROOT / "apps/web/public" / path.lstrip("/")).read_bytes()
            with urlopen(base + "/static-public/test-version/brand/favicon-48.png", timeout=3) as response:
                assert response.read() == legacy_bytes
                assert "immutable" in response.headers["Cache-Control"]
            with response_without_redirect(Request(base + "/brand/favicon-64.png")) as response:
                assert response.status == 404
    finally:
        for name in reversed(started):
            docker("rm", "-f", name, check=False)
        docker("network", "rm", network, check=False)
