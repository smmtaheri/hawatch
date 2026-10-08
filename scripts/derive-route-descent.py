#!/usr/bin/env python3
"""Offline only: derive descent from verified local GPX; never upload the tracks.

Use the existing 50m resampling/5-sample smoothing algorithm. Require a
canonical route, full continuous origin→target coverage and ordered landmarks.
Ambiguous, partial, composite or technical tracks remain unknown.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyze_route_tracks import parse_gpx_track, haversine_m, cut_at_first_summit_approach, robust_smoothed_ascent_m

# Research manifests predate canonical names. This is offline evidence mapping,
# never a runtime slug alias or redirect.
RESEARCH_NAMES = {'touchal-darband':'tochal-darband','touchal-welanjak':'tochal-velenjak','touchal-ahar':'tochal-ahar','touchal-kalkchal':'tochal-kolakchal','touchal-shahrestanak':'tochal-shahrestanak'}

def derive(root, catalog_root=None):
    points, routes = {}, {}
    for file in sorted((catalog_root or root/'apps/api/fixtures/catalog').glob('*.json')):
        document = json.loads(file.read_text())
        points.update(document.get('weather_points', {}))
        routes.update({r['slug']:r for r in document.get('routes',{}).values()})
    candidates = {}
    diagnostics = []
    for manifest in sorted((root/'tracks').glob('**/*manifest.json')):
        document = json.loads(manifest.read_text())
        for track in document.get('tracks', []):
            slug = RESEARCH_NAMES.get(track.get('route_slug'),track.get('route_slug'))
            if slug not in routes: continue
            reason = None
            coverage = str(track.get('coverage','')).lower()
            role = str(track.get('role','')).lower()
            if any(t in coverage for t in ('partial','crosscheck','composite','technical','glacier','multiple_approaches')) or role in ('crosscheck','rejected','reference_only'):
                reason = 'partial, composite, technical or reference-only evidence'
            path = manifest.parent / track.get('filename','')
            route = routes[slug]
            ids = route.get('points',[])
            if reason is None:
                try:
                    if len(ids)<3 or any(i not in points for i in ids): raise ValueError('canonical chain incomplete')
                    coords = [(points[i]['latitude'],points[i]['longitude']) for i in ids]
                    raw = parse_gpx_track(path)
                    cut, meta = cut_at_first_summit_approach(raw,coords[-1])
                    if meta['min_summit_distance_m']>100: raise ValueError('target farther than 100m from track')
                    start = min(range(len(cut)),key=lambda i:haversine_m((cut[i]['lat'],cut[i]['lon']),coords[0]))
                    if haversine_m((cut[start]['lat'],cut[start]['lon']),coords[0])>100: raise ValueError('origin farther than 100m from track')
                    cut = cut[start:]
                    if len(cut)<10 or any(p['ele'] is None for p in cut): raise ValueError('elevation geometry incomplete')
                    if any(haversine_m((a['lat'],a['lon']),(b['lat'],b['lon']))>300 for a,b in zip(cut,cut[1:])): raise ValueError('discontinuous geometry')
                    last = 0
                    for coordinate in coords[1:-1]:
                        nearest = min(range(last,len(cut)),key=lambda i:haversine_m((cut[i]['lat'],cut[i]['lon']),coordinate))
                        if haversine_m((cut[nearest]['lat'],cut[nearest]['lon']),coordinate)>500: raise ValueError('ordered landmark farther than 500m')
                        last = nearest
                    measures = robust_smoothed_ascent_m(cut)
                    descent = round(measures['robust_smoothed_ascent_m']-measures['net_elevation_change_m'])
                    if descent<0: raise ValueError('invalid elevation result')
                    item = {'slug':slug,'descent_m':descent,'chain':ids,'evidence':{'method':'gpx-50m-5sample-v1','source_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'source_url':track.get('wikiloc_url'),'coverage':'canonical-origin-to-first-target','reference_only_elevation':True}}
                    priority = 0 if role=='primary' or track.get('catalog_applied') else 1
                    candidates.setdefault(slug,[]).append((priority,item))
                except (ValueError,TypeError,KeyError,OSError) as error: reason=str(error)
            if reason: diagnostics.append({'slug':slug,'reason':reason})
    result = []
    for slug, items in sorted(candidates.items()):
        preferred = [i for p,i in items if p==min(p for p,_ in items)]
        if len(preferred)>1 and max(i['descent_m'] for i in preferred)-min(i['descent_m'] for i in preferred)>max(50,min(i['descent_m'] for i in preferred)*.3):
            diagnostics.append({'slug':slug,'reason':'conflicting independent elevation profiles'})
        else: result.append(preferred[0])
    known={i['slug'] for i in result}
    return {'schema_version':'route-descent-1','routes':result,'unresolved':sorted(set(routes)-known),'diagnostics':diagnostics}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root',type=Path,required=True)
    parser.add_argument('--catalog-root',type=Path,help='Canonical reviewed catalog directory; keep unrelated local drafts out')
    args=parser.parse_args()
    print(json.dumps(derive(args.source_root,args.catalog_root),ensure_ascii=False,indent=2))
