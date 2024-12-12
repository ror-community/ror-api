from rest_framework import serializers
from rorapi.common.serializers import BucketSerializer, OrganizationRelationshipsSerializer

class AggregationsSerializer(serializers.Serializer):
    types = BucketSerializer(many=True)
    countries = BucketSerializer(many=True)
    statuses = BucketSerializer(many=True)


class OrganizationLabelSerializer(serializers.Serializer):
    label = serializers.CharField()
    iso639 = serializers.CharField()


class CountrySerializer(serializers.Serializer):
    country_name = serializers.CharField()
    country_code = serializers.CharField()


class LicenseSerializer(serializers.Serializer):
    attribution = serializers.StringRelatedField()
    license = serializers.StringRelatedField()


class NutsSerializer(serializers.Serializer):
    name = serializers.CharField()
    code = serializers.CharField()


class AddressGeoNamesSerializer(serializers.Serializer):
    name = serializers.CharField()
    id = serializers.IntegerField()
    ascii_name = serializers.CharField()
    code = serializers.CharField()


class GeoNamesCitySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    city = serializers.StringRelatedField()
    geonames_admin1 = AddressGeoNamesSerializer()
    geonames_admin2 = AddressGeoNamesSerializer()
    license = LicenseSerializer()
    nuts_level1 = NutsSerializer()
    nuts_level2 = NutsSerializer()
    nuts_level3 = NutsSerializer()


class OrganizationAddressesSerializer(serializers.Serializer):
    lat = serializers.DecimalField(max_digits=None,
                                   decimal_places=10,
                                   coerce_to_string=False)
    lng = serializers.DecimalField(max_digits=None,
                                   decimal_places=10,
                                   coerce_to_string=False)
    state = serializers.StringRelatedField()
    state_code = serializers.CharField()
    city = serializers.CharField()
    geonames_city = GeoNamesCitySerializer()
    postcode = serializers.CharField()
    primary = serializers.BooleanField()
    line = serializers.CharField()
    country_geonames_id = serializers.IntegerField()


class ExternalIdSerializer(serializers.Serializer):
    preferred = serializers.CharField()
    all = serializers.StringRelatedField(many=True)


class GridExternalIdSerializer(serializers.Serializer):
    preferred = serializers.CharField()
    all = serializers.StringRelatedField()


class ExternalIdsSerializer(serializers.Serializer):
    ISNI = ExternalIdSerializer(required=False)
    FundRef = ExternalIdSerializer(required=False)
    HESA = ExternalIdSerializer(required=False)
    UCAS = ExternalIdSerializer(required=False)
    UKPRN = ExternalIdSerializer(required=False)
    CNRS = ExternalIdSerializer(required=False)
    OrgRef = ExternalIdSerializer(required=False)
    Wikidata = ExternalIdSerializer(required=False)
    GRID = GridExternalIdSerializer(required=False)


class OrganizationSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    email_address = serializers.StringRelatedField()
    ip_addresses = serializers.StringRelatedField(many=True)
    established = serializers.IntegerField()
    types = serializers.StringRelatedField(many=True)
    relationships = OrganizationRelationshipsSerializer(many=True)
    addresses = OrganizationAddressesSerializer(many=True)
    links = serializers.StringRelatedField(many=True)
    aliases = serializers.StringRelatedField(many=True)
    acronyms = serializers.StringRelatedField(many=True)
    status = serializers.CharField()
    wikipedia_url = serializers.CharField()
    labels = OrganizationLabelSerializer(many=True)
    country = CountrySerializer()
    external_ids = ExternalIdsSerializer()


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
