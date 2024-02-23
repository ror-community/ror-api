from rest_framework import viewsets, routers, status
from rest_framework.response import Response
from django.http import HttpResponse
from django.views import View
from django.shortcuts import redirect
from rest_framework.authentication import BasicAuthentication
from rest_framework.permissions import BasePermission
from rest_framework.views import APIView
import json

from rorapi.settings import REST_FRAMEWORK
from rorapi.common.matching import match_organizations
from rorapi.common.models import (
    Errors
)
from rorapi.common.serializers import ErrorsSerializer

from rorapi.v1.serializers import (
    OrganizationSerializer as OrganizationSerializerV1,
    ListResultSerializer as ListResultSerializerV1,
    MatchingResultSerializer as MatchingResultSerializerV1
)
from rorapi.v2.serializers import (
    OrganizationSerializer as OrganizationSerializerV2,
    ListResultSerializer as ListResultSerializerV2,
    MatchingResultSerializer as MatchingResultSerializerV2,
)

from rorapi.common.queries import search_organizations, retrieve_organization, get_ror_id
from urllib.parse import urlencode
import os
import update_address as ua
from rorapi.management.commands.generaterorid import check_ror_id
from rorapi.management.commands.generaterorid import check_ror_id
from rorapi.management.commands.indexror import process_files

from django.core import management
import rorapi.management.commands.indexrordump


class OrganizationViewSet(viewsets.ViewSet):
    lookup_value_regex = r"((https?(:\/\/|%3A%2F%2F))?ror\.org(\/|%2F))?.*"

    def list(self, request, version=REST_FRAMEWORK["DEFAULT_VERSION"]):
        params = request.GET.dict()
        if "query.name" in params or "query.names" in params:
            print("redirecting")
            param_name = "query.name" if "query.name" in params else "query.names"
            params["query"] = params[param_name]
            del params[param_name]
            return redirect("{}?{}".format(request.path, urlencode(params)))
        if "format" in params:
            del params["format"]
        if "affiliation" in params:
            errors, organizations = match_organizations(params, version)
        else:
            errors, organizations = search_organizations(params, version)
        if errors is not None:
            return Response(ErrorsSerializer(errors).data)
        if "affiliation" in params:
            if version == "v2":
                serializer = MatchingResultSerializerV2(organizations)
            else:
                serializer = MatchingResultSerializerV1(organizations)
        else:
            if version == "v2":
                serializer = ListResultSerializerV2(organizations)
            else:
                serializer = ListResultSerializerV1(organizations)
        return Response(serializer.data)

    def retrieve(self, request, pk=None, version=REST_FRAMEWORK["DEFAULT_VERSION"]):
        ror_id = get_ror_id(pk)
        if ror_id is None:
            errors = Errors(["'{}' is not a valid ROR ID".format(pk)])
            return Response(
                ErrorsSerializer(errors).data, status=status.HTTP_404_NOT_FOUND
            )
        errors, organization = retrieve_organization(ror_id, version)
        if errors is not None:
            return Response(
                ErrorsSerializer(errors).data, status=status.HTTP_404_NOT_FOUND
            )
        if version == "v2":
            serializer = OrganizationSerializerV2(organization)
        else:
            serializer = OrganizationSerializerV1(organization)
        return Response(serializer.data)


organizations_router = routers.DefaultRouter(trailing_slash=False)
organizations_router.register(
    r"organizations", OrganizationViewSet, basename="organization"
)


class HeartbeatView(View):
    def get(self, request, version=REST_FRAMEWORK["DEFAULT_VERSION"]):
        print(version)
        try:
            errors, organizations = search_organizations({}, version)
            if errors is None:
                return HttpResponse("OK")
        except:
            pass
        return HttpResponse(status=500)


class OurTokenPermission(BasePermission):
    """
    Allows access only to using our token and user name.
    """

    def has_permission(self, request, view):
        header_token = request.headers.get("Token", None)
        header_user = request.headers.get("Route-User", None)
        user = os.environ.get("ROUTE_USER")
        token = os.environ.get("TOKEN")
        return header_token == token and header_user == user


class GenerateAddress(APIView):
    permission_classes = [OurTokenPermission]

    def get(self, request, geonamesid):
        address = ua.new_geonames(geonamesid)
        return Response(address)


class GenerateId(APIView):
    permission_classes = [OurTokenPermission]

    def get(self, request, version=REST_FRAMEWORK["DEFAULT_VERSION"]):
        id = check_ror_id(version)
        print("Generated ID: {}".format(id))
        return Response({"id": id})

class IndexData(APIView):
    permission_classes = [OurTokenPermission]

    def get(self, request, branch):
        st = 200
        msg = process_files(branch)
        if msg["status"] == "ERROR":
            st = 400
        return Response({"status": msg["status"], "msg": msg["msg"]}, status=st)


class IndexDataDump(APIView):
    permission_classes = [OurTokenPermission]

    def get(self, request, filename, dataenv, version=REST_FRAMEWORK["DEFAULT_VERSION"]):
        schema = 1
        testdata = True
        st = 200
        if version == 'v2':
            schema = 2
        if dataenv == 'prod':
            testdata = False
        msg = management.call_command("setup", filename, schema=2, testdata=True)
        if 'ERROR' in msg:
            st = 400

        return Response({"status": msg}, status=st)
