from rest_framework import serializers
from rorapi.common.serializers import (
    AggregationsSerializer,
    OrganizationRelationshipsSerializer,
)


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
