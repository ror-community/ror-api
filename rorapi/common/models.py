from geonamescache.mappers import country


class Entity:
    """Generic model class"""

    def __init__(self, base_object, attributes):
        [setattr(self, a, getattr(base_object, a)) for a in attributes]


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
        mapper = country(from_key="iso", to_key="name")
        try:
            self.title = mapper(data.key)
        except AttributeError:
            # if we have a country code with no name mapping, skip it to prevent 500
            pass
        self.count = data.doc_count

class ContinentBucket:
    """A model class for country aggregation bucket"""

    def __init__(self, data):
        self.id = data.key.lower()
        self.title = data.key
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
        self.continents = [ContinentBucket(b) for b in data.continents.buckets]
        self.statuses = [StatusBucket(b) for b in data.statuses.buckets]


class Errors:
    """Errors model class"""

    def __init__(self, errors):
        self.errors = errors
