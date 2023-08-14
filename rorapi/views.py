from rest_framework import viewsets, routers, status
from rest_framework.response import Response
from django.http import HttpResponse
from django.views import View
from django.shortcuts import redirect
from rest_framework.authentication import BasicAuthentication
from rest_framework.permissions import BasePermission
from rest_framework.views import APIView
import json

from .settings import REST_FRAMEWORK
from .matching import match_organizations
from .models_v1 import OrganizationSerializerV1, ListResultSerializerV1, \
    MatchingResultSerializerV1, ErrorsV1, ErrorsSerializerV1
from .models_v2 import OrganizationSerializerV2, ListResultSerializerV2, \
    MatchingResultSerializerV2, ErrorsV2, ErrorsSerializerV2
from .queries import search_organizations, retrieve_organization, get_ror_id
from urllib.parse import urlencode
import os
import update_address as ua
from rorapi.management.commands.generaterorid import check_ror_id
from rorapi.management.commands.indexror import process_files

class OrganizationViewSet(viewsets.ViewSet):
    lookup_value_regex = \
        r'((https?(:\/\/|%3A%2F%2F))?ror\.org(\/|%2F))?.*'

    def list(self, request, version=REST_FRAMEWORK['DEFAULT_VERSION']):
        print(version)
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
            errors, organizations = match_organizations(params, version)
        else:
            errors, organizations = search_organizations(params, version)
        if errors is not None:
            if version == 'v2':
                return Response(ErrorsSerializerV2(errors).data)
            return Response(ErrorsSerializerV1(errors).data)
        if 'affiliation' in params:
            if version == 'v2':
                serializer = MatchingResultSerializerV2(organizations)
            else:
                serializer = MatchingResultSerializerV1(organizations)
        else:
            if version == 'v2':
                serializer = ListResultSerializerV2(organizations)
            else:
                serializer = ListResultSerializerV1(organizations)
        return Response(serializer.data)

    def retrieve(self, request, pk=None, version=REST_FRAMEWORK['DEFAULT_VERSION']):
        ror_id = get_ror_id(pk)
        if ror_id is None:
            if  version == 'v2':
                errors = ErrorsV2(['\'{}\' is not a valid ROR ID'.format(pk)])
                return Response(ErrorsSerializerV2(errors).data, status=status.HTTP_404_NOT_FOUND)
            errors = ErrorsV1(['\'{}\' is not a valid ROR ID'.format(pk)])
            return Response(ErrorsSerializerV1(errors).data, status=status.HTTP_404_NOT_FOUND)
        errors, organization = retrieve_organization(ror_id, version)
        if errors is not None:
            if version == '2':
                return Response(ErrorsSerializerV2(errors).data, status=status.HTTP_404_NOT_FOUND)
            return Response(ErrorsSerializerV1(errors).data, status=status.HTTP_404_NOT_FOUND)
        if version == 'v2':
            serializer = OrganizationSerializerV2(organization)
        else:
            serializer = OrganizationSerializerV1(organization)
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

class OurTokenPermission(BasePermission):
    """
    Allows access only to using our token and user name.
    """
    def has_permission(self, request, view):
        header_token = request.headers.get('Token',None)
        header_user = request.headers.get('Route-User',None)
        user = os.environ.get('ROUTE_USER')
        token = os.environ.get('TOKEN')
        return (header_token == token and header_user == user)

class GenerateAddress(APIView):
    permission_classes = [OurTokenPermission]
    def get(self, request, geonamesid):
        address = ua.new_geonames(geonamesid)
        return Response(address)

class GenerateId(APIView):
    permission_classes = [OurTokenPermission]
    def get(self, request):
        id = check_ror_id()
        return Response({'id': id})

class IndexData(APIView):
    permission_classes = [OurTokenPermission]
    def get(self, request, branch):
        st = 200
        msg = process_files(branch)
        if msg['status'] == "ERROR":
            st = 400
        return Response({'status': msg['status'], 'msg': msg['msg']}, status=st)
