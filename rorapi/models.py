import pycountry

from rest_framework import serializers

#####################################################################
# Models                                                            #
#####################################################################


class Entity:
    """Generic model class"""
    def __init__(self, base_object, attributes):
        [setattr(self, a, getattr(base_object, a)) for a in attributes]

class GeoCity:
    """A model class for storing external identifiers"""
    def __init__(self, data):
        for a in [
                'geonames_city'
        ]:
            try:
                setattr(self, a, Entity(getattr(data, a),
                                        ['id']))
            except AttributeError:
                pass

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
        super(Organization, self).__init__(data, [
            'id', 'name', 'types', 'links', 'aliases', 'acronyms', 'status',
            'wikipedia_url','established','relationships','addresses'
        ])
        self.labels = [Entity(l, ['label', 'iso639']) for l in data.labels]
        self.country = Entity(data.country, ['country_name', 'country_code'])
        self.relationships = [Entity(r, ['type','label','id']) for r in data.relationships]
        self.addresses = [Entity(a, ['lng','lat','state_code','city','postcode','line']) for a in data.addresses]
        self.geonames_city = GeoCity(data.addresses)
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
        country = pycountry.countries.get(alpha_2=data.key)
        try:
            self.title = country.official_name
        except AttributeError:
            self.title = country.name
        self.count = data.doc_count


class Aggregations:
    """Aggregations model class"""
    def __init__(self, data):
        self.types = [TypeBucket(b) for b in data.types.buckets]
        self.countries = [CountryBucket(b) for b in data.countries.buckets]


class ListResult:
    """A model class for the list of organizations returned from the search"""
    def __init__(self, data):
        self.number_of_results = data.hits.total
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
        self.organization = data.organization


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

class AddressGeoNamesSerializer(serializers.Serializer):
    name = serializers.CharField()
    id = serializers.CharField()
    ascii_name = serializers.CharField()
    code = serializers.CharField()

class GeoNamesCitySerializer(serializers.Serializer):
    id = serializers.IntegerField()

class OrganizationAddressesSerializer(serializers.Serializer):
    lat = serializers.CharField()
    lng = serializers.CharField()
    state_code = serializers.CharField()
    city = serializers.CharField()
    postcode = serializers.CharField()
    line = serializers.CharField()


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
    established = serializers.IntegerField()
    types = serializers.StringRelatedField(many=True)
    relationships = OrganizationRelationshipsSerializer(many=True)
    addresses = OrganizationAddressesSerializer(many=True)
    geonames_city = GeoNamesCitySerializer()
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
