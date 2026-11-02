"""A cheap compatibility endpoint for the same artifact Nginx serves."""
import hashlib
import os

from django.http import HttpResponse
from django.utils.cache import get_conditional_response
from django.utils.http import http_date
from django.views.decorators.http import require_safe

from hawatch.modules.catalog.sitemap import CACHE_CONTROL, MAX_BYTES, sitemap_root


@require_safe
def sitemap_response(request):
    try:
        with (sitemap_root() / "sitemap.xml").open("rb") as handle:
            stat = os.fstat(handle.fileno())
            if stat.st_size > MAX_BYTES:
                raise OSError("Sitemap exceeds maximum size")
            content = handle.read()
        if not content:
            raise OSError("Empty sitemap")
    except OSError:
        response = HttpResponse("Sitemap temporarily unavailable.\n", status=503, content_type="text/plain; charset=utf-8")
        response["Cache-Control"] = "no-store"
        response["Retry-After"] = "60"
        return response
    etag = '"' + hashlib.sha256(content).hexdigest() + '"'
    response = HttpResponse(content if request.method == "GET" else b"", content_type="application/xml; charset=utf-8")
    response["ETag"] = etag
    response["Last-Modified"] = http_date(stat.st_mtime)
    response["Content-Length"] = str(len(content))
    response["Cache-Control"] = CACHE_CONTROL
    return get_conditional_response(request, etag=etag, last_modified=int(stat.st_mtime), response=response)
