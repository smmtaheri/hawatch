#!/usr/bin/env python3
"""هستهٔ پایلوت جمع‌آوری نقاط طبیعت‌گردی و کوهنوردی برای هواچ.

ویژگی‌ها:
  - منابع اصلی: OSM، GeoNames، NGA GNS، Wikidata و فهرست قله‌های ویکی‌پدیا
  - ذخیرهٔ مشاهدات خام و نقاط نرمال‌شده در SQLite با WAL
  - لاگ JSONL، لاگ خطا، heartbeat و فایل وضعیت اتمیک
  - ادامهٔ کار بعد از خطای یک منبع، retry محدود و پشتیبانی از SIGINT/SIGTERM
  - جلوگیری از اجرای هم‌زمان دو نمونه

OSM در این نسخه از PBF محلی با ابزار osmium خوانده می‌شود و به Overpass وابسته نیست؛
برای به‌روزرسانی داده‌ها باید PBF جدید جایگزین و در اجرای بعدی import شود.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import math
import os
import re
import signal
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Callable, Iterable


VERSION = "0.1.0"
DEFAULT_BBOX = (51.10, 35.70, 51.80, 36.20)  # west, south, east, north
DEFAULT_SOURCES = ("osm", "geonames", "gns", "wikidata", "wikipedia_4k")
USER_AGENT = "HawatchCoreCrawler/0.1 (+https://hawatch-weather.admirer135.chatgpt.site/)"
STOP_EVENT = threading.Event()


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


def compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str)


def as_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def as_int(value: Any) -> int | None:
    try:
        if value is None or value == "":
            return None
        return int(float(value))
    except (TypeError, ValueError):
        return None


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    text = unicodedata.normalize("NFKC", str(value))
    text = text.replace("ي", "ی").replace("ى", "ی").replace("ك", "ک")
    text = text.replace("ۀ", "هٔ").replace("ة", "ه")
    text = text.replace("ـ", "")
    text = re.sub(r"[\u064B-\u065F\u0670]", "", text)
    text = text.replace("\u200c", " ").replace("\u200d", " ")
    text = re.sub(r"[^\w\u0600-\u06ff]+", " ", text, flags=re.UNICODE)
    return re.sub(r"\s+", " ", text).strip().casefold()


def parse_bbox(value: str) -> tuple[float, float, float, float]:
    parts = [as_float(part.strip()) for part in value.split(",")]
    if len(parts) != 4 or any(part is None for part in parts):
        raise argparse.ArgumentTypeError("bbox باید به شکل west,south,east,north باشد")
    west, south, east, north = (float(part) for part in parts)
    if not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
        raise argparse.ArgumentTypeError("مقادیر bbox معتبر نیستند")
    return west, south, east, north


def inside_bbox(lat: float | None, lon: float | None, bbox: tuple[float, float, float, float]) -> bool:
    if lat is None or lon is None:
        return False
    west, south, east, north = bbox
    return south <= lat <= north and west <= lon <= east


class JsonLogger:
    def __init__(self, log_path: Path, error_path: Path):
        self.log_path = log_path
        self.error_path = error_path
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.error_path.parent.mkdir(parents=True, exist_ok=True)
        self.log_path.touch(exist_ok=True)
        self.error_path.touch(exist_ok=True)
        self._lock = threading.Lock()

    def log(self, level: str, event: str, **fields: Any) -> None:
        record = {
            "ts": utc_now(),
            "level": level,
            "event": event,
            "pid": os.getpid(),
            **fields,
        }
        line = compact_json(record) + "\n"
        with self._lock:
            with self.log_path.open("a", encoding="utf-8") as main_handle:
                main_handle.write(line)
                main_handle.flush()
            if level in {"ERROR", "CRITICAL"}:
                with self.error_path.open("a", encoding="utf-8") as error_handle:
                    error_handle.write(line)
                    error_handle.flush()
        short = f"[{record['ts']}] {level:<8} {event}"
        if fields:
            visible = " ".join(f"{key}={value}" for key, value in fields.items() if key not in {"traceback"})
            short += " " + visible[:500]
        print(short, flush=True)


class ProcessLock:
    def __init__(self, path: Path):
        self.path = path
        self.held = False

    @staticmethod
    def _pid_alive(pid: int) -> bool:
        if pid <= 0:
            return False
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False

    def acquire(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        except FileExistsError:
            try:
                old_pid = int(self.path.read_text(encoding="utf-8").strip())
            except (OSError, ValueError):
                old_pid = -1
            if self._pid_alive(old_pid):
                raise RuntimeError(f"نمونهٔ دیگری در حال اجراست؛ lock pid={old_pid}")
            self.path.unlink(missing_ok=True)
            fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(str(os.getpid()))
        self.held = True

    def release(self) -> None:
        if self.held:
            self.path.unlink(missing_ok=True)
            self.held = False


class HttpRequestError(RuntimeError):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status


def http_request(
    url: str,
    *,
    data: bytes | None = None,
    content_type: str | None = None,
    timeout: float = 60,
    retries: int = 2,
    logger: JsonLogger | None = None,
    source: str = "unknown",
) -> bytes:
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json,text/html,*/*"}
    if content_type:
        headers["Content-Type"] = content_type
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        request = urllib.request.Request(url, data=data, headers=headers, method="POST" if data else "GET")
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                body = response.read()
                if logger and attempt:
                    logger.log("INFO", "http_recovered", source=source, attempt=attempt, status=response.status)
                return body
        except urllib.error.HTTPError as exc:
            body = exc.read(1000)
            last_error = exc
            retryable = exc.code == 429 or 500 <= exc.code <= 599
            if not retryable or attempt >= retries:
                raise HttpRequestError(exc.code, f"HTTP {exc.code} from {source}: {body[:300]!r}") from exc
            retry_after = as_float(exc.headers.get("Retry-After")) if exc.headers else None
            delay = retry_after if retry_after is not None else min(30.0, 2.0**attempt)
            if logger:
                logger.log(
                    "WARNING",
                    "http_retry",
                    source=source,
                    status=exc.code,
                    attempt=attempt + 1,
                    delay_seconds=delay,
                )
            STOP_EVENT.wait(delay)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_error = exc
            if attempt >= retries:
                raise RuntimeError(f"network error from {source}: {exc}") from exc
            delay = min(30.0, 2.0**attempt)
            if logger:
                logger.log("WARNING", "network_retry", source=source, attempt=attempt + 1, delay_seconds=delay)
            STOP_EVENT.wait(delay)
    raise RuntimeError(f"request failed from {source}: {last_error}")


def http_json(url: str, **kwargs: Any) -> Any:
    body = http_request(url, **kwargs)
    try:
        return json.loads(body.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"invalid JSON from {kwargs.get('source', 'unknown')}: {exc}") from exc


def make_record(
    *,
    source: str,
    source_id: str,
    name: str,
    lat: float | None,
    lon: float | None,
    point_type: str,
    source_url: str,
    raw: Any,
    name_fa: str | None = None,
    aliases: Iterable[str] = (),
    elevation_m: float | None = None,
    coordinate_status: str = "source_coordinate",
    importance: str = "normal",
) -> dict[str, Any] | None:
    if lat is None or lon is None or not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return None
    name = str(name or "").strip()
    if not name:
        name = f"point-{source_id}"
    alias_list = [str(item).strip() for item in aliases if str(item).strip()]
    return {
        "source": source,
        "source_id": str(source_id),
        "name": name,
        "name_fa": str(name_fa).strip() if name_fa else None,
        "aliases": alias_list,
        "lat": round(float(lat), 7),
        "lon": round(float(lon), 7),
        "elevation_m": elevation_m,
        "point_type": point_type or "unknown",
        "coordinate_status": coordinate_status,
        "importance": "low" if importance == "low" else "normal",
        "source_url": source_url,
        "raw": raw,
    }


OSM_PBF_FILTERS = (
    "n/natural=peak",
    "n/natural=saddle",
    "n/natural=cliff",
    "n/natural=waterfall",
    "n/natural=cave",
    "n/natural=spring",
    "n/natural=glacier",
    "n/tourism=alpine_hut,wilderness_hut,viewpoint,camp_site,picnic_site,information",
    "n/place=hamlet,village,locality,isolated_dwelling",
    "w/route=hiking",
    "r/route=hiking",
)


def _coordinate_pairs(value: Any) -> Iterable[tuple[float, float]]:
    if isinstance(value, list) and len(value) >= 2 and all(isinstance(item, (int, float)) for item in value[:2]):
        lon, lat = as_float(value[0]), as_float(value[1])
        if lon is not None and lat is not None:
            yield lon, lat
        return
    if isinstance(value, list):
        for child in value:
            yield from _coordinate_pairs(child)


def _representative_coordinate(geometry: Any) -> tuple[float | None, float | None]:
    if not isinstance(geometry, dict):
        return None, None
    pairs = list(_coordinate_pairs(geometry.get("coordinates")))
    if not pairs:
        return None, None
    lon = sum(item[0] for item in pairs) / len(pairs)
    lat = sum(item[1] for item in pairs) / len(pairs)
    return lat, lon


def _osm_feature_to_record(feature: dict[str, Any]) -> dict[str, Any] | None:
    properties = feature.get("properties") or {}
    lat, lon = _representative_coordinate(feature.get("geometry"))
    object_type = str(properties.get("@type") or "unknown").lower()
    object_id = properties.get("@id") or feature.get("id")
    if isinstance(object_id, str) and object_id[:1] in {"n", "w", "r"} and object_id[1:].isdigit():
        object_type = {"n": "node", "w": "way", "r": "relation"}.get(object_id[:1], object_type)
        object_id = object_id[1:]
    if object_id is None:
        return None
    source_id = f"{object_type}:{object_id}"
    tags = {str(key): value for key, value in properties.items() if not str(key).startswith("@")}
    name_fa = tags.get("name:fa") or tags.get("name:fa_IR")
    name_en = tags.get("name:en")
    display_name = tags.get("name") or name_fa or name_en
    named = bool(str(display_name or "").strip())
    if not named:
        display_name = f"OSM {source_id}"
    point_type = tags.get("natural") or tags.get("tourism") or tags.get("place") or tags.get("route") or "unknown"
    aliases = [
        tags.get(key)
        for key in ("name:fa", "name:fa_IR", "name:en", "alt_name", "official_name", "loc_name", "old_name")
    ]
    raw = {
        "type": feature.get("type"),
        "id": feature.get("id"),
        "geometry": feature.get("geometry"),
        "properties": properties,
    }
    return make_record(
        source="osm",
        source_id=source_id,
        name=str(display_name),
        name_fa=name_fa,
        aliases=[item for item in aliases if item],
        lat=lat,
        lon=lon,
        elevation_m=as_float(tags.get("ele")),
        point_type=str(point_type),
        coordinate_status="osm_pbf_candidate" if named else "osm_pbf_candidate_low",
        importance="normal" if named else "low",
        source_url=f"https://www.openstreetmap.org/{object_type}/{object_id}",
        raw=raw,
    )


def extract_osm(
    pbf_path: Path,
    max_records: int,
    timeout_seconds: float,
    cache_dir: Path,
    logger: JsonLogger,
) -> list[dict[str, Any]]:
    if not pbf_path.is_file():
        raise FileNotFoundError(f"OSM PBF پیدا نشد: {pbf_path}")
    if max_records < 0:
        raise ValueError("max_records برای OSM نمی‌تواند منفی باشد")
    command_timeout = max(60.0, float(timeout_seconds))
    cache_dir.mkdir(parents=True, exist_ok=True)
    logger.log(
        "INFO",
        "osm_pbf_started",
        pbf=str(pbf_path),
        pbf_bytes=pbf_path.stat().st_size,
        max_records=max_records,
        command_timeout_seconds=command_timeout,
        filters=list(OSM_PBF_FILTERS),
    )
    try:
        with tempfile.TemporaryDirectory(prefix="hawatch-osm-pbf-", dir=str(cache_dir)) as temp_dir:
            temp_root = Path(temp_dir)
            filtered_pbf = temp_root / "relevant.osm.pbf"
            geojson_path = temp_root / "relevant.geojson"
            filter_command = [
                "osmium",
                "tags-filter",
                "--no-progress",
                str(pbf_path),
                *OSM_PBF_FILTERS,
                "-o",
                str(filtered_pbf),
            ]
            filtered = subprocess.run(
                filter_command,
                check=True,
                capture_output=True,
                text=True,
                timeout=command_timeout,
            )
            logger.log(
                "INFO",
                "osm_pbf_filtered",
                filtered_bytes=filtered_pbf.stat().st_size,
                stderr=filtered.stderr[-1000:] if filtered.stderr else None,
            )
            export_command = [
                "osmium",
                "export",
                "--no-progress",
                "-u",
                "type_id",
                "-a",
                "type,id",
                str(filtered_pbf),
                "-f",
                "geojson",
                "-o",
                str(geojson_path),
            ]
            exported = subprocess.run(
                export_command,
                check=True,
                capture_output=True,
                text=True,
                timeout=command_timeout,
            )
            payload = json.loads(geojson_path.read_text(encoding="utf-8"))
            features = payload.get("features") or []
            records: list[dict[str, Any]] = []
            unnamed = 0
            geometryless = 0
            for feature in features:
                record = _osm_feature_to_record(feature)
                if record is None:
                    geometryless += 1
                    continue
                if record.get("importance") == "low":
                    unnamed += 1
                records.append(record)
                if max_records and len(records) >= max_records:
                    break
            logger.log(
                "INFO",
                "osm_pbf_exported",
                exported_features=len(features),
                accepted_records=len(records),
                unnamed_records=unnamed,
                geometryless_features=geometryless,
                geojson_bytes=geojson_path.stat().st_size,
                stderr=exported.stderr[-1000:] if exported.stderr else None,
            )
            logger.log(
                "INFO",
                "osm_pbf_completed",
                returned_records=len(records),
                named_records=len(records) - unnamed,
                unnamed_records=unnamed,
            )
            return records
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"osmium برای OSM PBF از timeout گذشت: {exc}") from exc
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or "").strip()[-2000:]
        raise RuntimeError(f"osmium برای OSM PBF شکست خورد: {detail}") from exc


GEONAMES_CODES = {
    "CAVE", "CMP", "FLLS", "GLCR", "HLL", "HLLS", "LK", "LKI", "LKN", "LKS",
    "MT", "MTS", "PASS", "PK", "PKS", "PRK", "RDGE", "RESF", "RESN", "RESW",
    "RPDS", "SDL", "SPNG", "SPNS", "SPNT", "VAL", "VLC", "WTRC",
}


def extract_geonames(
    bbox: tuple[float, float, float, float], max_records: int, timeout: float, cache_dir: Path, logger: JsonLogger
) -> list[dict[str, Any]]:
    cache_dir.mkdir(parents=True, exist_ok=True)
    zip_path = cache_dir / "IR.zip"
    if not zip_path.exists():
        zip_path.write_bytes(
            http_request(
                "https://download.geonames.org/export/dump/IR.zip",
                timeout=max(timeout, 60),
                retries=2,
                logger=logger,
                source="geonames",
            )
        )
    records: list[dict[str, Any]] = []
    with zipfile.ZipFile(zip_path) as archive:
        names = [name for name in archive.namelist() if name.lower().endswith("ir.txt")]
        if not names:
            names = [name for name in archive.namelist() if name.endswith(".txt") and "readme" not in name.lower()]
        if not names:
            raise RuntimeError("GeoNames IR.zip فایل متنی ندارد")
        with archive.open(names[0]) as handle:
            for raw_line in handle:
                if STOP_EVENT.is_set():
                    break
                cols = raw_line.decode("utf-8", errors="replace").rstrip("\n").split("\t")
                if len(cols) < 19 or cols[7] not in GEONAMES_CODES:
                    continue
                lat, lon = as_float(cols[4]), as_float(cols[5])
                if not inside_bbox(lat, lon, bbox):
                    continue
                name, asciiname = cols[1], cols[2]
                record = make_record(
                    source="geonames",
                    source_id=cols[0],
                    name=name or asciiname,
                    name_fa=name if re.search(r"[\u0600-\u06ff]", name) else None,
                    aliases=[asciiname, cols[3]],
                    lat=lat,
                    lon=lon,
                    elevation_m=as_float(cols[15]),
                    point_type=cols[7],
                    coordinate_status="geonames_coordinate",
                    source_url=f"https://www.geonames.org/{cols[0]}/",
                    raw={"geonames_columns": cols},
                )
                if record:
                    records.append(record)
    records.sort(key=lambda item: (item["elevation_m"] is None, -(item["elevation_m"] or 0)))
    return records[:max_records]


GNS_LAYERS = (6,)


def extract_gns(
    bbox: tuple[float, float, float, float], max_records: int, timeout: float, logger: JsonLogger
) -> list[dict[str, Any]]:
    west, south, east, north = bbox
    base = "https://geonames.nga.mil/geon-ags/rest/services/visualizationNonScaled/GeoNamesFeatureClass/MapServer"
    records: list[dict[str, Any]] = []
    failures: list[str] = []
    for layer in GNS_LAYERS:
        if len(records) >= max_records or STOP_EVENT.is_set():
            break
        page_size = min(1000, max(200, max_records))
        offset = 0
        page_number = 0
        max_pages = 100
        groups: dict[str, dict[str, Any]] = {}
        seen_page_signatures: set[tuple[str, ...]] = set()
        base_params = {
            "where": "cc_ft = 'IRN' AND term_dt_f IS NULL AND term_dt_n IS NULL",
            "outFields": "ufi,uni,full_name,full_nm_nd,nt,lat_dd,long_dd,desig_cd,fc,adm1,lang_cd,mod_dt_ft",
            "returnGeometry": "false",
            "f": "json",
            "resultRecordCount": str(page_size),
            "geometry": f"{west},{south},{east},{north}",
            "geometryType": "esriGeometryEnvelope",
            "inSR": "4326",
            "spatialRel": "esriSpatialRelIntersects",
        }
        while not STOP_EVENT.is_set() and page_number < max_pages:
            params = {**base_params, "resultOffset": str(offset)}
            url = f"{base}/{layer}/query?{urllib.parse.urlencode(params)}"
            try:
                payload = http_json(url, timeout=timeout, retries=2, logger=logger, source="gns")
            except Exception as exc:  # one unavailable layer must not kill the source
                failures.append(f"layer={layer},offset={offset}: {exc}")
                break
            features = payload.get("features") or []
            if not features:
                break
            page_number += 1
            signature = tuple(compact_json(feature.get("attributes") or {}) for feature in features)
            if signature in seen_page_signatures:
                failures.append(f"layer={layer},offset={offset}: repeated pagination page")
                break
            seen_page_signatures.add(signature)
            for index, feature in enumerate(features):
                attrs = feature.get("attributes") or {}
                ufi = str(attrs.get("ufi") or "").strip()
                group_key = f"{layer}:{ufi}" if ufi else f"{layer}:feature:{offset + index}"
                group = groups.setdefault(group_key, {"ufi": ufi, "names": [], "attributes": []})
                group["attributes"].append(attrs)
                for field in ("full_name", "full_nm_nd"):
                    value = str(attrs.get(field) or "").strip()
                    if value and value not in group["names"]:
                        group["names"].append(value)
            logger.log(
                "INFO",
                "gns_page_fetched",
                layer=layer,
                page=page_number,
                offset=offset,
                fetched_records=len(features),
                grouped_points=len(groups),
                exceeded_transfer_limit=bool(payload.get("exceededTransferLimit")),
            )
            offset += len(features)
            if len(features) < page_size and not payload.get("exceededTransferLimit"):
                break
        if page_number >= max_pages:
            failures.append(f"layer={layer}: pagination exceeded {max_pages} pages")

        for group_key, group in groups.items():
            attrs_list = group["attributes"]
            names = group["names"]
            primary = attrs_list[0] if attrs_list else {}
            coordinates = [
                (as_float(attrs.get("lat_dd")), as_float(attrs.get("long_dd")))
                for attrs in attrs_list
            ]
            lat, lon = next(
                (
                    (candidate_lat, candidate_lon)
                    for candidate_lat, candidate_lon in coordinates
                    if inside_bbox(candidate_lat, candidate_lon, bbox)
                ),
                (None, None),
            )
            if lat is None or lon is None:
                continue
            name = names[0] if names else str(primary.get("uni") or group["ufi"] or group_key)
            name_fa = next((item for item in names if re.search(r"[\u0600-\u06ff]", item)), None)
            aliases = [item for item in names if item != name]
            point_type = next(
                (
                    attrs.get("desig_cd") or attrs.get("fc")
                    for attrs in attrs_list
                    if attrs.get("desig_cd") or attrs.get("fc")
                ),
                f"gns_layer_{layer}",
            )
            record = make_record(
                source="gns",
                source_id=group_key,
                name=name,
                name_fa=name_fa,
                aliases=aliases,
                lat=lat,
                lon=lon,
                point_type=point_type,
                coordinate_status="gns_coordinate",
                source_url="https://geonames.nga.mil/gns/html/",
                raw={"ufi": group["ufi"], "names": names, "attributes": attrs_list},
            )
            if record:
                records.append(record)
            if len(records) >= max_records:
                break
    if not records and failures:
        raise RuntimeError("GNS همهٔ لایه‌ها خطا دادند: " + " | ".join(failures))
    return records[:max_records]


def extract_wikidata(
    bbox: tuple[float, float, float, float], max_records: int, timeout: float, logger: JsonLogger
) -> list[dict[str, Any]]:
    west, south, east, north = bbox
    query = f"""
SELECT ?item ?itemLabel ?coord ?elev ?class ?classLabel WHERE {{
  VALUES ?class {{ wd:Q8502 wd:Q46831 wd:Q35509 wd:Q39816 wd:Q16521 wd:Q23413 wd:Q35120 }}
  ?item wdt:P17 wd:Q794;
        wdt:P625 ?coord;
        wdt:P31 ?class.
  BIND(geof:latitude(?coord) AS ?lat)
  BIND(geof:longitude(?coord) AS ?lon)
  FILTER(?lat >= {south} && ?lat <= {north} && ?lon >= {west} && ?lon <= {east})
  OPTIONAL {{ ?item wdt:P2044 ?elev. }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "fa,en". }}
}}
LIMIT {min(max(100, max_records * 3), 1000)}
""".strip()
    url = "https://query.wikidata.org/sparql?" + urllib.parse.urlencode({"query": query, "format": "json"})
    payload = http_json(url, timeout=max(timeout, 60), retries=2, logger=logger, source="wikidata")
    records: list[dict[str, Any]] = []
    for binding in payload.get("results", {}).get("bindings", []):
        coord = binding.get("coord", {}).get("value", "")
        match = re.search(r"Point\(([-0-9.]+) ([-0-9.]+)\)", coord)
        if not match:
            continue
        lon, lat = float(match.group(1)), float(match.group(2))
        item_url = binding.get("item", {}).get("value", "")
        name = binding.get("itemLabel", {}).get("value", "")
        class_name = binding.get("classLabel", {}).get("value", "natural point")
        record = make_record(
            source="wikidata",
            source_id=item_url.rsplit("/", 1)[-1],
            name=name,
            name_fa=name if re.search(r"[\u0600-\u06ff]", name) else None,
            lat=lat,
            lon=lon,
            elevation_m=as_float(binding.get("elev", {}).get("value")),
            point_type=class_name,
            coordinate_status="wikidata_coordinate",
            source_url=item_url,
            raw=binding,
        )
        if record:
            records.append(record)
        if len(records) >= max_records:
            break
    return records


def parse_dms(value: str) -> float | None:
    text = html.unescape(re.sub(r"<[^>]+>", " ", value)).replace("−", "-")
    text = re.sub(r"\[[^]]+\]", "", text)
    match = re.search(r"([+-]?\d{1,3})[^0-9]+(\d{1,2})?[^0-9]+(\d{1,2}(?:\.\d+)?)?\s*([NSWE])?", text, re.I)
    if not match:
        decimal = re.search(r"([+-]?\d{1,3}(?:\.\d+)?)", text)
        return float(decimal.group(1)) if decimal else None
    degrees = float(match.group(1))
    minutes = float(match.group(2) or 0)
    seconds = float(match.group(3) or 0)
    result = abs(degrees) + minutes / 60 + seconds / 3600
    if degrees < 0 or (match.group(4) or "").upper() in {"S", "W"}:
        result *= -1
    return result


class WikiTableParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows: list[list[str]] = []
        self._table_depth = 0
        self._in_table = False
        self._row: list[str] | None = None
        self._cell: list[str] | None = None
        self._skip = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_map = dict(attrs)
        if tag == "table" and "wikitable" in (attrs_map.get("class") or ""):
            self._table_depth += 1
            self._in_table = True
        elif self._in_table and tag == "tr":
            self._row = []
        elif self._in_table and tag in {"td", "th"} and self._row is not None:
            self._cell = []
        elif self._in_table and tag in {"sup", "style", "script"}:
            self._skip += 1

    def handle_endtag(self, tag: str) -> None:
        if self._in_table and tag in {"sup", "style", "script"} and self._skip:
            self._skip -= 1
        elif self._in_table and tag in {"td", "th"} and self._cell is not None and self._row is not None:
            self._row.append(re.sub(r"\s+", " ", "".join(self._cell)).strip())
            self._cell = None
        elif self._in_table and tag == "tr":
            if self._row:
                self.rows.append(self._row)
            self._row = None
        elif tag == "table" and self._in_table:
            self._table_depth -= 1
            if self._table_depth <= 0:
                self._in_table = False

    def handle_data(self, data: str) -> None:
        if self._in_table and self._cell is not None and not self._skip:
            self._cell.append(data)


def extract_wikipedia(
    bbox: tuple[float, float, float, float], max_records: int, timeout: float, logger: JsonLogger
) -> list[dict[str, Any]]:
    url = "https://en.wikipedia.org/wiki/List_of_Iranian_four-thousanders"
    body = http_request(url, timeout=timeout, retries=2, logger=logger, source="wikipedia_4k")
    parser = WikiTableParser()
    parser.feed(body.decode("utf-8", errors="replace"))
    records: list[dict[str, Any]] = []
    for row in parser.rows:
        if len(row) < 9 or not re.match(r"^\d+\.?$", row[0]):
            continue
        lat = parse_dms(row[6])
        lon = parse_dms(row[7])
        if lat is None or lon is None or not inside_bbox(lat, lon, bbox):
            continue
        name = row[1]
        name_fa = row[2] if re.search(r"[\u0600-\u06ff]", row[2]) else None
        record = make_record(
            source="wikipedia_4k",
            source_id=row[0],
            name=name,
            name_fa=name_fa,
            aliases=[row[2]],
            lat=lat,
            lon=lon,
            elevation_m=as_float(re.search(r"[0-9][0-9,]*", row[3]).group(0).replace(",", "")) if re.search(r"[0-9][0-9,]*", row[3]) else None,
            point_type="four_thousander",
            coordinate_status="wikipedia_dms_coordinate",
            source_url=url,
            raw={"row": row},
        )
        if record:
            records.append(record)
        if len(records) >= max_records:
            break
    return records


SOURCE_EXTRACTORS: dict[str, Callable[..., list[dict[str, Any]]]] = {
    "osm": extract_osm,
    "geonames": extract_geonames,
    "gns": extract_gns,
    "wikidata": extract_wikidata,
    "wikipedia_4k": extract_wikipedia,
}


SCHEMA = """
CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS runs (
  run_id TEXT PRIMARY KEY,
  started_at TEXT NOT NULL,
  finished_at TEXT,
  status TEXT NOT NULL,
  duration_seconds REAL,
  bbox TEXT NOT NULL,
  sources TEXT NOT NULL,
  total_observations INTEGER NOT NULL DEFAULT 0,
  total_candidates INTEGER NOT NULL DEFAULT 0,
  successful_sources INTEGER NOT NULL DEFAULT 0,
  failed_sources INTEGER NOT NULL DEFAULT 0,
  error_count INTEGER NOT NULL DEFAULT 0,
  new_points INTEGER NOT NULL DEFAULT 0,
  matched_points INTEGER NOT NULL DEFAULT 0,
  duplicate_records INTEGER NOT NULL DEFAULT 0,
  unnamed_records INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS source_runs (
  run_id TEXT NOT NULL,
  source TEXT NOT NULL,
  started_at TEXT NOT NULL,
  finished_at TEXT,
  status TEXT NOT NULL,
  fetched_records INTEGER NOT NULL DEFAULT 0,
  inserted_observations INTEGER NOT NULL DEFAULT 0,
  new_points INTEGER NOT NULL DEFAULT 0,
  matched_points INTEGER NOT NULL DEFAULT 0,
  duplicate_records INTEGER NOT NULL DEFAULT 0,
  unnamed_records INTEGER NOT NULL DEFAULT 0,
  error_message TEXT,
  PRIMARY KEY (run_id, source),
  FOREIGN KEY (run_id) REFERENCES runs(run_id)
);
CREATE TABLE IF NOT EXISTS points (
  candidate_key TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  name_fa TEXT,
  normalized_name TEXT NOT NULL,
  aliases_json TEXT NOT NULL,
  point_type TEXT NOT NULL,
  lat REAL NOT NULL,
  lon REAL NOT NULL,
  elevation_m REAL,
  coordinate_status TEXT NOT NULL,
  importance TEXT NOT NULL DEFAULT 'normal',
  first_seen_at TEXT NOT NULL,
  last_seen_at TEXT NOT NULL,
  observation_count INTEGER NOT NULL DEFAULT 0,
  source_count INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS observations (
  observation_id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id TEXT NOT NULL,
  source TEXT NOT NULL,
  source_id TEXT NOT NULL,
  candidate_key TEXT NOT NULL,
  name TEXT NOT NULL,
  name_fa TEXT,
  lat REAL NOT NULL,
  lon REAL NOT NULL,
  elevation_m REAL,
  point_type TEXT NOT NULL,
  coordinate_status TEXT NOT NULL,
  importance TEXT NOT NULL DEFAULT 'normal',
  source_url TEXT NOT NULL,
  raw_json TEXT NOT NULL,
  observed_at TEXT NOT NULL,
  UNIQUE(run_id, source, source_id),
  FOREIGN KEY (run_id) REFERENCES runs(run_id),
  FOREIGN KEY (candidate_key) REFERENCES points(candidate_key)
);
CREATE TABLE IF NOT EXISTS point_sources (
  candidate_key TEXT NOT NULL,
  source TEXT NOT NULL,
  source_id TEXT NOT NULL,
  first_seen_at TEXT NOT NULL,
  last_seen_at TEXT NOT NULL,
  PRIMARY KEY (candidate_key, source, source_id),
  FOREIGN KEY (candidate_key) REFERENCES points(candidate_key)
);
CREATE INDEX IF NOT EXISTS idx_points_name ON points(normalized_name);
CREATE INDEX IF NOT EXISTS idx_points_coords ON points(lat, lon);
CREATE INDEX IF NOT EXISTS idx_observations_source ON observations(source, observed_at);
"""


def open_database(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=30000")
    conn.executescript(SCHEMA)
    migrations = {
        "runs": {
            "new_points": "INTEGER NOT NULL DEFAULT 0",
            "matched_points": "INTEGER NOT NULL DEFAULT 0",
            "duplicate_records": "INTEGER NOT NULL DEFAULT 0",
            "unnamed_records": "INTEGER NOT NULL DEFAULT 0",
        },
        "source_runs": {
            "new_points": "INTEGER NOT NULL DEFAULT 0",
            "matched_points": "INTEGER NOT NULL DEFAULT 0",
            "duplicate_records": "INTEGER NOT NULL DEFAULT 0",
            "unnamed_records": "INTEGER NOT NULL DEFAULT 0",
        },
        "points": {"importance": "TEXT NOT NULL DEFAULT 'normal'"},
        "observations": {"importance": "TEXT NOT NULL DEFAULT 'normal'"},
    }
    for table, columns in migrations.items():
        existing = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
        for column, definition in columns.items():
            if column not in existing:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
    conn.execute("INSERT OR REPLACE INTO metadata(key,value) VALUES('schema_version',?)", (VERSION,))
    conn.commit()
    return conn


def candidate_key(record: dict[str, Any]) -> tuple[str, str]:
    preferred_name = record.get("name_fa") or record.get("name") or ""
    normalized = normalize_text(preferred_name)
    lat_bucket = round(float(record["lat"]), 3)
    lon_bucket = round(float(record["lon"]), 3)
    raw_key = f"{normalized}|{record.get('point_type','unknown')}|{lat_bucket:.3f}|{lon_bucket:.3f}"
    digest = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()[:24]
    return f"pt_{digest}", normalized


def _stored_aliases(value: Any) -> list[str]:
    try:
        decoded = json.loads(value or "[]") if isinstance(value, str) else value
    except (TypeError, ValueError, json.JSONDecodeError):
        decoded = []
    return [str(item).strip() for item in (decoded or []) if str(item).strip()]


def _approx_distance_sq(lat_a: float, lon_a: float, lat_b: float, lon_b: float) -> float:
    latitude_scale = max(0.2, abs(math.cos(math.radians((lat_a + lat_b) / 2))))
    return ((lat_a - lat_b) ** 2) + (((lon_a - lon_b) * latitude_scale) ** 2)


def resolve_candidate_key(conn: sqlite3.Connection, record: dict[str, Any]) -> tuple[str, str | None]:
    generated_key, normalized_name = candidate_key(record)
    exact = conn.execute("SELECT candidate_key FROM points WHERE candidate_key=?", (generated_key,)).fetchone()
    if exact:
        return exact[0], "candidate_key"

    is_named = record.get("importance") != "low"
    names = {
        normalize_text(record.get("name")),
        normalize_text(record.get("name_fa")),
        *(normalize_text(alias) for alias in record.get("aliases", [])),
    }
    names.discard("")
    latitude = float(record["lat"])
    longitude = float(record["lon"])
    name_radius = 0.02 if is_named else 0.0015
    rows = conn.execute(
        """
        SELECT candidate_key,name,name_fa,aliases_json,lat,lon
        FROM points
        WHERE lat BETWEEN ? AND ? AND lon BETWEEN ? AND ?
        """,
        (latitude - name_radius, latitude + name_radius, longitude - name_radius, longitude + name_radius),
    ).fetchall()
    best: tuple[float, str] | None = None
    for key, name, name_fa, aliases_json, point_lat, point_lon in rows:
        distance = _approx_distance_sq(latitude, longitude, float(point_lat), float(point_lon))
        if is_named:
            point_names = {
                normalize_text(name),
                normalize_text(name_fa),
                *(normalize_text(alias) for alias in _stored_aliases(aliases_json)),
            }
            point_names.discard("")
            if not names.intersection(point_names):
                continue
        if best is None or distance < best[0]:
            best = (distance, key)
    if best is not None:
        return best[1], "name_coordinate" if is_named else "coordinate"
    return generated_key, None


def save_records(
    conn: sqlite3.Connection,
    run_id: str,
    source: str,
    records: list[dict[str, Any]],
    observed_at: str,
) -> tuple[int, int, dict[str, int]]:
    inserted = 0
    candidates: set[str] = set()
    metrics = {
        "new_points": 0,
        "matched_points": 0,
        "duplicate_records": 0,
        "unnamed_records": 0,
    }
    seen_source_ids: set[str] = set()
    with conn:
        for record in records:
            key, match_kind = resolve_candidate_key(conn, record)
            existing = conn.execute(
                "SELECT aliases_json,importance FROM points WHERE candidate_key=?", (key,)
            ).fetchone()
            if existing:
                metrics["matched_points"] += 1
            else:
                metrics["new_points"] += 1
            if record.get("importance") == "low":
                metrics["unnamed_records"] += 1
            prior_source = conn.execute(
                "SELECT 1 FROM point_sources WHERE candidate_key=? AND source=? AND source_id=?",
                (key, source, record["source_id"]),
            ).fetchone()
            if prior_source or record["source_id"] in seen_source_ids:
                metrics["duplicate_records"] += 1
            seen_source_ids.add(record["source_id"])
            candidates.add(key)
            aliases = list(dict.fromkeys([*(_stored_aliases(existing[0]) if existing else []), *record.get("aliases", []), record.get("name") or ""]))
            importance = "normal" if (existing and existing[1] == "normal") or record.get("importance") != "low" else "low"
            conn.execute(
                """
                INSERT INTO points(candidate_key,name,name_fa,normalized_name,aliases_json,point_type,lat,lon,elevation_m,coordinate_status,importance,first_seen_at,last_seen_at,observation_count,source_count)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,0,0)
                ON CONFLICT(candidate_key) DO UPDATE SET
                  name=CASE WHEN excluded.name_fa IS NOT NULL AND (points.name_fa IS NULL OR points.name_fa='') THEN excluded.name_fa ELSE points.name END,
                  name_fa=COALESCE(points.name_fa,excluded.name_fa),
                  aliases_json=excluded.aliases_json,
                  elevation_m=COALESCE(points.elevation_m,excluded.elevation_m),
                  last_seen_at=excluded.last_seen_at,
                  importance=CASE WHEN points.importance='normal' OR excluded.importance='normal' THEN 'normal' ELSE 'low' END
                """,
                (key, record["name"], record.get("name_fa"), normalize_text(record.get("name_fa") or record.get("name") or ""), compact_json(aliases), record["point_type"], record["lat"], record["lon"], record.get("elevation_m"), record["coordinate_status"], importance, observed_at, observed_at),
            )
            cursor = conn.execute(
                """
                INSERT OR IGNORE INTO observations(run_id,source,source_id,candidate_key,name,name_fa,lat,lon,elevation_m,point_type,coordinate_status,importance,source_url,raw_json,observed_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (run_id, source, record["source_id"], key, record["name"], record.get("name_fa"), record["lat"], record["lon"], record.get("elevation_m"), record["point_type"], record["coordinate_status"], record.get("importance", "normal"), record["source_url"], compact_json(record["raw"]), observed_at),
            )
            if cursor.rowcount:
                inserted += 1
                conn.execute("UPDATE points SET observation_count=observation_count+1 WHERE candidate_key=?", (key,))
            conn.execute(
                """
                INSERT INTO point_sources(candidate_key,source,source_id,first_seen_at,last_seen_at)
                VALUES(?,?,?,?,?)
                ON CONFLICT(candidate_key,source,source_id) DO UPDATE SET last_seen_at=excluded.last_seen_at
                """,
                (key, source, record["source_id"], observed_at, observed_at),
            )
        for key in candidates:
            conn.execute(
                "UPDATE points SET source_count=(SELECT COUNT(DISTINCT source) FROM point_sources WHERE candidate_key=?) WHERE candidate_key=?",
                (key, key),
            )
    return len(records), inserted, metrics


def new_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + os.urandom(3).hex()


def run_cycle(
    conn: sqlite3.Connection,
    logger: JsonLogger,
    bbox: tuple[float, float, float, float],
    sources: list[str],
    max_records: int,
    timeout: float,
    cache_dir: Path,
    osm_pbf: Path,
    osm_max_records: int = 0,
    osm_pbf_timeout_seconds: float = 900.0,
) -> dict[str, Any]:
    run_id = new_run_id()
    started_monotonic = time.monotonic()
    started_at = utc_now()
    bbox_text = ",".join(str(item) for item in bbox)
    conn.execute(
        "INSERT INTO runs(run_id,started_at,status,bbox,sources) VALUES(?,?,?,?,?)",
        (run_id, started_at, "running", bbox_text, compact_json(sources)),
    )
    conn.commit()
    logger.log("INFO", "run_started", run_id=run_id, sources=sources, bbox=bbox_text, max_records_per_source=max_records)
    total_observations = 0
    total_candidates = 0
    successful = 0
    failed = 0
    errors = 0
    total_new_points = 0
    total_matched_points = 0
    total_duplicate_records = 0
    total_unnamed_records = 0
    for source in sources:
        if STOP_EVENT.is_set():
            break
        source_started = utc_now()
        conn.execute("INSERT INTO source_runs(run_id,source,started_at,status) VALUES(?,?,?,?)", (run_id, source, source_started, "running"))
        conn.commit()
        logger.log("INFO", "source_started", run_id=run_id, source=source)
        try:
            extractor = SOURCE_EXTRACTORS[source]
            if source == "geonames":
                records = extractor(bbox, max_records, timeout, cache_dir, logger)
            elif source == "osm":
                records = extractor(osm_pbf, osm_max_records, osm_pbf_timeout_seconds, cache_dir, logger)
            else:
                records = extractor(bbox, max_records, timeout, logger)
            fetched, inserted, metrics = save_records(conn, run_id, source, records, utc_now())
            conn.execute(
                """
                UPDATE source_runs
                SET finished_at=?,status=?,fetched_records=?,inserted_observations=?,
                    new_points=?,matched_points=?,duplicate_records=?,unnamed_records=?
                WHERE run_id=? AND source=?
                """,
                (utc_now(), "succeeded", fetched, inserted, metrics["new_points"], metrics["matched_points"], metrics["duplicate_records"], metrics["unnamed_records"], run_id, source),
            )
            conn.commit()
            total_observations += inserted
            total_candidates += fetched
            successful += 1
            total_new_points += metrics["new_points"]
            total_matched_points += metrics["matched_points"]
            total_duplicate_records += metrics["duplicate_records"]
            total_unnamed_records += metrics["unnamed_records"]
            logger.log("INFO", "source_succeeded", run_id=run_id, source=source, fetched_records=fetched, inserted_observations=inserted, **metrics)
        except Exception as exc:
            failed += 1
            errors += 1
            message = str(exc)
            conn.execute(
                "UPDATE source_runs SET finished_at=?,status=?,error_message=? WHERE run_id=? AND source=?",
                (utc_now(), "failed", message[:2000], run_id, source),
            )
            conn.commit()
            logger.log("ERROR", "source_failed", run_id=run_id, source=source, error=message)
    duration = round(time.monotonic() - started_monotonic, 3)
    status = "stopped" if STOP_EVENT.is_set() else ("completed" if failed == 0 else "completed_with_errors")
    conn.execute(
        """
        UPDATE runs SET finished_at=?,status=?,duration_seconds=?,total_observations=?,total_candidates=?,successful_sources=?,failed_sources=?,error_count=?,new_points=?,matched_points=?,duplicate_records=?,unnamed_records=? WHERE run_id=?
        """,
        (utc_now(), status, duration, total_observations, total_candidates, successful, failed, errors, total_new_points, total_matched_points, total_duplicate_records, total_unnamed_records, run_id),
    )
    conn.commit()
    summary = {
        "run_id": run_id,
        "status": status,
        "duration_seconds": duration,
        "fetched_records": total_candidates,
        "inserted_observations": total_observations,
        "successful_sources": successful,
        "failed_sources": failed,
        "error_count": errors,
        "new_points": total_new_points,
        "matched_points": total_matched_points,
        "duplicate_records": total_duplicate_records,
        "unnamed_records": total_unnamed_records,
    }
    logger.log("INFO" if status == "completed" else "WARNING", "run_finished", **summary)
    return summary


def db_summary(conn: sqlite3.Connection) -> dict[str, Any]:
    def one(query: str) -> int:
        return int(conn.execute(query).fetchone()[0])

    return {
        "runs": one("SELECT COUNT(*) FROM runs"),
        "completed_runs": one("SELECT COUNT(*) FROM runs WHERE status='completed'"),
        "runs_with_errors": one("SELECT COUNT(*) FROM runs WHERE status='completed_with_errors'"),
        "failed_sources": one("SELECT COUNT(*) FROM source_runs WHERE status='failed'"),
        "candidate_points": one("SELECT COUNT(*) FROM points"),
        "observations": one("SELECT COUNT(*) FROM observations"),
        "sources_represented": one("SELECT COUNT(DISTINCT source) FROM observations"),
    }


def write_state(path: Path, state: dict[str, Any]) -> None:
    atomic_write_json(path, state)


def handle_signal(signum: int, _frame: Any) -> None:
    STOP_EVENT.set()
    print(f"signal={signum}; shutdown requested", flush=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="هستهٔ پایلوت crawler هواچ با SQLite")
    parser.add_argument("--version", action="version", version=VERSION)
    parser.add_argument("--db", type=Path, default=Path("data/hawatch-core.sqlite3"))
    parser.add_argument("--log", type=Path, default=Path("logs/hawatch-core.jsonl"))
    parser.add_argument("--error-log", type=Path, default=Path("logs/hawatch-core-error.jsonl"))
    parser.add_argument("--state", type=Path, default=Path("state/hawatch-core-state.json"))
    parser.add_argument("--cache-dir", type=Path, default=Path("cache"))
    parser.add_argument("--lock", type=Path, default=Path("state/hawatch-core.lock"))
    parser.add_argument("--bbox", type=parse_bbox, default=DEFAULT_BBOX, help="west,south,east,north")
    parser.add_argument("--sources", default=",".join(DEFAULT_SOURCES), help="comma-separated source names")
    parser.add_argument("--max-records-per-source", type=int, default=500)
    parser.add_argument("--timeout", type=float, default=60)
    parser.add_argument(
        "--osm-pbf",
        type=Path,
        default=Path("data/osm/iran-260824.osm.pbf"),
        help="مسیر PBF محلی OSM",
    )
    parser.add_argument(
        "--osm-max-records",
        type=int,
        default=0,
        help="سقف رکوردهای OSM؛ صفر یعنی همهٔ رکوردهای مرتبط",
    )
    parser.add_argument(
        "--osm-pbf-timeout-seconds",
        type=float,
        default=900.0,
        help="سقف زمانی هر مرحلهٔ osmium برای import PBF",
    )
    parser.add_argument("--duration-seconds", type=float, default=3600)
    parser.add_argument("--cycle-interval-seconds", type=float, default=900)
    parser.add_argument("--heartbeat-seconds", type=float, default=30)
    parser.add_argument("--once", action="store_true", help="فقط یک چرخه اجرا شود")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    sources = [item.strip() for item in args.sources.split(",") if item.strip()]
    unknown = sorted(set(sources) - set(SOURCE_EXTRACTORS))
    if unknown:
        print(f"منبع ناشناخته: {', '.join(unknown)}", file=sys.stderr)
        return 2
    if args.max_records_per_source < 1:
        print("--max-records-per-source باید حداقل ۱ باشد", file=sys.stderr)
        return 2
    if args.osm_max_records < 0:
        print("--osm-max-records نمی‌تواند منفی باشد", file=sys.stderr)
        return 2
    if args.osm_pbf_timeout_seconds <= 0:
        print("--osm-pbf-timeout-seconds باید مثبت باشد", file=sys.stderr)
        return 2
    logger = JsonLogger(args.log, args.error_log)
    lock = ProcessLock(args.lock)
    try:
        lock.acquire()
    except RuntimeError as exc:
        logger.log("ERROR", "lock_failed", error=str(exc))
        return 3
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, handle_signal)
    conn = open_database(args.db)
    start_monotonic = time.monotonic()
    deadline = start_monotonic + max(0.0, args.duration_seconds)
    state = {
        "version": VERSION,
        "pid": os.getpid(),
        "status": "running",
        "started_at": utc_now(),
        "last_heartbeat_at": utc_now(),
        "last_run": None,
        "database": str(args.db),
        "log": str(args.log),
        "bbox": list(args.bbox),
        "sources": sources,
        "osm_pbf": str(args.osm_pbf),
    }
    write_state(args.state, state)
    logger.log("INFO", "crawler_started", version=VERSION, duration_seconds=args.duration_seconds, cycle_interval_seconds=args.cycle_interval_seconds, db=str(args.db), bbox=args.bbox, sources=sources)
    runs: list[dict[str, Any]] = []
    try:
        while not STOP_EVENT.is_set():
            if not args.once and time.monotonic() >= deadline:
                break
            summary = run_cycle(
                conn,
                logger,
                args.bbox,
                sources,
                args.max_records_per_source,
                args.timeout,
                args.cache_dir,
                args.osm_pbf,
                args.osm_max_records,
                args.osm_pbf_timeout_seconds,
            )
            runs.append(summary)
            state.update({"last_heartbeat_at": utc_now(), "last_run": summary, "totals": db_summary(conn)})
            write_state(args.state, state)
            if args.once or STOP_EVENT.is_set():
                break
            wait_until = min(deadline, time.monotonic() + max(0.0, args.cycle_interval_seconds))
            while not STOP_EVENT.is_set() and time.monotonic() < wait_until:
                remaining = wait_until - time.monotonic()
                beat = min(max(1.0, args.heartbeat_seconds), remaining)
                STOP_EVENT.wait(beat)
                state.update({"last_heartbeat_at": utc_now(), "status": "running", "totals": db_summary(conn)})
                write_state(args.state, state)
                logger.log("INFO", "heartbeat", last_run=summary["run_id"], totals=state["totals"])
    except KeyboardInterrupt:
        STOP_EVENT.set()
    finally:
        state.update({"status": "stopped" if STOP_EVENT.is_set() else "finished", "finished_at": utc_now(), "totals": db_summary(conn)})
        write_state(args.state, state)
        logger.log("INFO", "crawler_finished", status=state["status"], cycles=len(runs), totals=state["totals"])
        conn.close()
        lock.release()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
