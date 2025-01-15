from geonamescache.mappers import country
from rorapi.common.models import TypeBucket, CountryBucket, StatusBucket, Entity
from rorapi.v2.record_constants import continent_code_to_name

class ContinentBucket:
    """A model class for country aggregation bucket"""

    def __init__(self, data):
        self.id = data.key.lower()
        self.title = continent_code_to_name(data.key)
        self.count = data.doc_count

class CountryBucket:
    """A model class for country aggregation bucket"""

    def __init__(self, data):
        self.id = data.key.lower()
        mapper = country(from_key="iso", to_key="name")
        try:
            self.title = mapper(data.key)
        except AttributeError:
            # if we have a country code with no name mapping, skip it to prevent 500
            pass
        self.count = data.doc_count


class Aggregations:
    """Aggregations model class"""

    def __init__(self, data):
        self.types = [TypeBucket(b) for b in data.types.buckets]
        self.countries = [CountryBucket(b) for b in data.countries.buckets]
        self.continents = [ContinentBucket(b) for b in data.continents.buckets]
        self.statuses = [StatusBucket(b) for b in data.statuses.buckets]

class GeoNamesDetails:
    """A model class for storing geonames city hash"""

    def __init__(self, data):
        self.continent_code = getattr(data, 'continent_code', None)
        self.continent_name = getattr(data, 'continent_name', None)
        self.country_code = data.country_code
        self.country_name = data.country_name
        self.country_subdivision_code = getattr(data, 'country_subdivision_code', None)
        self.country_subdivision_name = getattr(data, 'country_subdivision_name', None)
        self.name = data.name
        self.lat = data.lat
        self.lng = data.lng


class Location:
    """A model class for storing addresses"""

    def __init__(self, data):
        self.geonames_id = data.geonames_id
        self.geonames_details = GeoNamesDetails(data.geonames_details)


class ExternalId:
    """A model class for storing external id"""

    def __init__(self, data):
        self.type = data.type
        self.preferred = data.preferred
        self.all = [a for a in data.all]


class Admin:
    """A model class for storing admin information"""

    def __init__(self, data):
        for a in ["created", "last_modified"]:
            try:
                setattr(self, a, Entity(getattr(data, a), ["date", "schema_version"]))
            except AttributeError:
                pass


class Organization(Entity):
    """Organization model class"""

    def __init__(self, data):
        if "_source" in data:
            data = data["_source"]
        super(Organization, self).__init__(
            data, ["established", "id", "status"]
        )
        self.admin = Admin(data.admin)
        self.domains = sorted(data.domains)
        sorted_ext_ids = sorted(data.external_ids, key=lambda x: x['type'])
        self.external_ids = [
            Entity(e, ["type", "preferred", "all"]) for e in sorted_ext_ids
        ]
        sorted_links = sorted(data.links, key=lambda x: x['type'])
        self.links = [Entity(l, ["value", "type"]) for l in sorted_links]
        self.locations = [Location(l) for l in data.locations]
        sorted_names = sorted(data.names, key=lambda x: x['value'])
        self.names = [Entity(n, ["value", "lang", "types"]) for n in sorted_names]
        sorted_rels = sorted(data.relationships, key=lambda x: x['type'])
        self.relationships = [
            Entity(r, ["type", "label", "id"]) for r in sorted_rels
        ]
        self.types = sorted(data.types)


class ListResult:
    """A model class for the list of organizations returned from the search"""

    def __init__(self, data):
        self.number_of_results = data.hits.total.value
        self.time_taken = data.took
        self.items = [Organization(x) for x in data]
        self.meta = Aggregations(data.aggregations)


class MatchedOrganization:
    """A model class for an organization matched based on an affiliation
    string"""

    def __init__(self, data):
        print(data)
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