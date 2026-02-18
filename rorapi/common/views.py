import csv
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
from rorapi.settings import REST_FRAMEWORK, ES7, ES_VARS
from rorapi.common.matching import match_organizations
from rorapi.common.matching_single_search import match_organizations as single_search_match_organizations
from rorapi.common.models import (
    Errors
)
from rorapi.common.serializers import ErrorsSerializer

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
from rorapi.management.commands.indexror import process_files
from django.core import management
import rorapi.management.commands.indexrordump
from django.core.mail import EmailMultiAlternatives
from django.utils.timezone import now
from rorapi.v2.models import Client
from rorapi.v2.serializers import ClientSerializer

class ClientRegistrationView(APIView):
    def post(self, request, version='v2'):
        serializer = ClientSerializer(data=request.data)
        if serializer.is_valid():
            client = serializer.save()

            subject = 'ROR API client ID'
            from_email = "ROR API Support <api@ror.org>"
            recipient_list = [client.email]

            html_content = self._get_html_content(client.client_id)
            text_content = self._get_text_content(client.client_id)

            msg = EmailMultiAlternatives(subject, text_content, from_email, recipient_list)
            msg.attach_alternative(html_content, "text/html")
            msg.send()

            return Response({'client_id': client.client_id}, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def _get_text_content(self, client_id):
        return f"""
            Thank you for registering for a ROR API client ID!

            Your ROR API client ID is:
            {client_id}

            This client ID is not used for authentication or authorization, and is therefore not secret and can be sent as plain text.

            In order to receive a rate limit of 2000 requests per 5 minute period, please include this client ID with your ROR API requests, in a custom HTTP header named Client-Id, for example:

            curl -H "Client-Id: {client_id}" https://api.ror.org/organizations?query=oxford

            Requests without a valid client ID are subject to a rate limit of 50 requests per 5 minute period.

            We do not provide a way to recover or revoke a lost client ID. If you lose track of your client ID, please register a new client ID. For more information about ROR API client IDs, see https://ror.readme.io/docs/client-id

            If you have questions, please see ROR documentation or contact us at support@ror.org

            Cheers,
            The ROR Team
            support@ror.org
            https://ror.org
        """


    def _get_html_content(self, client_id):
        return f"""
            <div style="font-family: Arial, sans-serif; line-height: 1.5;">
                <p>Thank you for registering for a ROR API client ID!</p>
                <p><strong>Your ROR API client ID is:</strong></p>
                <pre style="background:#f4f4f4;padding:10px;">{client_id}</pre>
                <p>This client ID is not used for authentication or authorization, and is therefore not secret and can be sent as plain text.</p>
                <p>In order to receive a rate limit of <strong>2000 requests per 5 minute period</strong>, please include this client ID with your ROR API requests, in a custom HTTP header named <code>Client-Id</code>, for example:</p>
                <pre style="background:#f4f4f4;padding:10px;">curl -H "Client-Id: {client_id}" https://api.ror.org/organizations?query=oxford</pre>
                <p>Requests without a valid client ID are subject to a rate limit of 50 requests per 5 minute period.</p>
                <p>We do not provide a way to recover or revoke a lost client ID. If you lose track of your client ID, please register a new one.</p>
                <p>For more information about ROR API client IDs, see <a href="https://ror.readme.io/docs/client-id/">our documentation</a>.</p>
                <p>If you have questions, please see the ROR documentation or contact us at <a href="mailto:support@ror.org">support@ror.org</a>.</p>
                <p>Cheers,<br>
                The ROR Team<br>
                <a href="mailto:support@ror.org">support@ror.org</a><br>
                <a href="https://ror.org">https://ror.org</a></p>
            </div>
        """


class ValidateClientView(APIView):
    def get(self, request, client_id):
        client_exists = Client.objects.filter(client_id=client_id).exists()

        return Response({'valid': client_exists}, status=status.HTTP_200_OK)

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
            if "single_search" in params:
                errors, organizations = single_search_match_organizations(params)
            else:
                errors, organizations = match_organizations(params)
        else:
            errors, organizations = search_organizations(params)
        if errors is not None:
            return Response(ErrorsSerializer(errors).data)
        if "affiliation" in params:
            serializer = MatchingResultSerializerV2(organizations)
        else:
            serializer = ListResultSerializerV2(organizations)
        return Response(serializer.data)

    def retrieve(self, request, pk=None, version=REST_FRAMEWORK["DEFAULT_VERSION"]):
        ror_id = get_ror_id(pk)
        if ror_id is None:
            errors = Errors(["'{}' is not a valid ROR ID".format(pk)])
            return Response(
                ErrorsSerializer(errors).data, status=status.HTTP_404_NOT_FOUND
            )
        errors, organization = retrieve_organization(ror_id)
        if errors is not None:
            return Response(
                ErrorsSerializer(errors).data, status=status.HTTP_404_NOT_FOUND
            )
        serializer = OrganizationSerializerV2(organization)
        return Response(serializer.data)

    def create(self, request, version=REST_FRAMEWORK["DEFAULT_VERSION"]):
        errors = None
        json_input = request.data
        if 'id' in json_input and (json_input['id'] is not None and json_input['id'] != ""):
            errors = Errors(["Value {} found in ID field. New records cannot contain a value in the ID field".format(json_input['id'])])
        else:
            create_error, valid_data = new_record_from_json(json_input, 'v2')
            if create_error:
                errors = Errors([create_error])
        if errors is not None:
            return Response(
                ErrorsSerializer(errors).data, status=status.HTTP_400_BAD_REQUEST
            )
        serializer = OrganizationSerializerV2(valid_data)
        return Response(serializer.data)

    def update(self, request, pk=None, version=REST_FRAMEWORK["DEFAULT_VERSION"]):
        errors = None
        ror_id = get_ror_id(pk)
        if ror_id is None:
            errors = Errors(["'{}' is not a valid ROR ID".format(pk)])
            return Response(
                ErrorsSerializer(errors).data, status=status.HTTP_404_NOT_FOUND
            )
        errors, organization = retrieve_organization(ror_id)
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
        try:
            if ES7.indices.exists(ES_VARS['INDEX_V2']):
                return HttpResponse("OK")
        except Exception:
            pass
        return HttpResponse(status=500)


class GenerateAddress(APIView):
    permission_classes = [OurTokenPermission]

    def get(self, request, geonamesid, version=REST_FRAMEWORK["DEFAULT_VERSION"]):
        address = ua.new_geonames_v2(geonamesid)
        return Response(address)


class GenerateId(APIView):
    permission_classes = [OurTokenPermission]

    def get(self, request, version=REST_FRAMEWORK["DEFAULT_VERSION"]):
        id = check_ror_id()
        print("Generated ID: {}".format(id))
        return Response({"id": id})

class IndexData(APIView):
    permission_classes = [OurTokenPermission]

    def get(self, request, branch, version=REST_FRAMEWORK["DEFAULT_VERSION"]):
        st = 200
        msg = process_files(branch, 'v2')
        if msg["status"] == "ERROR":
            st = 400
        return Response({"status": msg["status"], "msg": msg["msg"]}, status=st)

class IndexDataDump(APIView):
    permission_classes = [OurTokenPermission]

    def get(self, request, filename, dataenv, version=REST_FRAMEWORK["DEFAULT_VERSION"]):
        # Always use v2 schema - v1 indexing support has been removed
        schema = 2
        testdata = True
        st = 200
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
        validate_only = False
        errors = None
        if request.data:
            file_object = request.data.get('file')
            if file_object is None:
                errors = Errors(["File upload required. 'file' field is missing."])
            else:
                mime_type = magic.from_buffer(file_object.read(2048))
                print(mime_type)
                if "ASCII text" in mime_type or "UTF-8 text" in mime_type or "UTF-8 Unicode text" in mime_type or "CSV text" in mime_type:
                    file_object.seek(0)
                    csv_validation_errors = validate_csv(file_object)
                    if len(csv_validation_errors) == 0:
                        file_object.seek(0)
                        params = request.GET.dict()
                        if "validate" in params:
                            validate_only = True
                        process_csv_error, msg = process_csv(file_object, 'v2', validate_only)
                        if process_csv_error:
                            errors = Errors([process_csv_error])
                    else:
                        errors = Errors(csv_validation_errors)
                else:
                    errors = Errors(["File upload must be CSV. File type '{}' is not supported".format(mime_type)])
        else:
            errors = Errors(["Could not process request. No data included in request."])
        if errors is not None:
            print(errors.__dict__)
            return Response(
                ErrorsSerializer(errors).data, status=status.HTTP_400_BAD_REQUEST
            )
        if validate_only:
            with open(msg) as file:
                response = HttpResponse(file, content_type='text/csv')
                response['Content-Disposition'] = 'attachment; filename=reports.csv'
            return response

        return Response(
            msg,
            status=status.HTTP_201_CREATED
        )