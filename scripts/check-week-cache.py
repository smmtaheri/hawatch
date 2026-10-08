#!/usr/bin/env python3
"""Local read-only cache/header check. CDN HIT requires the CDN's own evidence."""
import argparse
import json
import time
from urllib.request import Request, urlopen
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--base-url',required=True)
parser.add_argument('--point',default='tochal')
parser.add_argument('--route',default='tochal-darband')
args=parser.parse_args()
base=args.base_url.rstrip('/')

def check(path):
    outputs=[]
    for attempt in range(2):
        start=time.perf_counter()
        with urlopen(Request(base+path,headers={'Accept-Encoding':'identity'}),timeout=60) as response:
            body=response.read(); headers=dict(response.headers)
            info={'request':attempt+1,'status':response.status,'milliseconds':round((time.perf_counter()-start)*1000,1),'bytes':len(body),'headers':{k:v for k,v in headers.items() if k.lower() in ('cache-control','etag','age','vary','x-hawatch-cache','cf-cache-status','x-cache','x-cache-status','cdn-cache-control','server','content-encoding')}}
            outputs.append(info)
            if 'forecast/week' in path:
                payload=json.loads(body)
                if len(payload.get('days',[]))!=8: raise SystemExit('Expected eight forecast dates')
            if 'public' not in response.headers.get('Cache-Control',''): raise SystemExit('Response is not publicly cacheable: '+path)
    print(json.dumps({'path':path,'requests':outputs},ensure_ascii=False,indent=2))
for path in (f'/api/v1/points/{args.point}/forecast/week/',f'/api/v1/routes/{args.route}/forecast/week/'):
    check(path)
# Read the actual version from the server HTML, never assume the build's tag.
import re
with urlopen(base+'/points/'+args.point,timeout=60) as response: html=response.read().decode()
css=re.search(r'href="(/static-assets/[^\"]+/assets/hawatch\.css)"',html)
if not css: raise SystemExit('Versioned CSS was not found in the page')
check(css.group(1))
print('X-Hawatch-Cache is the origin application cache. A real CDN HIT must be verified independently using Age/CDN headers or its dashboard.')
