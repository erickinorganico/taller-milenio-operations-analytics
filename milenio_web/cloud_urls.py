from django.urls import include, path

# Internal CRM remains available. AccessMiddleware closes commercial mail routes.
urlpatterns = [path("commercial/", include("commercial.urls")), path("", include("workshop.urls"))]
