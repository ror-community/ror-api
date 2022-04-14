from django.conf.urls import url, include
from django.urls import path
from rest_framework.documentation import include_docs_urls

from . import views
from rorapi.views import HeartbeatView,GenerateAddress,GenerateId,IndexData

urlpatterns = [
    # Health check
    url(r"^heartbeat$", HeartbeatView.as_view()),
    # Using REST API
    path('generateaddress/<str:geonamesid>', GenerateAddress.as_view()),
    url(r"^generateid$", GenerateId.as_view()),
    path('indexdata/<str:branch>', IndexData.as_view()),
    url(r"^", include(views.organizations_router.urls)),
    url(r"^docs/", include_docs_urls(title="Research Organization Registry")),
    # Prometheus
    url("", include("django_prometheus.urls")),
]
