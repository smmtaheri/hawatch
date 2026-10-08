from datetime import date, timedelta
import secrets
from django.http import HttpResponseRedirect
from django.db import IntegrityError, transaction
from rest_framework.decorators import api_view, authentication_classes, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny
from rest_framework.throttling import AnonRateThrottle
from rest_framework.exceptions import ValidationError, NotFound
from rest_framework.response import Response
from hawatch.common.time import now_tehran
from hawatch.modules.routes.models import SharedRoutePlan
from .serializers import get_route

class ShareThrottle(AnonRateThrottle):
    rate = "60/hour"

@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
@throttle_classes([ShareThrottle])
def create_share(request):
    route = get_route(str(request.data.get("route", "")))
    try:
        selected = date.fromisoformat(request.data["date"])
        raw_hour = request.data["start_hour"]
        if isinstance(raw_hour, bool) or not isinstance(raw_hour, int):
            raise ValueError("whole hour required")
        hour = raw_hour
        speed = request.data["speed"]
    except (KeyError, ValueError, TypeError):
        raise ValidationError("انتخاب برنامه معتبر نیست")
    today = now_tehran().date()
    if not today <= selected <= today+timedelta(days=7) or not 0 <= hour <= 23 or speed not in ("slow","medium","fast"):
        raise ValidationError("انتخاب برنامه معتبر نیست")
    for _ in range(5):
        try:
            with transaction.atomic():
                plan = SharedRoutePlan.objects.create(code=secrets.token_urlsafe(6), route=route, date=selected, start_hour=hour, speed=speed, expires_at=now_tehran()+timedelta(days=30))
            break
        except IntegrityError: continue
    else: raise ValidationError("ساخت لینک ممکن نشد؛ دوباره تلاش کنید")
    response = Response({"path": f"/p/{plan.code}", "expires_at": plan.expires_at.isoformat()},status=201)
    response["Cache-Control"] = "no-store"
    return response

def open_share(request, code):
    from urllib.parse import urlencode
    plan = SharedRoutePlan.objects.select_related("route").filter(code=code, expires_at__gt=now_tehran(), route__is_active=True).first()
    if plan is None:
        from django.http import HttpResponse
        return HttpResponse("این لینک پیدا نشد یا اعتبار آن تمام شده است.",status=404,headers={"Cache-Control":"no-store","X-Robots-Tag":"noindex, nofollow"})
    today = now_tehran().date()
    expired = plan.date < today
    params = {"date": (today if expired else plan.date).isoformat(), "start_time": f"{plan.start_hour:02}:00", "speed": plan.speed}
    if expired: params["past_program"] = "1"
    response = HttpResponseRedirect(f"/routes/{plan.route.slug}?{urlencode(params)}")
    response["Cache-Control"] = "no-store"
    response["X-Robots-Tag"] = "noindex, nofollow"
    return response
