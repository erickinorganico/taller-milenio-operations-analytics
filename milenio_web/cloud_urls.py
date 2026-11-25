from django.urls import include, path
from workshop.access import WORKSHOP_AGENT_PATH
from workshop.agent_api import endpoint as workshop_agent

# Internal CRM remains available. AccessMiddleware closes commercial mail routes.
urlpatterns = [path(WORKSHOP_AGENT_PATH.lstrip("/"), workshop_agent),
               path("commercial/", include("commercial.urls")), path("", include("workshop.urls"))]
