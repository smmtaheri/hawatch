"""Apply only offline derived totals; no GPX, provider access or catalog import."""
import json
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from hawatch.modules.routes.models import Route
from hawatch.api.v1.week_cache import invalidate_week_cache

class Command(BaseCommand):
    help = 'Apply GPX descent and missing segment distances for matching canonical chains.'
    def handle(self, *args, **options):
        document=json.loads((settings.FIXTURES_DIR/'route_descent_v1.json').read_text())
        if document['schema_version']!='route-descent-1': raise CommandError('Unknown descent schema')
        updated, skipped=0,0
        with transaction.atomic():
            for item in document['routes']:
                route=Route.objects.filter(slug=item['slug']).first()
                points=list(route.points.select_related('weather_point').order_by('sort_order','pk')) if route else []
                if route is None or [p.weather_point.slug if p.weather_point else None for p in points]!=item['chain']:
                    skipped+=1
                    continue
                if item['descent_m']<0: raise CommandError('Negative descent')
                cumulative=item.get('cumulative_distance_m')
                if cumulative is not None:
                    if len(cumulative)!=len(points) or cumulative[0]!=0 or any(not isinstance(v,int) or isinstance(v,bool) for v in cumulative) or any(b<=a for a,b in zip(cumulative,cumulative[1:])):
                        raise CommandError('Invalid GPX cumulative distances')
                    # Complete a missing profile from one consistent source; retain fully curated profiles.
                    if any(p.segment_distance_m is None for p in points[1:]):
                        for index,point in enumerate(points):
                            point.segment_distance_m=0 if index==0 else cumulative[index]-cumulative[index-1]
                        type(points[0]).objects.bulk_update(points,['segment_distance_m'])
                route.descent_m=item['descent_m']
                route.descent_evidence=item['evidence']
                route.save(update_fields=['descent_m','descent_evidence'])
                updated+=1
            transaction.on_commit(invalidate_week_cache)
        self.stdout.write(f'Descent updated: {updated}; unmatched routes: {skipped}; unresolved evidence: {len(document["unresolved"])}')
