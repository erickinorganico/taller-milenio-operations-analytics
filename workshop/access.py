from functools import wraps
from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect
from django.shortcuts import redirect

ROLES = {"manager": "Gerencia", "advisor": "Recepción", "technician": "Técnico", "parts": "Refacciones", "finance": "Administración", "viewer": "Consulta gerencial"}
CAPABILITIES = {
    "manage": {"manager"}, "reception": {"manager", "advisor"},
    "work": {"manager", "advisor", "technician"},
    "stock": {"manager", "parts"}, "finance": {"manager", "finance"},
    "review": {"manager", "advisor", "finance"},
    "complete_task": {"manager", "advisor", "finance", "technician", "parts"},
    "office_read": {"manager", "advisor", "finance", "viewer"},
    "finance_read": {"manager", "finance", "viewer"},
    "data_read": {"manager", "finance", "viewer"},
    "intelligence_read": {"manager", "advisor", "finance", "viewer"},
    "orders_read_all": {"manager", "advisor", "parts", "finance", "viewer"},
    "stock_read": {"manager", "advisor", "parts", "finance", "viewer", "technician"},
}

def can(user, capability):
    return bool(user.is_authenticated and (user.is_superuser or user.groups.filter(name__in=CAPABILITIES.get(capability, set())).exists()))

def require(capability):
    def decorator(view):
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect(settings.LOGIN_URL)
            if not can(request.user, capability):
                raise PermissionDenied("Tu rol no permite esta acción.")
            return view(request, *args, **kwargs)
        return wrapped
    return decorator

def navigation(request):
    return {"app_mode": settings.MILENIO_MODE, "cap": {key: can(request.user, key) for key in CAPABILITIES}, "role_label": "Gerencia" if request.user.is_authenticated and request.user.is_superuser else ", ".join(ROLES.get(name, name) for name in request.user.groups.values_list("name", flat=True)) if request.user.is_authenticated else "", "native_enabled": settings.MILENIO_CODEX_ENABLED}

class AccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
    def __call__(self, request):
        if not request.path.startswith(("/static/", "/health/")):
            configured = User.objects.filter(is_superuser=True, is_active=True).exists()
            if not configured and request.path != "/setup/":
                return redirect("/setup/")
            if configured and request.path == "/setup/":
                return redirect("/")
            if configured and not request.user.is_authenticated and request.path not in {"/login/"}:
                return HttpResponseRedirect("/login/")
        response = self.get_response(request)
        if not request.path.startswith("/static/"):
            response["Cache-Control"] = "no-store"
        response["Content-Security-Policy"] = "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'"
        response["Referrer-Policy"] = "same-origin"
        return response
