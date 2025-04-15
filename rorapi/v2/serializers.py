from rest_framework import serializers
import bleach
import pycountry
import re
from rorapi.v2.models import Client
from rorapi.common.serializers import BucketSerializer, OrganizationRelationshipsSerializer

class AggregationsSerializer(serializers.Serializer):
    types = BucketSerializer(many=True)
    countries = BucketSerializer(many=True)
    continents = BucketSerializer(many=True)
    statuses = BucketSerializer(many=True)

class AdminDetailsSerializer(serializers.Serializer):
    date = serializers.DateTimeField()
    schema_version = serializers.CharField()


class AdminSerializer(serializers.Serializer):
    created = AdminDetailsSerializer()
    last_modified = AdminDetailsSerializer()


class OrganizationNameSerializer(serializers.Serializer):
    lang = serializers.CharField()
    types = serializers.StringRelatedField(many=True)
    value = serializers.CharField()


class ExternalIdSerializer(serializers.Serializer):
    all = serializers.StringRelatedField(many=True)
    preferred = serializers.CharField()
    type = serializers.CharField()


class LinkSerializer(serializers.Serializer):
    type = serializers.CharField()
    value = serializers.CharField()


class GeoNamesDetailsSerializer(serializers.Serializer):
    continent_code = serializers.CharField()
    continent_name = serializers.CharField()
    country_code = serializers.CharField()
    country_name = serializers.CharField()
    country_subdivision_code = serializers.CharField()
    country_subdivision_name = serializers.CharField()
    lat = serializers.DecimalField(
        max_digits=None, decimal_places=10, coerce_to_string=False
    )
    lng = serializers.DecimalField(
        max_digits=None, decimal_places=10, coerce_to_string=False
    )
    name = serializers.StringRelatedField()


class OrganizationLocationSerializer(serializers.Serializer):
    geonames_details = GeoNamesDetailsSerializer()
    geonames_id = serializers.IntegerField()


class OrganizationSerializer(serializers.Serializer):
    admin = AdminSerializer()
    domains = serializers.StringRelatedField(many=True)
    established = serializers.IntegerField()
    external_ids = ExternalIdSerializer(many=True)
    id = serializers.CharField()
    links = LinkSerializer(many=True)
    locations = OrganizationLocationSerializer(many=True)
    names = OrganizationNameSerializer(many=True)
    relationships = OrganizationRelationshipsSerializer(many=True)
    status = serializers.CharField()
    types = serializers.StringRelatedField(many=True)


class ListResultSerializer(serializers.Serializer):
    number_of_results = serializers.IntegerField()
    time_taken = serializers.IntegerField()
    items = OrganizationSerializer(many=True)
    meta = AggregationsSerializer()


class MatchedOrganizationSerializer(serializers.Serializer):
    substring = serializers.CharField()
    score = serializers.FloatField()
    matching_type = serializers.CharField()
    chosen = serializers.BooleanField()
    organization = OrganizationSerializer()


class MatchingResultSerializer(serializers.Serializer):
    number_of_results = serializers.IntegerField()
    items = MatchedOrganizationSerializer(many=True)


class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = ['email', 'name', 'institution_name', 'institution_ror', 'country_code', 'ror_use']

    def validate_email(self, value):
        """Validate the email format and ensure it's unique."""
        if Client.objects.filter(email=value).exists():
            raise serializers.ValidationError("A client with this email already exists.")
        return value

    def validate_name(self, value):
        """Sanitize name and validate length."""
        value = bleach.clean(value)  # Sanitize to strip HTML
        if len(value) > 255:
            raise serializers.ValidationError("Name cannot be longer than 255 characters.")
        return value

    def validate_institution_name(self, value):
        """Sanitize institution name and validate length."""
        value = bleach.clean(value)  # Sanitize to strip HTML
        if len(value) > 255:
            raise serializers.ValidationError("Institution name cannot be longer than 255 characters.")
        return value

    def validate_institution_ror(self, value):
        """Validate and format institution ROR to match 'https://ror.org/XXXXX'."""
        value = bleach.clean(value)  # Sanitize to strip HTML
        ror_regex = r'https://ror\.org/[A-Za-z0-9]+'
        if not re.match(ror_regex, value):
            raise serializers.ValidationError("Institution ROR must be in the format 'https://ror.org/XXXXX'.")
        return value

    def validate_country_code(self, value):
        """Validate that the country code is a valid ISO 3166-1 alpha-2 country code."""
        value = value.strip().upper()  # Normalize to uppercase
        if len(value) != 2 or not pycountry.countries.get(alpha_2=value):
            raise serializers.ValidationError(f"{value} is not a valid ISO 3166-1 alpha-2 country code.")
        return value

    def validate_ror_use(self, value):
        """Sanitize ror_use and validate length."""
        value = bleach.clean(value)  # Sanitize to strip HTML
        if len(value) > 500:
            raise serializers.ValidationError("ROR use cannot be longer than 500 characters.")
        return value
