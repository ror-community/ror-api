from rest_framework import viewsets, routers, status
from rest_framework.response import Response
from django.http import HttpResponse
from django.views import View
from django.shortcuts import redirect
from rest_framework.permissions import BasePermission
from rest_framework.views import APIView
from rest_framework.parsers import FormParser, MultiPartParser
from rorapi.settings import DATA
import mimetypes
import magic

from rorapi.common.create_update import new_record_from_json, update_record_from_json
from rorapi.common.csv_bulk import process_csv
from rorapi.common.csv_utils import validate_csv
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

class OurTokenPermission(BasePermission):
    """
    Allows access only to using our token and user name.
    """

    def has_permission(self, request, view):
        has_permission = False
        if request.method == 'GET':
            has_permission = True
        else:
            header_token = request.headers.get("Token", None)
            header_user = request.headers.get("Route-User", None)
            user = os.environ.get("ROUTE_USER")
            token = os.environ.get("TOKEN")
            if header_token == token and header_user == user:
                has_permission = True

        return has_permission


class OrganizationViewSet(viewsets.ViewSet):
    permission_classes = [OurTokenPermission]

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

    def create(self, request, version=REST_FRAMEWORK["DEFAULT_VERSION"]):
        errors = None
        if version == "v2":
            json_input = request.data
            if 'id' in json_input and (json_input['id'] is not None and json_input['id'] != ""):
                errors = Errors(["Value {} found in ID field. New records cannot contain a value in the ID field".format(json_input['id'])])
            else:
                create_error, valid_data = new_record_from_json(json_input, version)
                if create_error:
                    errors = Errors([create_error])
        else:
            errors = Errors(["Version {} does not support creating records".format(version)])
        if errors is not None:
            print(errors)
            return Response(
                ErrorsSerializer(errors).data, status=status.HTTP_400_BAD_REQUEST
            )
        serializer = OrganizationSerializerV2(valid_data)
        return Response(serializer.data)

    def update(self, request, pk=None, version=REST_FRAMEWORK["DEFAULT_VERSION"]):
        errors = None
        if version == "v2":
            ror_id = get_ror_id(pk)
            if ror_id is None:
                errors = Errors(["'{}' is not a valid ROR ID".format(pk)])
                return Response(
                    ErrorsSerializer(errors).data, status=status.HTTP_404_NOT_FOUND
                )
            errors, organization = retrieve_organization(ror_id, version)
            if organization is None:
                return Response(
                    ErrorsSerializer(errors).data, status=status.HTTP_404_NOT_FOUND
                )
            json = request.data
            if 'id' not in json:
                errors = Errors(["No value found in ID field. Updated records must include a value in the ID field"])
            elif get_ror_id(json['id']) != ror_id:
                errors = Errors(["Value {} in IDs field does not match resource ID specified in request URL {}".format(json['id'], pk)])
            else:
                update_error, valid_data = update_record_from_json(json, organization)
                if update_error:
                    errors = Errors([update_error])
        else:
            errors = Errors(["Version {} does not support creating records".format(version)])
        if errors is not None:
            return Response(
                ErrorsSerializer(errors).data, status=status.HTTP_400_BAD_REQUEST
            )
        serializer = OrganizationSerializerV2(valid_data)
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


class GenerateAddress(APIView):
    permission_classes = [OurTokenPermission]

    def get(self, request, geonamesid, version=REST_FRAMEWORK["DEFAULT_VERSION"]):
        if version == 'v2':
            address = ua.new_geonames_v2(geonamesid)
        else:
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

    def get(self, request, branch, version=REST_FRAMEWORK["DEFAULT_VERSION"]):
        st = 200
        msg = process_files(branch, version)
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
        msg = management.call_command("setup", filename, schema=schema, testdata=testdata)
        if 'ERROR' in msg:
            st = 400

        return Response({"status": msg}, status=st)


class BulkUpdate(APIView):
    permission_classes = [OurTokenPermission]
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, version=REST_FRAMEWORK["DEFAULT_VERSION"]):
        errors = None
        if version == 'v2':
            if request.data:
                file_object = request.data['file']
                mime_type = magic.from_buffer(file_object.read(2048))
                print(mime_type)
                if "ASCII text" in mime_type or "UTF-8 Unicode text" in mime_type or "CSV text" in mime_type:
                    file_object.seek(0)
                    csv_validation_errors = validate_csv(file_object)
                    if len(csv_validation_errors) == 0:
                        file_object.seek(0)
                        process_csv_error, msg = process_csv(file_object, version)
                        print("views msg")
                        print(msg)
                        print("views type msg")
                        print(type(msg))
                        if process_csv_error:
                            errors = Errors([process_csv_error])
                    else:
                        errors=Errors(csv_validation_errors)
                else:
                    errors = Errors(["File upload must be CSV. File type '{}' is not supported".format(mime_type)])
            else:
                    errors = Errors(["Could not processs request. No data included in request."])
        else:
            errors = Errors(["Version {} does not support creating records".format(version)])
        if errors is not None:
            print(errors.__dict__)
            return Response(
                ErrorsSerializer(errors).data, status=status.HTTP_400_BAD_REQUEST
            )

        return Response(
            msg,
            status=status.HTTP_201_CREATED
        )