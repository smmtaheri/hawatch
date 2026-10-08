"""Apply only offline derived totals; no GPX, provider access or catalog import."""
import json
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from hawatch.modules.routes.models import Route
from hawatch.api.v1.week_cache import invalidate_week_cache

class Command(BaseCommand):
    help = 'Apply reference GPX descent when the canonical route chain matches.'
    def handle(self, *args, **options):
        document=json.loads((settings.FIXTURES_DIR/'route_descent_v1.json').read_text())
        if document['schema_version']!='route-descent-1': raise CommandError('Unknown descent schema')
        updated, skipped=0,0
        with transaction.atomic():
            for item in document['routes']:
                route=Route.objects.filter(slug=item['slug']).first()
                if route is None or list(route.points.order_by('sort_order').values_list('weather_point__slug',flat=True))!=item['chain']:
                    skipped+=1
                    continue
                if item['descent_m']<0: raise CommandError('Negative descent')
                route.descent_m=item['descent_m']
                route.descent_evidence=item['evidence']
                route.save(update_fields=['descent_m','descent_evidence'])
                updated+=1
            transaction.on_commit(invalidate_week_cache)
        self.stdout.write(f'Descent updated: {updated}; unmatched routes: {skipped}; unresolved evidence: {len(document["unresolved"])}')
