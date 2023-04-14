from rest_framework import serializers
from geonamescache.mappers import country

#####################################################################
# Models                                                            #
#####################################################################


class Entity:
    """Generic model class"""
    def __init__(self, base_object, attributes):
        print("BASE_OBJ")
        print(base_object)
        #print("ATTRS")
        #print(attributes)
        [setattr(self, a, getattr(base_object, a)) for a in attributes]


class GeoAdmin:
    def __init__(self, data):
        if hasattr(data, 'id'):
            self.id = data.id
        else:
            self.id = None
        if hasattr(data, 'code'):
            self.code = data.code
        else:
            self.code = None
        if hasattr(data, 'name'):
            self.name = data.name
        else:
            self.name = None
        if hasattr(data, 'ascii_name'):
            self.ascii_name = data.ascii_name
        else:
            self.ascii_name = None


class Nuts:
    """A model class for storing the NUTS metadata"""
    def __init__(self, data):
        self.code = getattr(data, 'code', None)
        self.name = getattr(data, 'name', None)


class License:
    """A model class for storing license metadata"""
    def __init__(self, data):
        self.attribution = getattr(data, 'attribution', None)
        self.license = getattr(data, 'license', None)


class GeoNamesCity:
    """A model class for storing geonames city hash"""
    def __init__(self, data):
        self.id = getattr(data, 'id', None)
        self.city = getattr(data, 'city', None)
        if hasattr(data, 'license'):
            self.license = License(data.license)
        else:
            self.license = None
        if hasattr(data, 'geonames_admin1'):
            self.geonames_admin1 = GeoAdmin(data.geonames_admin1)
        else:
            self.geonames_admin1 = None
        if hasattr(data, 'geonames_admin2'):
            self.geonames_admin2 = GeoAdmin(data.geonames_admin2)
        else:
            self.geonames_admin2 = None
        if hasattr(data, 'nuts_level1'):
            self.nuts_level1 = GeoAdmin(data.nuts_level1)
        else:
            self.nuts_level1 = None
        if hasattr(data, 'nuts_level2'):
            self.nuts_level2 = GeoAdmin(data.nuts_level2)
        else:
            self.nuts_level2 = None
        if hasattr(data, 'nuts_level3'):
            self.nuts_level3 = GeoAdmin(data.nuts_level3)
        else:
            self.nuts_level3 = None


class Addresses:
    """A model class for storing addresses"""
    def __init__(self, data):
        self.country_geonames_id = data.country_geonames_id
        self.lat = data.lat
        self.lng = data.lng
        self.line = data.line
        self.state_code = data.state_code
        self.state = getattr(data, 'state', None)
        self.postcode = data.postcode
        self.city = data.city
        self.primary = data.primary
        self.geonames_city = GeoNamesCity(data.geonames_city)


class ExternalIds:
    """A model class for storing external identifiers"""
    def __init__(self, data):
        for a in [
                'ISNI', 'FundRef', 'HESA', 'UCAS', 'UKPRN', 'CNRS', 'OrgRef',
                'Wikidata', 'GRID'
        ]:
            try:
                setattr(self, a, Entity(getattr(data, a),
                                        ['preferred', 'all']))
            except AttributeError:
                pass


class Organization(Entity):
    """Organization model class"""
    def __init__(self, data):
        if "_source" in data:
            data = data["_source"]
        super(Organization, self).__init__(data, [
            'id', 'name', 'types', 'links', 'aliases', 'acronyms', 'status',
            'wikipedia_url', 'established', 'relationships', 'addresses'
        ])
        self.labels = [Entity(l, ['label', 'iso639']) for l in data.labels]
        self.country = Entity(data.country, ['country_name', 'country_code'])
        self.ip_addresses = data.ip_addresses
        self.established = getattr(data, 'established', None)
        self.email_address = getattr(data, 'email_address', None)
        self.relationships = [
            Entity(r, ['type', 'label', 'id']) for r in data.relationships
        ]
        self.addresses = [Addresses(a) for a in data.addresses]
        self.external_ids = ExternalIds(data.external_ids)


class TypeBucket:
    """A model class for type aggregation bucket"""
    def __init__(self, data):
        self.id = data.key.lower()
        self.title = data.key
        self.count = data.doc_count


class CountryBucket:
    """A model class for country aggregation bucket"""
    def __init__(self, data):
        self.id = data.key.lower()
        mapper = country(from_key='iso', to_key='name')
        try:
            self.title = mapper(data.key)
        except AttributeError:
            # if we have a country code with no name mapping, skip it to prevent 500
            pass
        self.count = data.doc_count

class StatusBucket:
    """A model class for status aggregation bucket"""
    def __init__(self, data):
        self.id = data.key.lower()
        self.title = data.key
        self.count = data.doc_count


class Aggregations:
    """Aggregations model class"""
    def __init__(self, data):
        self.types = [TypeBucket(b) for b in data.types.buckets]
        self.countries = [CountryBucket(b) for b in data.countries.buckets]
        self.statuses = [StatusBucket(b) for b in data.statuses.buckets]


class ListResult:
    """A model class for the list of organizations returned from the search"""
    def __init__(self, data):
        for x in data:
            print(x)
        self.number_of_results = data.hits.total.value
        self.time_taken = data.took
        self.items = [Organization(x) for x in data]
        self.meta = Aggregations(data.aggregations)


class MatchedOrganization:
    """A model class for an organization matched based on an affiliation
    string"""
    def __init__(self, data):
        self.substring = data.substring
        self.score = data.score
        self.matching_type = data.matching_type
        self.chosen = data.chosen
        self.organization = Organization(data.organization)


class MatchingResult:
    """A model class for the result of affiliation matching"""
    def __init__(self, data):
        self.number_of_results = len(data)
        self.items = [MatchedOrganization(x) for x in data]


class Errors:
    """Errors model class"""
    def __init__(self, errors):
        self.errors = errors


######################################################################
# Serializers                                                        #
######################################################################


class OrganizationLabelSerializer(serializers.Serializer):
    label = serializers.CharField()
    iso639 = serializers.CharField()


class OrganizationRelationshipsSerializer(serializers.Serializer):
    label = serializers.CharField()
    type = serializers.CharField()
    id = serializers.CharField()


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


class BucketSerializer(serializers.Serializer):
    id = serializers.CharField()
    title = serializers.CharField()
    count = serializers.IntegerField()


class AggregationsSerializer(serializers.Serializer):
    types = BucketSerializer(many=True)
    countries = BucketSerializer(many=True)
    statuses = BucketSerializer(many=True)


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


class ErrorsSerializer(serializers.Serializer):
    errors = serializers.StringRelatedField(many=True)
