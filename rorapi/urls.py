from django.conf.urls import url, include
from rest_framework.documentation import include_docs_urls

from . import views
from rorapi.views import HeartbeatView

urlpatterns = [
    # Health check
    url(r"^heartbeat$", HeartbeatView.as_view()),
    # Using REST API
    url(r"^", include(views.organizations_router.urls)),
    url(r"^docs/", include_docs_urls(title="Research Organization Registry")),
    # Prometheus
    url("", include("django_prometheus.urls")),
]
