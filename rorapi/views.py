from rest_framework import viewsets, routers
from rest_framework.response import Response
from django.http import HttpResponse
from django.views import View
from django.shortcuts import redirect

from .matching import match_organizations
from .models import OrganizationSerializer, ListResultSerializer, \
    MatchingResultSerializer, ErrorsSerializer
from .queries import search_organizations, retrieve_organization, get_ror_id
from urllib.parse import urlencode


class OrganizationViewSet(viewsets.ViewSet):

    lookup_value_regex = \
        r'((https?(:\/\/|%3A%2F%2F))?ror\.org(\/|%2F))?0\w{6}\d{2}'

    def list(self, request):
        params = request.GET.dict()
        if 'query.name' in params or 'query.names' in params:
            param_name = \
                'query.name' if 'query.name' in params else 'query.names'
            params['query'] = params[param_name]
            del params[param_name]
            return redirect('{}?{}'.format(request.path, urlencode(params)))
        if 'format' in params:
            del params['format']

        if 'affiliation' in params:
            errors, organizations = match_organizations(params)
        else:
            errors, organizations = search_organizations(params)
        if errors is not None:
            return Response(ErrorsSerializer(errors).data)
        if 'affiliation' in params:
            serializer = MatchingResultSerializer(organizations)
        else:
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
organizations_router.register(r'organizations',
                              OrganizationViewSet,
                              basename='organization')


class HeartbeatView(View):
    def get(self, request):
        try:
            errors, organizations = search_organizations({})
            if errors is None:
                return HttpResponse('OK')
        except:
            pass
        return HttpResponse(status=500)
