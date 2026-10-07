from django.urls import path
from . import views, mail_views

app_name = "commercial"
urlpatterns = [
    path("mail/", mail_views.dashboard, name="mail"),
    path("mail/incoming/<int:pk>/", mail_views.incoming, name="mail-incoming"),
    path("", views.index, name="index"),
    path("new/", views.new_account, name="new"),
    path("research/", views.research, name="research"),
    path("import/", views.import_csv, name="import"),
    path("export/", views.export_csv, name="export"),
    path("<uuid:pk>/", views.detail, name="detail"),
    path("<uuid:pk>/draft/", views.draft, name="draft"),
    path("<uuid:pk>/extract/", views.import_extract, name="extract"),
]
