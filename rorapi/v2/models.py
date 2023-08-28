from geonamescache.mappers import country
from rorapi.common.models import Aggregations, Entity


class GeoNamesDetails:
    """A model class for storing geonames city hash"""

    def __init__(self, data):
        self.name = data.name
        self.lat = data.lat
        self.lng = data.lng
        self.country_code = data.country_code
        self.country_name = data.country_name


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
            data, ["domains", "established", "id", "types", "status"]
        )
        self.admin = Admin(data.admin)
        self.external_ids = [
            Entity(e, ["type", "preferred", "all"]) for e in data.external_ids
        ]
        self.links = [Entity(l, ["value", "type"]) for l in data.links]
        self.locations = [Location(l) for l in data.locations]
        self.names = [Entity(n, ["value", "lang", "types"]) for n in data.names]
        self.relationships = [
            Entity(r, ["type", "label", "id"]) for r in data.relationships
        ]


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