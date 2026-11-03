#!/usr/bin/env python3
"""Maintain the editorial destination queue; never writes to the application/DB.

JSON is the editable ledger. Markdown views and all counts are derived from it.
Selection and rendering are offline. The optional SSH exporter uses a read-only
DB session; publication needs an explicit mapping and a saved catalog snapshot.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime
import json
from pathlib import Path
import shlex
import subprocess
import sys
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LEDGER = ROOT / "docs/catalog-queue.json"
SITES = {"havakouh": "هواکوه", "havagasht": "هواگشت"}
STATUSES = {
    "queued": "صف افزودن",
    "in_progress": "درحال‌کار",
    "needs_review": "نیازمند تعیین هویت/تطبیق",
    "catalog_only": "fixture موجود؛ انتشار تأیید نشده",
    "existing_point": "نقطهٔ موجود؛ بررسی ارتقای مقصد",
    "published": "صفحهٔ مستقل موجود",
    "covered": "پوشش مرتبط/نام دیگر؛ افزودن تکراری لازم نیست",
}
OPEN_STATUSES = {"queued", "in_progress", "needs_review", "catalog_only", "existing_point"}
VERIFIED_STATUSES = {"published", "covered", "existing_point"}


def export_live_snapshot(host: str) -> dict:
    """Export public catalog fields in a read-only database session over SSH."""
    query = (
        'import json; from django.db import connection; '
        'connection.cursor().execute("SET default_transaction_read_only = on"); '
        'from django.utils import timezone; '
        'from hawatch.modules.forecasts.models import WeatherPoint; '
        'from hawatch.modules.routes.models import Route; '
        'fields=["slug","name","page_name","short_label","place_type","category_key",'
        '"region","kind","importance","is_active","seo_indexable","aliases",'
        '"source_urls","identity_summary"]; '
        'points=[dict({k:getattr(p,k) for k in fields},latitude=p.location.y,longitude=p.location.x) '
        'for p in WeatherPoint.objects.all().order_by("slug")]; '
        'routes=list(Route.objects.values("slug","title","is_active","target_weather_point__slug")); '
        'print(json.dumps({"checked_at":timezone.now().isoformat(),"points":points,"routes":routes},ensure_ascii=False))'
    )
    remote = (
        "cd /root/hawatch && docker compose --env-file .env -f infra/compose/compose.yaml "
        "exec -T api python manage.py shell --verbosity 0 -c " + shlex.quote(query)
    )
    result = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", "--", host, remote],
        check=True, capture_output=True, text=True, timeout=60,
    )
    return json.loads(result.stdout)


def order(entry: dict) -> tuple:
    return (entry["priority"], entry["rank"], entry["id"])


def members(entry: dict, site: str | None = None) -> bool:
    return site is None or any(ref["site"] == site for ref in entry["sources"])


def next_entries(data: dict, limit: int, site: str | None = None) -> list[dict]:
    return sorted(
        (e for e in data["entries"] if e["status"] == "queued" and members(e, site)),
        key=order,
    )[:limit]


def counts(data: dict, site: str | None = None) -> Counter:
    return Counter(e["status"] for e in data["entries"] if members(e, site))


def validate(data: dict) -> list[str]:
    errors: list[str] = []
    if data.get("schema_version") != 1:
        errors.append("Unsupported schema_version")
    ids: set[str] = set()
    refs: dict[str, set[str]] = {site: set() for site in SITES}
    seen_slugs: dict[tuple[str, str], str] = {}
    for entry in data.get("entries", []):
        key = entry.get("id", "")
        if not key or key in ids:
            errors.append(f"Duplicate/missing entry id: {key}")
        ids.add(key)
        if not entry.get("name") or not entry.get("note"):
            errors.append(f"{key}: name and editorial note are required")
        status = entry.get("status")
        if status not in STATUSES:
            errors.append(f"{key}: unknown status {status}")
        if entry.get("priority") not in ("P1", "P2", "P3"):
            errors.append(f"{key}: invalid priority")
        if not isinstance(entry.get("rank"), int) or entry["rank"] < 1:
            errors.append(f"{key}: rank must be a positive integer")
        if not entry.get("sources"):
            errors.append(f"{key}: source references are required")
        for ref in entry.get("sources", []):
            site, source_key = ref.get("site"), ref.get("key")
            if site not in SITES or not isinstance(source_key, str) or not source_key:
                errors.append(f"{key}: invalid source reference")
                continue
            if source_key in refs[site]:
                errors.append(f"{key}: source item appears in two entries: {site}:{source_key}")
            refs[site].add(source_key)
            host = (urlsplit(ref.get("url", "")).hostname or "").removeprefix("www.")
            if host != site + ".com":
                errors.append(f"{key}: source URL must belong to {site}")
        slugs = entry.get("hawatch_slugs", [])
        if status in VERIFIED_STATUSES:
            if not slugs or not entry.get("verified_at") or not entry.get("match_basis"):
                errors.append(f"{key}: a verified state needs slugs, timestamp and match evidence")
            try:
                parsed = datetime.fromisoformat(entry.get("verified_at", "").replace("Z", "+00:00"))
                if parsed.tzinfo is None:
                    raise ValueError("Timezone is required")
            except ValueError:
                errors.append(f"{key}: invalid verified_at")
        elif slugs:
            errors.append(f"{key}: unresolved mappings belong in candidate_slugs")
        if status == "covered" and not entry.get("coverage_note"):
            errors.append(f"{key}: covered needs a precise coverage limit")
        if status == "published":
            for site in {ref["site"] for ref in entry["sources"]}:
                for slug in slugs:
                    pair = (site, slug)
                    if pair in seen_slugs:
                        errors.append(f"{key}: same published entity also in {seen_slugs[pair]}; merge its source references")
                    seen_slugs[pair] = key
    for site, snapshot in data.get("sources", {}).items():
        if site not in SITES:
            errors.append(f"Unknown source {site}")
            continue
        expected = snapshot.get("inventory_keys", [])
        excluded = snapshot.get("excluded", [])
        excluded_keys = {e["key"] for e in excluded}
        if len(expected) != len(set(expected)) or len(excluded_keys) != len(excluded):
            errors.append(f"{site}: duplicate inventory/excluded key")
        if refs[site] & excluded_keys:
            errors.append(f"{site}: excluded item also appears in the domestic queue")
        if refs[site] | excluded_keys != set(expected):
            lost = set(expected) - refs[site] - excluded_keys
            extra = refs[site] - set(expected)
            errors.append(f"{site}: inventory coverage mismatch; lost={sorted(lost)}, extra={sorted(extra)}")
    if set(data.get("sources", {})) != set(SITES):
        errors.append("Both source inventories are required")
    return errors


def complete(data: dict, entry_id: str, slug: str, snapshot: dict) -> None:
    """An explicit curator choice; refuse inactive/missing production records."""
    entry = next((e for e in data["entries"] if e["id"] == entry_id), None)
    if entry is None:
        raise ValueError(f"Unknown queue ID: {entry_id}")
    timestamp = snapshot.get("checked_at", "")
    parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Snapshot checked_at must include its timezone")
    baseline = max(
        datetime.fromisoformat(t.replace("Z", "+00:00"))
        for t in [data["production_snapshot"]["checked_at"], entry.get("verified_at", timestamp)]
    )
    if parsed < baseline:
        raise ValueError("Snapshot is older than the ledger's existing evidence")
    point = next((p for p in snapshot.get("points", []) if p.get("slug") == slug), None)
    if not point or not point.get("is_active"):
        raise ValueError(f"{slug}: not an active point in the read-only production snapshot")
    if not isinstance(point.get("seo_indexable"), bool):
        raise ValueError("Snapshot must include an explicit seo_indexable boolean")
    entry.setdefault("history", []).append({
        "at": timestamp,
        "previous_status": entry["status"],
        "previous_note": entry["note"],
        **({"local_track_dir": entry["local_track_dir"]} if entry.get("local_track_dir") else {}),
    })
    entry["status"] = "published" if point.get("seo_indexable") else "existing_point"
    entry["hawatch_slugs"] = [slug]
    entry["verified_at"] = timestamp
    entry["match_basis"] = "تطبیق صریح مسئول افزودن با رکورد فعال snapshot فقط‌خواندنی production"
    entry["route_slugs"] = sorted(
        r["slug"] for r in snapshot.get("routes", [])
        if r.get("is_active") and r.get("target_weather_point__slug") == slug
    )
    entry.pop("candidate_slugs", None)
    entry.pop("coverage_note", None)
    entry.pop("local_track_dir", None)
    entry["note"] = "ثبت نقطه در کاتالوگ زنده تأیید شد؛ وضعیت مسیرها مستقل از صف افزودن مقصد پیگیری می‌شود."


def esc(value: str) -> str:
    return str(value).replace("|", " / ").replace("\n", " ")


def source_label(entry: dict) -> str:
    return "، ".join(SITES[site] for site in SITES if members(entry, site))


def point_links(slugs: list[str]) -> str:
    return " · ".join(f"[{slug}](https://hawatch.ir/points/{slug})" for slug in slugs) or "—"


def summary(data: dict) -> list[str]:
    lines = ["| منبع | ردیف یکتای صف | صف افزودن | درحال‌کار | نیازمند بررسی | فقط fixture | نقطهٔ نیازمند ارتقا | صفحهٔ مستقل موجود | پوشش مرتبط |", "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for site, title in [*SITES.items(), (None, "کل؛ هر مقصد یک‌بار")]:
        c = counts(data, site)
        lines.append("| " + title + " | " + " | ".join(str(n) for n in [sum(c.values()), *[c[s] for s in STATUSES]]) + " |")
    return lines


def table(entries: list[dict], archive: bool = False) -> list[str]:
    if not entries:
        return ["موردی ثبت نشده است."]
    heading = "| ردیف | شناسه | مقصد | منطقهٔ منبع | اولویت | " + ("صفحهٔ هواچ | " if archive else "") + "وضعیت/اقدام بعدی |"
    lines = [heading, "| ---: | --- | --- | --- | --- | " + ("--- | " if archive else "") + "--- |"]
    for i, e in enumerate(entries, 1):
        note = e["note"].rstrip(".؛ ")
        labels = list(dict.fromkeys(ref["label"] for ref in e["sources"]))
        if len(labels) > 1:
            note += "؛ نام‌های منبع: " + "، ".join(labels)
        if e.get("local_track_dir"):
            note += f"؛ ترک محلی: `{e['local_track_dir']}`"
        if e.get("candidate_slugs"):
            note += "؛ همتاهای نیازمند تطبیق: " + point_links(e["candidate_slugs"])
        if e.get("route_slugs") and archive:
            note += "؛ مسیر: " + " · ".join(f"[{s}](https://hawatch.ir/routes/{s})" for s in e["route_slugs"])
        elif archive and e["status"] == "published":
            note += "؛ مسیرِ منتهی به این نقطه در snapshot ثبت نشده است."
        if e.get("coverage_note"):
            note += "؛ " + e["coverage_note"]
        title = esc(e["name"])
        ref = e["sources"][0]
        if ref["site"] == "havagasht":
            title = f"[{title}]({ref['url']})"
        fields = [str(i), f"`{e['id']}`", title, esc(e["region"] or "در فهرست منبع مشخص نشده"), e["priority"]]
        if archive:
            fields.append(point_links(e.get("hawatch_slugs", [])))
        fields.append(esc(note))
        lines.append("| " + " | ".join(fields) + " |")
    return lines


def views(data: dict) -> dict[str, str]:
    date = data["production_snapshot"]["checked_at"]
    total = counts(data)
    open_count = sum(total[s] for s in OPEN_STATUSES)
    main = [
        "# صف افزودن مقصدهای هواکوه و هواگشت", "",
        f"مبنای تطبیق با کاتالوگ زندهٔ هواچ: `{date}`. این وضعیتِ همان snapshot است؛ دستورهای نمایش صف هیچ درخواست شبکه‌ای نمی‌فرستند.", "",
        "منبع حقیقت این صف [`catalog-queue.json`](catalog-queue.json) است؛ این فایل و دو نمای منبع با `python3 scripts/catalog_queue.py --render` تولید می‌شوند. تاریخچهٔ قدیمی در `docs/archive/` حفظ شده و صف جاری محسوب نمی‌شود.", "",
        "هواکوه: فهرست زندهٔ ۳۱ استان به‌علاوهٔ پیست‌های داخل ایران بررسی شده است. ورودی‌های خارجی جداگانه در ledger نگهداری می‌شوند. نسخهٔ انگلیسی، ارتفاع‌های متعدد، املای دیگر و URL تکراری مقصد تازه نیستند. هواگشت: همهٔ شناسه‌های فهرست زنده با sitemap کنترل شده‌اند؛ ردیف‌های تکراریِ یک مقصد یک‌جا نگهداری می‌شوند.", "",
        "## شمارش جاری", "", *summary(data), "",
        f"کار باز صف: **{open_count} ردیف**؛ شامل {total['queued']} نامزد افزودن، {total['in_progress']} درحال‌کار، {total['needs_review']} نیازمند تعیین هویت، {total['catalog_only']} فقط fixture و {total['existing_point']} نقطهٔ نیازمند بررسی ارتقا. این دسته‌ها هم‌پوشانی ندارند.", "",
        "«صف افزودن» نامزدهایی است که در تطبیق نام/alias، نوع عارضه و منابع این بررسی همتای تأییدشده ندارند؛ کنترل مختصات و تکراری‌نبودن پیش از onboarding هر مورد همچنان الزامی است. «نیازمند بررسی» را به‌عنوان مقصد قطعاً غایب نشمارید. مجموع پنج ستون اول وضعیت‌ها، کار باز صف است؛ دو ستون آخر از صف افزودن خارج‌اند.", "",
        "«صفحهٔ مستقل موجود» یعنی رکورد فعال و indexable در کاتالوگ زنده؛ به معنی ایندکس‌شدن در گوگل یا تأیید تازگی forecast نیست. «پوشش مرتبط» برای نام دیگر یا پهنه‌ای است که با مقصد مشخص موجود پوشش داده شده؛ محدودهٔ پوشش در یادداشت هر ردیف آمده است. waypoint/noindex موجود هم با مقصد مستقل یکسان شمرده نمی‌شود.", "",
        "## اولویت و روش برداشتن مقصد", "",
        "P1: انتخاب تحریریه‌ایِ نام‌های شناخته‌شده، تنوع جغرافیایی، ارزش صفحهٔ هواشناسی و فرصت فصلی فعلی؛ این اولویت آمار حجم جست‌وجو نیست. P2: نامزدهای عادیِ با هویت اولیهٔ روشن. P3: موارد مبهم یا کم‌اطلاع. داخل هر اولویت، `rank` ترتیب صریح و ثابت است؛ گذشت زمان اولویت‌ها را خودکار عوض نمی‌کند.", "",
        "برای کار تازه، فقط از وضعیت `queued` و به‌ترتیب priority/rank بردارید. پیش از شروع، آن را `in_progress` کنید تا دوباره پیشنهاد نشود. مقصدهایی که همین حالا درحال‌کارند جداگانه ادامه پیدا می‌کنند.", "",
        "```bash", "python3 scripts/catalog_queue.py --next 10", "python3 scripts/catalog_queue.py --next 10 --source havakouh", "python3 scripts/catalog_queue.py --next 10 --source havagasht", "```", "",
        "## نوبت جاری", "", *table(sorted((e for e in data["entries"] if e["status"] == "in_progress"), key=order)), "",
        "## ده مقصد بعدی صف مشترک", "", *table(next_entries(data, 10)), "",
        "## نمای کامل هر منبع", "",
        "- [صف کامل هواکوه](havakouh-backlog.md)", "- [صف کامل هواگشت](havagasht-backlog.md)", "",
        "## بستن کار پس از انتشار", "",
        "snapshot تازه را با فرمان زیر بگیرید؛ اتصال دیتابیس read-only است و خروجی فقط فیلدهای عمومی نقطه/مسیر را دارد:", "",
        "```bash", "python3 scripts/catalog_queue.py --snapshot-live hawatch > /tmp/hawatch-live-catalog.json", "```", "",
        "هر مقصد یک شناسهٔ پایدار دارد. بعد از انتشار موفق و کنترل عمومی، همان ردیف با slug canonical و شاهد کاتالوگ زنده به `published` منتقل می‌شود؛ رکورد و منبع آن برای جلوگیری از پیشنهاد دوباره در آرشیو می‌ماند. داشتن فایل fixture، دانلود GPX یا موفقیت validator به‌تنهایی پایان کار نیست. کامل‌نشدن Route، مقصدی را که طبق مجوز قبلی منتشر شده دوباره وارد صف ساخت مقصد نمی‌کند؛ پیگیری Route مستقل است.", "",
        "snapshot فقط‌خواندنی باید `checked_at` دارای timezone و آرایهٔ `points` شامل slug/is_active/seo_indexable و، در صورت بررسی مسیر، آرایهٔ `routes` داشته باشد. هیچ کوکی، token، اطلاعات حساب یا env در آن قرار نگیرد و خود snapshot فقط در مسیر موقت محلی بماند. فرمان زیر فقط ledger و نماهای مستندات را تغییر می‌دهد:", "",
        "```bash", "python3 scripts/catalog_queue.py --complete HK-113 --slug actual-canonical-slug \\", "  --live-snapshot /tmp/hawatch-live-catalog.json", "python3 scripts/catalog_queue.py --check", "```", "",
        "برای پوشش مرتبط، ادغام نام دیگر یا رفع ابهام، ledger را با توضیح محدودیت پوشش و شواهد ویرایش و سپس `--render`/`--check` اجرا کنید. هر مرجع منبع باید دقیقاً در یک ردیف یا در فهرست خارج از دامنه باشد؛ validator جلوی گم‌شدن یا دو بار شمردن آن را می‌گیرد. برای به‌روزرسانی بعدی منابع، اختلاف شناسه‌های فهرست زنده با `inventory_keys` را بررسی کنید؛ حذف‌شدن از منبع به معنی حذف‌کردن دادهٔ هواچ نیست.", "",
        "صف درخواست ایندکس همچنان در [indexing-backlog.md](indexing-backlog.md) مستقل نگهداری می‌شود. اعلام ایندکس‌شدن کاربر فقط آن صف را تغییر می‌دهد.", "",
    ]
    rendered = {"docs/catalog-queue.md": "\n".join(main)}
    for site, title in SITES.items():
        snap = data["sources"][site]
        group = [e for e in data["entries"] if members(e, site)]
        body = [f"# صف مقصدهای {title} در هواچ", "", f"نمای تولیدشده از [صف یکپارچه](catalog-queue.md)؛ مبنای کاتالوگ زنده `{date}`. برای ویرایش، [ledger](catalog-queue.json) را تغییر دهید و `python3 scripts/catalog_queue.py --render` اجرا کنید.", "",
                f"فهرست زندهٔ منبع: [{title}]({snap['url']})؛ {len(snap['inventory_keys'])} شناسهٔ منبع، {len(snap.get('excluded', []))} ورودی خارج از دامنهٔ ایران و {len(group)} ردیف یکتای داخلی پس از ادغام تکراری‌ها. تعداد URLهای sitemap با تعداد مقصدها یکی نیست. اختلاف استان یا املای منبع در یادداشت ردیف حفظ شده است.", "",
                f"[تاریخچه و شواهد پیش از مرتب‌سازی](archive/{site}-backlog-before-queue-2026-11-03.md)", ""]
        c = counts(data, site)
        body.extend(["| وضعیت | تعداد |", "| --- | ---: |", *[f"| {label} | {c[state]} |" for state,label in STATUSES.items()], ""])
        for status, label in STATUSES.items():
            entries = sorted((e for e in group if e["status"] == status), key=order)
            body.extend([f"## {label} ({len(entries)})", "", *table(entries, archive=status in VERIFIED_STATUSES), ""])
        if snap.get("excluded"):
            body.extend(["## خارج از دامنهٔ فعلی ایران", "", "این موارد حذف نشده‌اند؛ از تعداد مقصدهای داخلی و پیشنهاد نوبت بعد کنار گذاشته شده‌اند.", "", "| شناسهٔ منبع | نام | دلیل |", "| --- | --- | --- |"])
            body.extend(f"| {e['key']} | {esc(e['name'])} | {esc(e['reason'])} |" for e in snap["excluded"])
            body.append("")
        rendered[f"docs/{site}-backlog.md"] = "\n".join(body)
    return rendered


def write_views(data: dict, root: Path = ROOT, check: bool = False) -> list[str]:
    stale = []
    for relative, content in views(data).items():
        path = root / relative
        if check:
            if not path.exists() or path.read_text(encoding="utf-8") != content:
                stale.append(relative)
        else:
            path.write_text(content, encoding="utf-8")
    return stale


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--render", action="store_true")
    mode.add_argument("--next", type=int, metavar="N")
    mode.add_argument("--complete", metavar="QUEUE_ID")
    mode.add_argument("--snapshot-live", metavar="SSH_HOST", help="Export public catalog data through a read-only DB session; stdout JSON only")
    parser.add_argument("--source", choices=SITES)
    parser.add_argument("--slug")
    parser.add_argument("--live-snapshot", type=Path)
    args = parser.parse_args()
    if args.snapshot_live:
        try:
            snapshot = export_live_snapshot(args.snapshot_live)
        except (subprocess.SubprocessError, ValueError) as exc:
            print(f"Read-only snapshot export failed: {exc}", file=sys.stderr)
            return 1
        print(json.dumps(snapshot, ensure_ascii=False, indent=2))
        return 0
    data = json.loads(args.ledger.read_text(encoding="utf-8"))
    if args.complete:
        if not args.slug or not args.live_snapshot:
            parser.error("--complete requires --slug and --live-snapshot")
        try:
            complete(data, args.complete, args.slug, json.loads(args.live_snapshot.read_text(encoding="utf-8")))
        except ValueError as exc:
            parser.error(str(exc))
    errors = validate(data)
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    if args.next is not None:
        if args.next < 1:
            parser.error("N must be positive")
        for i, e in enumerate(next_entries(data, args.next, args.source), 1):
            print(f"{i}. {e['id']} | {e['name']} | {source_label(e)} | {e['region']} | {e['priority']} | {e['note']}")
        return 0
    if args.complete:
        args.ledger.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    stale = write_views(data, check=args.check)
    if stale:
        print("Generated queue views need --render: " + ", ".join(stale), file=sys.stderr)
        return 1
    print(f"{'Checked' if args.check else 'Rendered'} {len(data['entries'])} unique domestic queue entries.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
