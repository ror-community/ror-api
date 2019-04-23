from rest_framework import viewsets, routers
from rest_framework.response import Response

from .models import OrganizationSerializer, ListResultSerializer, \
    ErrorsSerializer
from .queries import search_organizations, retrieve_organization


class OrganizationViewSet(viewsets.ViewSet):

    lookup_value_regex = r'https:\/\/ror\.org\/0\w{6}\d{2}'

    def list(self, request):
        errors, organizations = search_organizations(request.GET)
        if errors is not None:
            return Response(ErrorsSerializer(errors).data)
        serializer = ListResultSerializer(organizations)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        errors, organization = retrieve_organization(pk)
        if errors is not None:
            return Response(ErrorsSerializer(errors).data)
        serializer = OrganizationSerializer(organization)
        return Response(serializer.data)


organizations_router = routers.DefaultRouter(trailing_slash=False)
organizations_router.register(r'organizations', OrganizationViewSet,
                              basename='organization')
