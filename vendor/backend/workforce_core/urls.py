"""
workforce_core/urls.py

Root URLconf for the dedicated Workforce Backend (Port 8001).
Exposes /api/workforce/* and core auth routes.
"""







from django.conf import settings
from django.conf.urls.static import static
from django.db import connection
from django.http import JsonResponse
from django.urls import include, path
from django.utils import timezone


def health_check(request):
    """
    Generic liveness/readiness probe for this app.

    Bug found (gap): the only health check this app had was
    /api/workforce/dispatch/health/ (WorkforceDispatchHealthView), which
    reports on the dispatch background command's heartbeat specifically --
    useful, but not what a load balancer or uptime monitor needs to answer
    "is this Django process even up and able to reach its database?" This
    is deliberately app-agnostic and has no dependency on any one
    subsystem's internal state, unlike the dispatch-specific check.
    """
    db_ok = True
    db_error = ""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except Exception as exc:
        db_ok = False
        db_error = str(exc)

    payload = {
        "status": "ok" if db_ok else "error",
        "database": db_ok,
        "time": timezone.now().isoformat(),
    }
    if db_error:
        payload["database_error"] = db_error
    return JsonResponse(payload, status=200 if db_ok else 503)


urlpatterns = [
    # Generic health check (X-13): distinct from the dispatch-engine-
    # specific /api/workforce/dispatch/health/ below -- see health_check()
    # above.
    path("health/", health_check, name="health-check"),
    path("api/health/", health_check, name="api-health-check"),
    # Dedicated Workforce API namespace
    path("api/workforce/", include("workforce_api.urls")),
    # Vendor & Employee Wallet namespace
    path("api/workforce/", include("vendor_wallet.urls")),
    # Shared /api/auth/ endpoints for login/me/logout
    path("api/auth/", include("accounts.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
