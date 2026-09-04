from __future__ import annotations

import getpass
import os

from django.core.management.base import BaseCommand, CommandError

from hawatch.common.proxy import validate_proxy_uri
from hawatch.modules.forecasts.models import WeatherProxy


class Command(BaseCommand):
    help = (
        "Idempotently add the initial weather SOCKS proxies. Secrets are read "
        "from environment variables or hidden interactive input, never from Git."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--interactive",
            action="store_true",
            help="Prompt for the Canada and US proxy URIs without echoing them.",
        )
        parser.add_argument(
            "--deactivate-missing",
            action="store_true",
            help="Deactivate only the two bootstrap rows whose env/input URI is missing.",
        )

    def handle(self, *args, **options):
        rows = [
            ("CA", "پروکسی کانادا", 10, "WEATHER_PROXY_CA_URL"),
            ("US", "پروکسی آمریکا", 20, "WEATHER_PROXY_US_URL"),
        ]
        changed = 0
        seen_countries: set[str] = set()
        for country, name, sort_order, env_name in rows:
            uri = os.environ.get(env_name, "").strip()
            if options["interactive"]:
                entered = getpass.getpass(f"{country} SOCKS5 URI (blank to skip): ").strip()
                if entered:
                    uri = entered
            if not uri:
                if options["deactivate_missing"]:
                    disabled = WeatherProxy.objects.filter(country_code=country, name=name, is_active=True).update(
                        is_active=False
                    )
                    if disabled:
                        self.stdout.write(f"Deactivated missing {country} bootstrap proxy.")
                continue
            try:
                uri = validate_proxy_uri(uri)
            except ValueError as exc:
                raise CommandError(f"{env_name} is invalid: {exc}") from exc
            proxy, created = WeatherProxy.objects.get_or_create(
                country_code=country,
                name=name,
                defaults={"proxy_url": uri, "sort_order": sort_order, "is_active": True},
            )
            if not created:
                proxy.proxy_url = uri
                proxy.sort_order = sort_order
                proxy.is_active = True
                proxy.save(update_fields=["proxy_url", "sort_order", "is_active", "updated_at"])
            changed += 1
            seen_countries.add(country)
            self.stdout.write(f"{('Created' if created else 'Updated')} {country} weather proxy (id={proxy.pk}).")

        if not changed and not seen_countries:
            self.stdout.write("No proxy URI supplied; database was unchanged.")
