from django.urls import include, re_path
from  . import views
from rorapi.common.views import (
    HeartbeatView,GenerateAddress,GenerateId,IndexData,IndexDataDump,BulkUpdate,ClientRegistrationView,ValidateClientView)

urlpatterns = [
    # Health check
    re_path(r"^(?P<version>v2)\/heartbeat$", HeartbeatView.as_view()),
    re_path(r"^heartbeat$", HeartbeatView.as_view()),
    # Using REST API
    re_path(r"^(?P<version>v2)\/generateaddress\/(?P<geonamesid>[0-9]+)", GenerateAddress.as_view()),
    re_path(r"^generateaddress\/(?P<geonamesid>[^/]+)$", GenerateAddress.as_view()),
    re_path(r"^generateid$", GenerateId.as_view()),
    re_path(r"^(?P<version>v2)\/bulkupdate$", BulkUpdate.as_view()),
    re_path(r"^(?P<version>v2)\/register$", ClientRegistrationView.as_view()),
    re_path(r"^validate-client-id\/(?P<client_id>[^/]+)\/$", ValidateClientView.as_view()),
    re_path(r"^(?P<version>v2)\/indexdata/(?P<branch>.*)", IndexData.as_view()),
    re_path(r"^(?P<version>v2)\/indexdatadump\/(?P<filename>v(\d+\.)?(\d+\.)?(\*|\d+)-\d{4}-\d{2}-\d{2}-ror-data)\/(?P<dataenv>(test|prod))$", IndexDataDump.as_view()),
    re_path(r"^(?P<version>v2)\/", include(views.organizations_router.urls)),
    re_path(r"^", include(views.organizations_router.urls)),
    # Prometheus
    re_path("", include("django_prometheus.urls")),

]
