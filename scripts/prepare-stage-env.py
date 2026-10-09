"""Executed by the local deploy wrapper over SSH; never copy production secrets."""
import os
from pathlib import Path
import secrets
import sys
path = Path(sys.argv[1])
values = {}
previous = {}
if path.exists():
    for line in path.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            previous[k] = v
            if k.startswith("HAWATCH_STAGE_") or k == "HAWATCH_PUBLIC_ORIGIN":
                values[k] = v

if previous.get("POSTGRES_DB") == "hawatch_stage" and previous.get("POSTGRES_HOST") == "stage-postgres":
    for key in ("POSTGRES_PASSWORD", "DJANGO_SECRET_KEY"):
        candidate = previous.get(key, "")
        if len(candidate) >= 32 and "replace" not in candidate.lower():
            values[key] = candidate
host = os.environ.get("SSH_CONNECTION", "").split()
host = host[2] if len(host) == 4 else "127.0.0.1"
if not values.get("HAWATCH_STAGE_ORIGIN") or "SERVER_IP_OR_DOMAIN" in values["HAWATCH_STAGE_ORIGIN"]:
    values["HAWATCH_STAGE_ORIGIN"] = f"http://{host}:5050"
if not values.get("HAWATCH_STAGE_ALLOWED_HOSTS") or "SERVER_IP_OR_DOMAIN" in values["HAWATCH_STAGE_ALLOWED_HOSTS"]:
    values["HAWATCH_STAGE_ALLOWED_HOSTS"] = host
values.update(HAWATCH_STAGE_ENABLED="1", HAWATCH_STAGE_ENV_FILE=str(path),
              HAWATCH_STAGE_PORT="5050", POSTGRES_HOST="stage-postgres",
              POSTGRES_DB="hawatch_stage", POSTGRES_USER="hawatch_stage",
              DEMO_DATA_ENABLED="false", HAWATCH_BOOTSTRAP_LIVE_CATALOG_IF_EMPTY="false",
              HAWATCH_ENVIRONMENT="stage", OPEN_METEO_FORECAST_DAYS="10")
values.setdefault("HAWATCH_PUBLIC_ORIGIN", "https://hawatch.ir")
for key in ("POSTGRES_PASSWORD", "DJANGO_SECRET_KEY"):
    values.setdefault(key, secrets.token_hex(32))
fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
os.fchmod(fd, 0o600)
with os.fdopen(fd, "w") as f:
    f.write("\n".join(f"{k}={v}" for k, v in sorted(values.items())) + "\n")
