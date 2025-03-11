from django.urls import path
from rorapi.v2.views import ClientRegistrationView, ValidateClientView


urlpatterns = [
    path('client-id/', ClientRegistrationView.as_view(), name='client-registration'),
    path('validate-client-id/<uuid:client_id>/', ValidateClientView.as_view(), name='validate-client-id'),
]
