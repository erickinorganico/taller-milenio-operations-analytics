from django.contrib.auth.views import LogoutView
from django.urls import path
from . import views as v
from . import insight_views as iv
from . import import_views
urlpatterns=[
 path("",v.home,name="home"),path("setup/",v.setup),path("login/",v.sign_in),path("logout/",LogoutView.as_view()),path("health/",v.health),path("static/<path:path>",v.static_asset),
 path("records/<slug:key>/",v.records),path("records/<slug:key>/new/",v.edit_record),path("records/<slug:key>/<int:pk>/edit/",v.edit_record),
 path("orders/",v.orders),path("orders/new/",v.new_order),path("orders/<int:pk>/",v.order_detail),path("orders/<int:pk>/<slug:action>/",v.order_action),path("inspection/<int:pk>/photo/",v.inspection_photo),
 path("inventory/",v.inventory),path("inventory/<int:pk>/adjust/",v.stock_adjust),path("purchases/<int:pk>/",v.purchase_detail),path("purchases/<int:pk>/place/",v.place_purchase),path("purchase-lines/<int:pk>/receive/",v.receive_purchase),path("finance/",v.finance),path("fleets/",v.fleets),path("towing/",v.towing),path("towing/new/",v.new_tow),path("towing/<int:pk>/update/",v.tow_action),
 path("data/",v.data_index),path("data/<slug:key>/",v.data_table),path("import/",import_views.import_catalog),path("team/",v.team),path("team/<int:pk>/edit/",v.edit_team),path("account/",v.account),path("guide/",v.guide),
 path("documents/<slug:kind>/<int:pk>/",v.document),
 path("metrics/",iv.metrics),path("agents/",iv.agents),path("agents/run/",iv.run_agents),path("proposals/<int:pk>/review/",iv.review_proposal),path("tasks/<int:pk>/update/",iv.update_task)
]
