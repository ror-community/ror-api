from rest_framework import serializers
from geonamescache.mappers import country

#####################################################################
# Models                                                            #
#####################################################################


class Entity:
    """Generic model class"""
    def __init__(self, base_object, attributes):
        [setattr(self, a, getattr(base_object, a)) for a in attributes]


class GeoNamesDetails:
    """A model class for storing geonames city hash"""
    def __init__(self, data):
        self.name = data.name
        self.lat = data.lat
        self.lng = data.lng
        self.country_code = data.country_code
        self.country_name = data.country_name


class Locations:
    """A model class for storing addresses"""
    def __init__(self, data):
        self.geonames_id = data.geonames_id
        self.geonames_details = GeoNamesDetails(data.geonames_details)


class Admin:
    """A model class for storing admin information"""
    def __init__(self, data):
        for a in [
                'created', 'last_modified'
        ]:
            try:
                setattr(self, a, Entity(getattr(data, a),
                                        ['date', 'schema_version']))
            except AttributeError:
                pass


class OrganizationV2(Entity):
    """Organization model class"""
    def __init__(self, data):
        if "_source" in data:
            data = data["_source"]
        super(OrganizationV2, self).__init__(data, [
            'domains', 'established', 'id', 'types', 'status'
        ])
        self.admin = Admin(data.admin)
        self.external_ids = [Entity(e, ['all', 'type', 'preferred']) for e in data.external_ids]
        self.links = [Entity(l, ['value', 'type']) for l in data.links]
        self.locations = [Locations(l) for l in data.locations]
        self.names = [Entity(n, ['value', 'lang', 'types']) for n in data.names]
        self.relationships = [
            Entity(r, ['type', 'label', 'id']) for r in data.relationships
        ]


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


class ListResultV2:
    """A model class for the list of organizations returned from the search"""
    def __init__(self, data):
        self.number_of_results = data.hits.total.value
        self.time_taken = data.took
        self.items = [OrganizationV2(x) for x in data]
        self.meta = Aggregations(data.aggregations)


class MatchedOrganization:
    """A model class for an organization matched based on an affiliation
    string"""
    def __init__(self, data):
        self.substring = data.substring
        self.score = data.score
        self.matching_type = data.matching_type
        self.chosen = data.chosen
        self.organization = OrganizationV2(data.organization)


class MatchingResultV2:
    """A model class for the result of affiliation matching"""
    def __init__(self, data):
        self.number_of_results = len(data)
        self.items = [MatchedOrganization(x) for x in data]


class ErrorsV2:
    """Errors model class"""
    def __init__(self, errors):
        self.errors = errors


######################################################################
# Serializers                                                        #
######################################################################
class AdminDetailsSerializer(serializers.Serializer):
    date = serializers.DateTimeField()
    schema_version = serializers.CharField()


class AdminSerializer(serializers.Serializer):
    created = AdminDetailsSerializer()
    last_modified = AdminDetailsSerializer()


class OrganizationNameSerializer(serializers.Serializer):
    value = serializers.CharField()
    lang = serializers.CharField()
    types = serializers.CharField()


class OrganizationRelationshipsSerializer(serializers.Serializer):
    label = serializers.CharField()
    type = serializers.CharField()
    id = serializers.CharField()


class ExternalIdSerializer(serializers.Serializer):
    all = serializers.CharField()
    type = serializers.CharField()
    preferred = serializers.CharField()


class LinkSerializer(serializers.Serializer):
    value = serializers.CharField()
    type = serializers.CharField()


class GeoNamesDetailsSerializer(serializers.Serializer):
    name = serializers.StringRelatedField()
    lat = serializers.DecimalField(max_digits=None,
                                   decimal_places=10,
                                   coerce_to_string=False)
    lng = serializers.DecimalField(max_digits=None,
                                   decimal_places=10,
                                   coerce_to_string=False)
    country_name = serializers.CharField()
    country_code = serializers.CharField()


class OrganizationLocationSerializer(serializers.Serializer):
    geonames_id = serializers.IntegerField()
    geonames_details = GeoNamesDetailsSerializer()


class OrganizationSerializerV2(serializers.Serializer):
    admin = AdminSerializer()
    domains = serializers.StringRelatedField(many=True)
    established = serializers.IntegerField()
    external_ids = ExternalIdSerializer(many=True)
    id = serializers.CharField()
    links = LinkSerializer(many=True)
    locations = OrganizationLocationSerializer(many=True)
    names = OrganizationNameSerializer(many=True)
    types = serializers.StringRelatedField(many=True)
    relationships = OrganizationRelationshipsSerializer(many=True)
    status = serializers.CharField()


class BucketSerializer(serializers.Serializer):
    id = serializers.CharField()
    title = serializers.CharField()
    count = serializers.IntegerField()


class AggregationsSerializer(serializers.Serializer):
    types = BucketSerializer(many=True)
    countries = BucketSerializer(many=True)
    statuses = BucketSerializer(many=True)


class ListResultSerializerV2(serializers.Serializer):
    number_of_results = serializers.IntegerField()
    time_taken = serializers.IntegerField()
    items = OrganizationSerializerV2(many=True)
    meta = AggregationsSerializer()


class MatchedOrganizationSerializer(serializers.Serializer):
    substring = serializers.CharField()
    score = serializers.FloatField()
    matching_type = serializers.CharField()
    chosen = serializers.BooleanField()
    organization = OrganizationSerializerV2()


class MatchingResultSerializerV2(serializers.Serializer):
    number_of_results = serializers.IntegerField()
    items = MatchedOrganizationSerializer(many=True)


class ErrorsSerializerV2(serializers.Serializer):
    errors = serializers.StringRelatedField(many=True)
