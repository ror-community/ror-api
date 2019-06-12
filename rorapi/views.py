from rest_framework import viewsets, routers
from rest_framework.response import Response
from django.http import HttpResponse
from django.views import View

from .models import OrganizationSerializer, ListResultSerializer, \
    ErrorsSerializer
from .queries import search_organizations, retrieve_organization, get_ror_id


class OrganizationViewSet(viewsets.ViewSet):

    lookup_value_regex = r'((https?:\/\/)?ror\.org\/)?0\w{6}\d{2}'

    def list(self, request):
        params = request.GET.dict()
        if 'format' in params:
            del params['format']
        errors, organizations = search_organizations(params)
        if errors is not None:
            return Response(ErrorsSerializer(errors).data)
        serializer = ListResultSerializer(organizations)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        ror_id = get_ror_id(pk)
        errors, organization = retrieve_organization(ror_id)
        if errors is not None:
            return Response(ErrorsSerializer(errors).data)
        serializer = OrganizationSerializer(organization)
        return Response(serializer.data)


organizations_router = routers.DefaultRouter(trailing_slash=False)
organizations_router.register(r'organizations', OrganizationViewSet,
                              basename='organization')


class HeartbeatView(View):

    def get(self, request):
        return HttpResponse('Ok')
