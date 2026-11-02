import time

from django.conf import settings
from django.core.management.base import BaseCommand

from hawatch.jobs.sitemap_scheduler import SitemapScheduler


class Command(BaseCommand):
    help = "Publish sitemap periodically and promptly after Redis refresh hints."

    def handle(self, *args, **options):
        scheduler = SitemapScheduler(interval=settings.SITEMAP_REFRESH_SECONDS)
        try:
            while True:
                scheduler.tick()
                time.sleep(15)
        except KeyboardInterrupt:
            pass
