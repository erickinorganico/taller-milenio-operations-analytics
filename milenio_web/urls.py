from django.urls import include, path
from commercial.agent_api import endpoint
urlpatterns = [path("agent/v1/action", endpoint), path("commercial/", include("commercial.urls")), path("", include("workshop.urls"))]
