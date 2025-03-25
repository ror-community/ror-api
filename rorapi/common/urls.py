from django.conf.urls import url, include
from django.urls import path, re_path
from rest_framework.documentation import include_docs_urls
from  . import views
from rorapi.common.views import (
    HeartbeatView,GenerateAddress,GenerateId,IndexData,IndexDataDump,BulkUpdate,ClientRegistrationView,ValidateClientView)

urlpatterns = [
    # Health check
    url(r"^(?P<version>(v1|v2))\/heartbeat$", HeartbeatView.as_view()),
    url(r"^heartbeat$", HeartbeatView.as_view()),
    # Using REST API
    url(r"^(?P<version>(v1|v2))\/generateaddress\/(?P<geonamesid>[0-9]+)", GenerateAddress.as_view()),
    path('generateaddress/<str:geonamesid>', GenerateAddress.as_view()),
    url(r"^generateid$", GenerateId.as_view()),
    re_path(r"^(?P<version>(v1|v2))\/bulkupdate$", BulkUpdate.as_view()),
    re_path(r"^(?P<version>(v1|v2))\/register$", ClientRegistrationView.as_view()),
    path('validate-client-id/<str:client_id>/', ValidateClientView.as_view()),
    url(r"^(?P<version>(v1|v2))\/indexdata/(?P<branch>.*)", IndexData.as_view()),
    url(r"^(?P<version>(v1|v2))\/indexdatadump\/(?P<filename>v(\d+\.)?(\d+\.)?(\*|\d+)-\d{4}-\d{2}-\d{2}-ror-data)\/(?P<dataenv>(test|prod))$", IndexDataDump.as_view()),
    url(r"^(?P<version>(v1|v2))\/", include(views.organizations_router.urls)),
    url(r"^", include(views.organizations_router.urls)),
    url(r"^docs/", include_docs_urls(title="Research Organization Registry")),
    # Prometheus
    url("", include("django_prometheus.urls")),

]
